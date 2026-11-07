# Paraguay Climate Projections (Capstone)

Analysis of climate projections for Paraguay (datos.gov.py, 2006-2099).
Models: HadGEM2-ES, MIROC5, BESM, CanESM2. Scenarios: RCP4.5, RCP8.5.

## Stage 1 (December)
Rainfall change by region (Chaco vs Oriental) for the mid (2027-2063) and
end (2064-2099) terms, relative to the 1976-2005 baseline,
with model agreement. Models are shown separately (no ensemble).

## Structure
- `src/`: scripts (the real work)
- `notebooks/`: exploration only
- `data/`: raw/processed data (not in git)
- `outputs/`: tables and figures
- `app/`: Streamlit dashboard
- `docs/`: notes, findings, limitations

## Setup
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

## Data
Download from datos.gov.py into `data/raw/` (not tracked by git).

## Boundaries (Step 3)
Department boundaries come from geoBoundaries (Paraguay ADM1, not tracked by git). Download:
`Invoke-WebRequest "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbOpen/PRY/ADM1/geoBoundaries-PRY-ADM1.geojson" -OutFile data/external/departamentos/PRY_ADM1.geojson`
Then: `python -m src.assign_regions` and `python -m src.plot_region_map`.
