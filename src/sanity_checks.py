"""Step 2: sanity checks on data/processed/climate_{var}.parquet.

Checks nulls, value ranges, duplicates, grid consistency, month counts and coverage,
and writes one row per (model, scen, check) to outputs/tables/sanity_report.csv.
Status: PASS, WARN (worth a note, analysis can continue) or FAIL (must be fixed).
Exits with code 1 if anything FAILs.

Run from the project root:
    python -m src.sanity_checks
    python -m src.sanity_checks --var precip
"""
import argparse
import sys

import duckdb
import pandas as pd
from src.config import (DATA_PROCESSED, OUT_TABLES, VARIABLES, ACTIVE_VARIABLE, MODELS, SCENARIOS,
                        HIST_PERIOD, FUTURE_PERIOD, N_MONTHS_HIST, N_MONTHS_FUTURE, PLAUSIBLE_RANGE,
                        BASELINE, FUTURE_WINDOWS)


def run_checks(var):
    pq = DATA_PROCESSED / f"climate_{var}.parquet"
    if not pq.exists():
        raise FileNotFoundError(f"{pq} not found. Run: python -m src.convert_to_parquet --var {var}")
    con = duckdb.connect()
    con.execute(f"CREATE VIEW d AS SELECT * FROM '{pq.as_posix()}'")
    lo_ok, hi_ok = PLAUSIBLE_RANGE[var]

    g = con.execute(f"""
        WITH per_month AS (
            SELECT model, scen, date, count(*) AS n FROM d GROUP BY ALL
        ), grids AS (
            SELECT model, scen, md5(string_agg(lat || ',' || lon, ';' ORDER BY lat, lon)) AS grid_hash
            FROM (SELECT DISTINCT model, scen, lat, lon FROM d) GROUP BY ALL
        )
        SELECT model, scen,
               count(*) AS n_rows,
               count(*) FILTER (WHERE value IS NULL) AS null_value,
               count(*) FILTER (WHERE date IS NULL OR lat IS NULL OR lon IS NULL) AS null_keys,
               min(value) AS vmin, max(value) AS vmax, avg(value) AS vmean,
               count(*) FILTER (WHERE value < {lo_ok}) AS n_below,
               count(*) FILTER (WHERE value > {hi_ok}) AS n_above,
               count(*) - count(DISTINCT (date, lat, lon)) AS n_duplicates,
               count(DISTINCT (lat, lon)) AS n_cells,
               count(DISTINCT date) AS n_months,
               min(date) AS first_date, max(date) AS last_date,
               count(*) FILTER (WHERE day(date) <> 1) AS n_not_first_of_month,
               any_value(grid_hash) AS grid_hash,
               (SELECT min(n) FROM per_month p WHERE p.model = d.model AND p.scen = d.scen) AS min_cells_month,
               (SELECT max(n) FROM per_month p WHERE p.model = d.model AND p.scen = d.scen) AS max_cells_month
        FROM d JOIN grids USING (model, scen)
        GROUP BY ALL ORDER BY model, scen
    """).df()

    ref_hash = g["grid_hash"].mode()[0]
    ref_cells = int(g.loc[g["grid_hash"] == ref_hash, "n_cells"].iloc[0])
    rows = []

    def add(model, scen, check, value, expected, ok, warn_only=False, note=""):
        status = "PASS" if ok else ("WARN" if warn_only else "FAIL")
        rows.append({"var": var, "model": model, "scen": scen, "check": check, "value": value,
                     "expected": expected, "status": status, "note": note})

    # Coverage: every model x scenario present
    expected_pairs = {(m, s) for m in MODELS for s in ["historical", *SCENARIOS]}
    missing = sorted(expected_pairs - set(zip(g["model"], g["scen"])))
    add("ALL", "ALL", "model_scen_coverage", len(expected_pairs) - len(missing), len(expected_pairs),
        not missing, note=f"missing: {missing}" if missing else "")
    add("ALL", "ALL", "unique_grids", g["grid_hash"].nunique(), 1, g["grid_hash"].nunique() == 1)

    for r in g.itertuples():
        hist = r.scen == "historical"
        y0, y1 = HIST_PERIOD if hist else FUTURE_PERIOD
        exp_months = N_MONTHS_HIST if hist else N_MONTHS_FUTURE
        add(r.model, r.scen, "null_value", r.null_value, 0, r.null_value == 0)
        add(r.model, r.scen, "null_keys", r.null_keys, 0, r.null_keys == 0)
        add(r.model, r.scen, "value_min", round(r.vmin, 3), f">= {lo_ok}", r.n_below == 0,
            note=f"{r.n_below} values below" if r.n_below else "")
        add(r.model, r.scen, "value_max", round(r.vmax, 3), f"<= {hi_ok}", r.n_above == 0, warn_only=True,
            note=f"{r.n_above} values above" if r.n_above else "")
        add(r.model, r.scen, "value_mean", round(r.vmean, 3), "info", True)
        add(r.model, r.scen, "duplicates", r.n_duplicates, 0, r.n_duplicates == 0)
        add(r.model, r.scen, "n_cells", r.n_cells, ref_cells, r.n_cells == ref_cells)
        add(r.model, r.scen, "same_grid", r.grid_hash == ref_hash, True, r.grid_hash == ref_hash)
        add(r.model, r.scen, "cells_every_month", f"{r.min_cells_month}-{r.max_cells_month}", r.n_cells,
            r.min_cells_month == r.max_cells_month == r.n_cells)
        add(r.model, r.scen, "dates_first_of_month", r.n_not_first_of_month, 0, r.n_not_first_of_month == 0)
        add(r.model, r.scen, "date_range", f"{r.first_date:%Y-%m}..{r.last_date:%Y-%m}",
            f"{y0}-01..{y1}-12", r.first_date.year == y0 and r.last_date.year == y1)
        add(r.model, r.scen, "n_months", r.n_months, exp_months, r.n_months == exp_months, warn_only=True,
            note="" if r.n_months == exp_months
            else f"{exp_months - r.n_months} month(s) missing, last = {r.last_date:%Y-%m}")

    # Analysis windows: the baseline (historical runs) and each projection window (RCP runs)
    # must be fully covered, i.e. 12 months x every year x every cell
    windows = {"baseline": BASELINE, **FUTURE_WINDOWS}
    win = con.execute(" UNION ALL ".join(f"""
        SELECT model, scen, '{name}' AS window, {y0} AS y0, {y1} AS y1,
               count(DISTINCT date) AS n_months, count(*) AS n_rows
        FROM d WHERE year BETWEEN {y0} AND {y1}
          AND scen {"=" if name == "baseline" else "<>"} 'historical'
        GROUP BY ALL""" for name, (y0, y1) in windows.items())).df()
    for r in g.itertuples():
        for name, (y0, y1) in windows.items():
            if (name == "baseline") != (r.scen == "historical"):
                continue
            w = win[(win["model"] == r.model) & (win["scen"] == r.scen) & (win["window"] == name)]
            n = int(w["n_months"].iloc[0]) if len(w) else 0
            exp = (y1 - y0 + 1) * 12
            add(r.model, r.scen, f"window_{name}", n, exp, n == exp, warn_only=True,
                note=f"{y0}-{y1}" + ("" if n == exp else f": {exp - n} month(s) missing"))

    return pd.DataFrame(rows)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--var", default=ACTIVE_VARIABLE, choices=list(VARIABLES))
    report = run_checks(p.parse_args().var)

    OUT_TABLES.mkdir(parents=True, exist_ok=True)
    out = OUT_TABLES / "sanity_report.csv"
    report.to_csv(out, index=False)

    pd.set_option("display.width", 250)
    print(report["status"].value_counts().to_string(), "\n")
    print(report.pivot_table(index=["model", "scen"], columns="check", values="status", aggfunc="first")
          .fillna("").to_string())
    issues = report[report["status"] != "PASS"]
    if len(issues):
        print("\nIssues:\n" + issues.to_string(index=False))
    print(f"\nReport -> {out}")
    sys.exit(1 if (report["status"] == "FAIL").any() else 0)
