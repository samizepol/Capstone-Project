"""Helpers for the raw datos.gov.py CSVs: filename parsing and column detection."""
import re

from src.config import DATA_RAW, MODELS

# e.g. HADGEM2-ES_RCP45_PREC_2006_2099_PY.csv
FNAME = re.compile(r"^(?P<model>.+)_(?P<scenario>HISTORICO|RCP\d+)_(?P<variable>[A-Z]+)"
                   r"_(?P<start_year>\d{4})_(?P<end_year>\d{4})_(?P<region>[A-Z]+)$")
MODEL_NAMES = {m.upper(): m for m in MODELS}           # CANESM2 -> CanESM2
SCENARIO_NAMES = {"HISTORICO": "historical"}           # RCP45/RCP85 stay as-is


def parse_filename(stem):
    m = FNAME.match(stem)
    if not m:
        raise ValueError(f"Unexpected filename pattern: {stem}")
    meta = m.groupdict()
    meta["model"] = MODEL_NAMES.get(meta["model"].upper(), meta["model"])
    meta["scenario"] = SCENARIO_NAMES.get(meta["scenario"], meta["scenario"])
    meta["start_year"], meta["end_year"] = int(meta["start_year"]), int(meta["end_year"])
    return meta


def raw_files(var_col=None):
    """Raw CSVs sorted by name, optionally only those for one variable column (e.g. 'PREC')."""
    files = sorted(DATA_RAW.glob("*.csv"))
    if var_col:
        files = [f for f in files if parse_filename(f.stem)["variable"] == var_col]
    return files


def csv_source(path):
    """DuckDB table expression that reads a raw CSV with every column as text."""
    return f"read_csv('{path.as_posix()}', header=true, all_varchar=true)"


def detect_columns(cols):
    """Return (date, lat, lon) column names. Layouts differ:
    historical = Data,Hora,Latitude,Longitude,<VAR>; RCP = Fecha,Latitud,Longitud,<VAR>."""
    lower = {c.lower(): c for c in cols}
    dt = lower.get("fecha") or lower.get("data")
    la = next(c for c in cols if c.lower().startswith("lat"))
    lo = next(c for c in cols if c.lower().startswith("lon"))
    return dt, la, lo


def date_expr(col):
    """SQL turning '1961/01/01' or '2006-01-01' into a DATE."""
    return f"""CAST(replace("{col}", '/', '-') AS DATE)"""
