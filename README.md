# Frjógv í Føroyum

Ein einføld vevsíða sum vísir mett gras- og bjørkufrjógv fyri Føroyar,
bygt á evropeisku CAMS-frágreiðingina (Copernicus Atmosphere Monitoring Service).

**Viðmerking:** CAMS hevur onga máingarstøð í Føroyum. Talini eru ókalibrerað
modell-mett, ikki máld. Vevsíðan sigur hetta greitt fyri brúkaranum.

## Hvussu tað virkar

1. Ein GitHub Action koyrir hvønn dag kl. 10:00 UTC.
2. Hon heintar gras- og bjørkufrjógv fyri eitt lítið øki kring Føroyar úr CAMS.
3. Hon skrivar `data/pollen.json` og committar hana aftur í repoið.
4. GitHub Pages tænir `index.html` + `data/pollen.json` sum static síðu.

Eingin ambætari (server) — alt koyrir ókeypis á GitHub.

## Uppseting

### 1. CAMS-konta og API-lyklur

- Stovna eina konta á https://ads.atmosphere.copernicus.eu/
- Far til vangamyndina → **API Token**. Copyera lykilin (long tekstur).
- Á fyrstu koyring skalt tú møguliga góðkenna licensina fyri
  *cams-europe-air-quality-forecasts* eina ferð (inni á ADS-vevsíðuni).

### 2. Legg lykilin sum secret

Í repoinum: **Settings → Secrets and variables → Actions → New secret**
- Navn: `CDSAPI_KEY`
- Virði: tín ADS API-lykil

### 3. Kveik GitHub Pages

**Settings → Pages → Source: Deploy from a branch → main / (root)**

### 4. Koyr fyrstu ferð

**Actions → Dagliga frjógv-dátu → Run workflow** (manuelt).
Tá ið hon er liðug, er `data/pollen.json` skrivað og síðan er klár.

## Lokalt

```bash
pip install cdsapi xarray netcdf4 numpy
export CDSAPI_URL=https://ads.atmosphere.copernicus.eu/api
export CDSAPI_KEY=<tín lykil>
python scripts/fetch_pollen.py
```

Fyri at royna vevsíðuna lokalt (við test-dátu):
```bash
python3 -m http.server 8000
# opna http://localhost:8000
```

## Skrá

```
index.html                     vevsíðan (ein fíla)
data/pollen.json               dagførd dátu (skrivað av botti)
scripts/fetch_pollen.py        heintar + umskrivar CAMS-dátu
.github/workflows/update-pollen.yml   dagliga koyring
```

## Mørk og stig

Grasfrjógv-stigini fylgja vanligum evropeiskum mørkum (frjókorn/m³):
lágt < 30, moderat 30–50, høgt 50–150, sera høgt > 150.
Bjørk hevur aðrar mørk (sí `scripts/fetch_pollen.py`). Hesar kunnu tú
tillaga um tú hevur betri lokal viðmiðanir.

## Licens

CAMS-dátu er ókeypis og opin, men krevur rætta ávísing til Copernicus/CAMS.
Vevsíðan ávísir keldu í foturinum. Sí Copernicus-licensina:
https://ads.atmosphere.copernicus.eu/
