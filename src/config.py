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

# Periods
HIST_PERIOD = (1961, 2005)
FUTURE_PERIOD = (2006, 2099)
BASELINE = (1976, 2005)
FUTURE_WINDOWS = {"mid": (2041, 2070), "end": (2071, 2099)}

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