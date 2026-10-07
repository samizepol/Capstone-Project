"""Step 1 inventory: one row per raw CSV with filename metadata, row count, date range and QC checks.

DuckDB streams each CSV through aggregate queries, so no file is loaded fully into memory.
Run from the project root:  python -m src.inventory
"""
import duckdb
import pandas as pd
from src.config import OUT_TABLES, VARIABLES, ACTIVE_VARIABLE, N_MONTHS_FUTURE, N_MONTHS_HIST
from src.raw_files import raw_files, parse_filename, csv_source, detect_columns, date_expr

con = duckdb.connect()
rows = []

for f in raw_files():
    meta = parse_filename(f.stem)
    src = csv_source(f)
    cols = [c[0] for c in con.execute(f"DESCRIBE SELECT * FROM {src}").fetchall()]
    dt, la, lo = detect_columns(cols)
    val = VARIABLES[ACTIVE_VARIABLE]
    d = f'"{dt}"'
    dd = date_expr(dt)
    v = f'TRY_CAST("{val}" AS DOUBLE)'

    stats = con.execute(f"""
        SELECT count(*) AS n_rows,
               count(DISTINCT {d}) AS n_dates,
               count(DISTINCT ("{la}", "{lo}")) AS n_cells,
               min({dd}) AS first_date, max({dd}) AS last_date,
               string_agg(DISTINCT substr({d}, 9, 2), ',') AS days_present,
               count(*) FILTER (WHERE regexp_matches({d}, '[-/]02[-/]29')) AS n_feb29,
               count(*) FILTER (WHERE {v} IS NULL) AS n_nulls,
               min({v}) AS vmin, max({v}) AS vmax, avg({v}) AS vmean
        FROM {src}
    """).df().iloc[0].to_dict()

    grid_hash = con.execute(f"""
        SELECT md5(string_agg(la || ',' || lo, ';' ORDER BY la, lo))
        FROM (SELECT DISTINCT round(CAST("{la}" AS DOUBLE), 3) AS la,
                              round(CAST("{lo}" AS DOUBLE), 3) AS lo FROM {src})
    """).fetchone()[0]

    expected = N_MONTHS_HIST if meta["scenario"] == "historical" else N_MONTHS_FUTURE
    rows.append({
        "file": f.name, **meta,
        "cols": "|".join(cols), "date_col": dt, "lat_col": la, "lon_col": lo, "value_col": val,
        **stats,
        "years_match_name": (stats["first_date"].year == meta["start_year"]
                             and stats["last_date"].year == meta["end_year"]),
        "grid_hash": grid_hash,
        "expected_months": expected,
        "months_ok": stats["n_dates"] == expected,
        "complete": stats["n_rows"] == stats["n_dates"] * stats["n_cells"],
    })
    print("done:", f.name)

df = pd.DataFrame(rows)
OUT_TABLES.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT_TABLES / "file_inventory.csv", index=False)

pd.set_option("display.width", 250)
print("\nColumn layouts found:", list(df["cols"].unique()))
print("Unique grids:", df["grid_hash"].nunique(), "(expected 1)")
print("Files with wrong month count:", (~df["months_ok"]).sum())
print("Incomplete files:", (~df["complete"]).sum())
print(df[["model", "scenario", "variable", "start_year", "end_year", "n_rows", "n_dates",
          "n_cells", "first_date", "last_date", "months_ok"]].to_string())
print(df[["file", "days_present", "n_feb29", "n_nulls", "vmin", "vmax", "vmean"]].to_string())
