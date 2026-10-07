from pathlib import Path

# Paths
ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_INTERIM = ROOT / "data" / "interim"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_EXTERNAL = ROOT / "data" / "external"
OUT_TABLES = ROOT / "outputs" / "tables"
OUT_FIGURES = ROOT / "outputs" / "figures"
APP_DATA = ROOT / "app" / "data"

# Models and scenarios (confirm exact names against the filenames in Step 1)
MODELS = ["HadGEM2-ES", "MIROC5", "BESM", "CanESM2"]
SCENARIOS = ["RCP45", "RCP85"]

# Variables (stage 1: precipitation only; the code stays parameterized)
VARIABLES = {"precip": "PREC"}  # TODO: confirm the column/variable name in Step 1
ACTIVE_VARIABLE = "precip"
UNITS = {"precip": "mm/month"}  # confirmed in Step 1 (notebooks/01_inventory_checks.ipynb)
# Physically plausible range per value (sanity_checks.py flags anything outside it)
PLAUSIBLE_RANGE = {"precip": (0.0, 1500.0)}

# Periods
HIST_PERIOD = (1961, 2005)     # coverage of the historical files
FUTURE_PERIOD = (2006, 2099)   # coverage of the RCP files (used by the data checks)
BASELINE = (1976, 2005)        # reference climate for computing change

# Projections are analysed from 2027 on, split into two contiguous terms (no gap, no overlap).
# 2006-2026 stays in the processed data but is not part of any projection window.
PROJECTION_PERIOD = (2027, 2099)
FUTURE_WINDOWS = {"mid": (2027, 2063), "end": (2064, 2099)}   # 37 and 36 years

assert FUTURE_WINDOWS["mid"][0] == PROJECTION_PERIOD[0]
assert FUTURE_WINDOWS["end"][1] == PROJECTION_PERIOD[1]
assert FUTURE_WINDOWS["mid"][1] + 1 == FUTURE_WINDOWS["end"][0]

# Expected month counts (Step 1 check)
N_MONTHS_FUTURE = 1128   # 2006-2099
N_MONTHS_HIST = 540      # 1961-2005

# Regions
CHACO_DEPARTMENTS = ["Alto Paraguay", "Boquerón", "Presidente Hayes"]

# Seasons
SEASONS = {
    "DJF": [12, 1, 2],
    "MAM": [3, 4, 5],
    "JJA": [6, 7, 8],
    "SON": [9, 10, 11],
}