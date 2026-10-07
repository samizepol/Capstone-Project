"""Step 2: convert every raw CSV of one variable into a single tidy Parquet file.

Output: data/processed/climate_{var}.parquet with columns
    model, scen, var, date, year, month, lat, lon, value
DuckDB streams the CSVs straight into Parquet, so nothing is loaded fully into memory.

Run from the project root:
    python -m src.convert_to_parquet               # active variable from config (precip)
    python -m src.convert_to_parquet --var precip
"""
import argparse

import duckdb
from src.config import DATA_PROCESSED, VARIABLES, ACTIVE_VARIABLE
from src.raw_files import raw_files, parse_filename, csv_source, detect_columns, date_expr


def file_select(con, f, var, var_col):
    """SELECT statement that maps one raw CSV onto the common schema."""
    meta = parse_filename(f.stem)
    src = csv_source(f)
    cols = [c[0] for c in con.execute(f"DESCRIBE SELECT * FROM {src}").fetchall()]
    dt, la, lo = detect_columns(cols)
    if var_col not in cols:
        raise ValueError(f"{f.name}: column {var_col!r} not found in {cols}")
    d = date_expr(dt)
    # TRY_CAST so bad values become NULL and are caught by sanity_checks.py instead of crashing here
    return f"""
        SELECT '{meta["model"]}' AS model, '{meta["scenario"]}' AS scen, '{var}' AS var,
               {d} AS date, year({d}) AS year, month({d}) AS month,
               round(CAST("{la}" AS DOUBLE), 3) AS lat,
               round(CAST("{lo}" AS DOUBLE), 3) AS lon,
               TRY_CAST("{var_col}" AS DOUBLE) AS value
        FROM {src}"""


def convert(var):
    var_col = VARIABLES[var]
    files = raw_files(var_col)
    if not files:
        raise FileNotFoundError(f"No raw CSVs found for variable {var!r} (column {var_col})")

    con = duckdb.connect()
    union = "\nUNION ALL\n".join(file_select(con, f, var, var_col) for f in files)
    out = DATA_PROCESSED / f"climate_{var}.parquet"
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    print(f"Converting {len(files)} files -> {out.relative_to(DATA_PROCESSED.parents[1])}")
    con.execute(f"""
        COPY (SELECT * FROM ({union}) ORDER BY model, scen, date, lat, lon)
        TO '{out.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
    """)

    # Row counts must match the raw files exactly
    n_raw = sum(con.execute(f"SELECT count(*) FROM {csv_source(f)}").fetchone()[0] for f in files)
    summary = con.execute(f"""
        SELECT model, scen, count(*) AS n_rows, min(date) AS first, max(date) AS last
        FROM '{out.as_posix()}' GROUP BY ALL ORDER BY ALL
    """).df()
    print(summary.to_string(index=False))
    n_out = int(summary["n_rows"].sum())
    print(f"\nRows: raw={n_raw:,}  parquet={n_out:,}  "
          f"{'OK' if n_raw == n_out else 'MISMATCH'}  ({out.stat().st_size / 1e6:.1f} MB)")
    if n_raw != n_out:
        raise RuntimeError("Row count mismatch between raw CSVs and Parquet")
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--var", default=ACTIVE_VARIABLE, choices=list(VARIABLES))
    convert(p.parse_args().var)
