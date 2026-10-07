# Paraguay Climate Projections (Capstone)

Analysis of climate projections for Paraguay (datos.gov.py, 2006-2099).
Models: HadGEM2-ES, MIROC5, BESM, CanESM2. Scenarios: RCP4.5, RCP8.5.

## Stage 1 (December)
Rainfall change by region (Chaco vs Oriental) by mid- and end-century,
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