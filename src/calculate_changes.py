import pandas as pd

from src.config import (
    DATA_PROCESSED,
    OUT_TABLES,
    BASELINE,
    FUTURE_WINDOWS,
)


# --------------------------------------------------
# 1. CALCULATE CHANGE METRICS
# --------------------------------------------------

def calculate_changes(data, dimensions, frequency):

    data = data[data["frequency"] == frequency].copy()

    # Seasonal calculations must keep each season separate
    if frequency == "seasonal":
        dimensions = dimensions + ["season"]

    keys = ["model"] + dimensions

    # Historical baseline: 1976-2005
    baseline_data = data[
        (data["scen"] == "historical")
        & data["year"].between(BASELINE[0], BASELINE[1])
    ]

    baseline = (
        baseline_data.groupby(keys, observed=True)
        .agg(
            baseline_mean=("value", "mean"),
            baseline_n_years=("year", "nunique"),
        )
        .reset_index()
    )

    results = []

    # Compare each future window separately
    for window_name, (start_year, end_year) in FUTURE_WINDOWS.items():

        future_data = data[
            (data["scen"].isin(["RCP45", "RCP85"]))
            & data["year"].between(start_year, end_year)
        ]

        future = (
            future_data.groupby(
                keys + ["scen"], observed=True
            )
            .agg(
                future_mean=("value", "mean"),
                future_n_years=("year", "nunique"),
            )
            .reset_index()
        )

        # Match each future result with its model's historical baseline
        changes = future.merge(
            baseline,
            on=keys,
            how="left",
            validate="many_to_one",
        )

        if changes["baseline_mean"].isna().any():
            raise ValueError(
                f"Missing historical baseline for {frequency}"
            )

        changes["window"] = window_name
        changes["period_start"] = start_year
        changes["period_end"] = end_year

        # Absolute and relative changes
        changes["change_mm"] = (
            changes["future_mean"] - changes["baseline_mean"]
        )

        changes["change_pct"] = (
            changes["change_mm"] / changes["baseline_mean"] * 100
        )

        # Avoid division by zero
        changes.loc[
            changes["baseline_mean"] == 0, "change_pct"
        ] = float("nan")

        changes["frequency"] = frequency

        results.append(changes)

    if not results:
        return pd.DataFrame()

    return pd.concat(results, ignore_index=True)


# --------------------------------------------------
# 2. MAIN PIPELINE
# --------------------------------------------------

def main():

    OUT_TABLES.mkdir(parents=True, exist_ok=True)

    annual = pd.read_parquet(
        DATA_PROCESSED / "precip_annual.parquet"
    )

    seasonal = pd.read_parquet(
        DATA_PROCESSED / "precip_seasonal.parquet"
    )

    regional = pd.read_parquet(
        DATA_PROCESSED / "precip_regional.parquet"
    )

    print("Calculating cell-level changes...")

    # Annual cell-level changes
    annual_cells = calculate_changes(
        annual,
        dimensions=["lat", "lon"],
        frequency="annual",
    )

    # Seasonal cell-level changes
    seasonal_cells = calculate_changes(
        seasonal,
        dimensions=["lat", "lon"],
        frequency="seasonal",
    )

    change_by_cell = pd.concat(
        [annual_cells, seasonal_cells],
        ignore_index=True,
        sort=False,
    )

    # Save cell-level results
    cell_path = DATA_PROCESSED / "change_by_cell.parquet"

    change_by_cell.to_parquet(cell_path, index=False)

    print("Calculating regional changes...")

    # Annual regional changes
    annual_regions = calculate_changes(
        regional,
        dimensions=["region"],
        frequency="annual",
    )

    # Seasonal regional changes
    seasonal_regions = calculate_changes(
        regional,
        dimensions=["region"],
        frequency="seasonal",
    )

    change_by_region = pd.concat(
        [annual_regions, seasonal_regions],
        ignore_index=True,
        sort=False,
    )

    # Save regional results
    region_path = OUT_TABLES / "change_by_region.csv"

    change_by_region.to_csv(region_path, index=False)

    print("\nSTEP 5 COMPLETED")
    print("--------------------------------")
    print(f"Cell-level records: {len(change_by_cell):,}")
    print(f"Regional records:   {len(change_by_region):,}")

    print("\nGenerated files:")
    print(cell_path)
    print(region_path)

    print("\nRegional results preview:")
    print(
        change_by_region[
            [
                "model",
                "scen",
                "region",
                "frequency",
                "season",
                "window",
                "baseline_mean",
                "future_mean",
                "change_mm",
                "change_pct",
                "future_n_years",
            ]
        ].head(12).to_string(index=False)
    )


if __name__ == "__main__":
    main()