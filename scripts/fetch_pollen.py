#!/usr/bin/env python3
"""
Heintar gras- og bjørkufrjógv (grass + birch pollen) úr CAMS European
air quality forecasts fyri Føroyar og skrivar eina reina JSON-fílu.

Data: Copernicus Atmosphere Monitoring Service (CAMS), ensemble median.
Eind: frjókorn/m3 (grains/m3) við jørðina.

VÍÐMERKING: CAMS hevur onga jarðstøð í Føroyum. Talini eru ókalibrerað
modell-mett, ikki máld. Sí www (ansvarsfráskriving) á vevsíðuni.
"""

import os
import sys
import json
import datetime as dt
import tempfile

import cdsapi
import xarray as xr
import numpy as np

# ---- Uppseting -------------------------------------------------------------

# Ískoyti kring Føroyar: [nord, vest, sud, eyst]
# Føroyar liggja umleið 61.3-62.4 N, 6.2-7.7 W.
AREA = [62.5, -7.8, 61.2, -6.1]

VARIABLES = {
    "grass_pollen": "gras",
    "birch_pollen": "bjork",
}

# Frágreiðing um stig (grains/m3) fyri gras. Vanligar evropeiskar mørk.
# Birch hevur aðrar mørk, men vit brúka somu skala fyri einfaldni í fyrstu útgávu.
# Kelda: vanligar EAACI/EAN-tær mørk fyri gras.
GRASS_LEVELS = [
    (0, 1, "eingin", "None"),
    (1, 30, "lágt", "Low"),
    (30, 50, "moderat", "Moderate"),
    (50, 150, "høgt", "High"),
    (150, float("inf"), "sera høgt", "Very high"),
]
BIRCH_LEVELS = [
    (0, 1, "eingin", "None"),
    (1, 100, "lágt", "Low"),
    (100, 300, "moderat", "Moderate"),
    (300, 1500, "høgt", "High"),
    (1500, float("inf"), "sera høgt", "Very high"),
]


def level_for(value, table):
    for lo, hi, fo, en in table:
        if lo <= value < hi:
            return {"fo": fo, "en": en}
    return {"fo": "ókent", "en": "unknown"}


def fetch(client, date_str):
    """Heintar 0-96 tímar frá dagsins 00:00-forecast fyri okkara ískoyti."""
    leadtimes = [str(h) for h in range(0, 97, 3)]  # hvør 3. tími, 0..96
    request = {
        "variable": list(VARIABLES.keys()),
        "model": "ensemble",
        "level": "0",
        "date": f"{date_str}/{date_str}",
        "type": "forecast",
        "time": "00:00",
        "leadtime_hour": leadtimes,
        "data_format": "netcdf",
        "area": AREA,
    }
    tmp = tempfile.NamedTemporaryFile(suffix=".nc", delete=False)
    tmp.close()
    client.retrieve("cams-europe-air-quality-forecasts", request).download(tmp.name)
    return tmp.name


def process(nc_path, base_date):
    ds = xr.open_dataset(nc_path)

    # Variabul-nøvn í fíluni kunnu vera stutt (t.d. gr_pol / apg_conc).
    # Vit leita eftir teimum sum líkjast.
    def find_var(candidates):
        for name in ds.data_vars:
            low = name.lower()
            if any(c in low for c in candidates):
                return name
        return None

    varmap = {
        "grass_pollen": find_var(["gr_pol", "grass", "gpg"]),
        "birch_pollen": find_var(["bir", "bpg", "birch"]),
    }

    # Tíðar-koordinat kann eita 'time' ella 'forecast_period'/'leadtime'.
    time_dim = None
    for cand in ["time", "forecast_period", "leadtime", "step"]:
        if cand in ds.dims:
            time_dim = cand
            break
    if time_dim is None:
        # sum bakstoppari: tak fyrsta dim sum ikki er lat/lon/level
        for d in ds.dims:
            if d not in ("latitude", "longitude", "lat", "lon", "level"):
                time_dim = d
                break

    result = {}
    for var_key, short in VARIABLES.items():
        vname = varmap[var_key]
        if vname is None:
            result[short] = None
            continue

        da = ds[vname].squeeze()

        # Reduser um lat/lon: tak MAX yvir øki (verstu støðu í Føroyum).
        space_dims = [d for d in da.dims if d in ("latitude", "longitude", "lat", "lon")]
        per_time = da.max(dim=space_dims)  # ein value per leadtime

        # Byggj dagligar tættir: leadtime-tímar -> almanaks-dagar.
        # Vit vita leadtime-tímarnar úr okkara umbøn (0..96 hvør 3.).
        n = per_time.sizes[time_dim]
        leadtimes = list(range(0, 97, 3))[:n]

        daily = {}
        for i, lt in enumerate(leadtimes):
            day = base_date + dt.timedelta(hours=lt)
            key = day.date().isoformat()
            val = float(per_time.isel({time_dim: i}).values)
            if np.isnan(val):
                continue
            daily.setdefault(key, []).append(val)

        table = GRASS_LEVELS if var_key == "grass_pollen" else BIRCH_LEVELS
        days = []
        for day_key in sorted(daily.keys()):
            peak = max(daily[day_key])
            days.append({
                "date": day_key,
                "peak": round(peak, 2),
                "level": level_for(peak, table),
            })
        result[short] = days

    ds.close()
    return result


def main():
    url = os.environ.get("CDSAPI_URL")
    key = os.environ.get("CDSAPI_KEY")
    if not key:
        print("Vantar CDSAPI_KEY", file=sys.stderr)
        sys.exit(1)

    client = cdsapi.Client(url=url, key=key)

    today = dt.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    date_str = today.strftime("%Y-%m-%d")

    nc_path = fetch(client, date_str)
    forecast = process(nc_path, today)

    output = {
        "updated": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "source": "Copernicus Atmosphere Monitoring Service (CAMS)",
        "note_fo": "Ókalibrerað modell-mett. Eingin jarðstøð í Føroyum.",
        "note_en": "Uncalibrated model estimate. No ground station in the Faroe Islands.",
        "area": {"north": AREA[0], "west": AREA[1], "south": AREA[2], "east": AREA[3]},
        "forecast": forecast,
    }

    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "pollen.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Skrivaði {out_path}")

    # --- Søgu-logg: goym dagsins mett fyri hvørja slag ---------------------
    # Vit brúka forecast fyri "í dag" (fyrsti dagur) sum dagsins verði.
    today_key = today.date().isoformat()
    hist_path = os.path.join(out_dir, "history.json")
    try:
        with open(hist_path, encoding="utf-8") as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history = {"days": []}

    entry = {"date": today_key}
    for short in VARIABLES.values():
        arr = forecast.get(short)
        entry[short] = arr[0]["peak"] if arr else None

    # Skift út um dagurin longu er skrásettur (t.d. manuell endurkoyring).
    history["days"] = [d for d in history["days"] if d.get("date") != today_key]
    history["days"].append(entry)
    history["days"].sort(key=lambda d: d["date"])
    # Hald bert seinastu 400 dagar.
    history["days"] = history["days"][-400:]
    history["updated"] = output["updated"]

    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    print(f"Skrivaði {hist_path} ({len(history['days'])} dagar)")

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
