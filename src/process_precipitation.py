from __future__ import annotations

import pandas as pd

from src.config import (
    DATA_PROCESSED,
    SEASONS,
)


# --------------------------------------------------
# 1. LOAD DATA
# --------------------------------------------------

def load_data():
    climate_path = DATA_PROCESSED / "climate_precip.parquet"
    regions_path = DATA_PROCESSED / "grid_regions.parquet"

    climate = pd.read_parquet(climate_path)
    regions = pd.read_parquet(regions_path)

    # Ensure consistent date and coordinate formats
    climate["date"] = pd.to_datetime(climate["date"])

    for df in (climate, regions):
        df["lat"] = df["lat"].round(3)
        df["lon"] = df["lon"].round(3)

    # Check that each coordinate has only one regional assignment
    if regions.duplicated(["lat", "lon"]).any():
        raise ValueError("Duplicate coordinates found in grid_regions.parquet")

    print(f"Climate records loaded: {len(climate):,}")
    print(f"Regional grid cells loaded: {len(regions):,}")

    return climate, regions


# --------------------------------------------------
# 2. ANNUAL PRECIPITATION
# --------------------------------------------------

def calculate_annual(climate):

    keys = ["model", "scen", "var", "year", "lat", "lon"]

    annual = (
        climate.groupby(keys, observed=True)
        .agg(
            value=("value", "sum"),
            n_months=("month", "nunique"),
            n_records=("month", "size"),
        )
        .reset_index()
    )

    # Keep only years with all 12 distinct monthly records
    annual = annual[
        (annual["n_months"] == 12)
        & (annual["n_records"] == 12)
    ].copy()

    annual["frequency"] = "annual"

    print(f"Complete annual records: {len(annual):,}")

    return annual


# --------------------------------------------------
# 3. SEASONAL PRECIPITATION
# --------------------------------------------------

def calculate_seasonal(climate):

    # Create month -> season mapping from config.py
    month_to_season = {
        month: season
        for season, months in SEASONS.items()
        for month in months
    }

    if len(month_to_season) != 12:
        raise ValueError("SEASONS must cover all 12 months exactly once")

    seasonal = climate.copy()

    seasonal["season"] = seasonal["month"].map(month_to_season)

    # December belongs to the following year's DJF.
    seasonal["season_year"] = (
        seasonal["year"] + (seasonal["month"] == 12).astype(int)
    )

    keys = [
        "model",
        "scen",
        "var",
        "season_year",
        "season",
        "lat",
        "lon",
    ]

    seasonal = (
        seasonal.groupby(keys, observed=True)
        .agg(
            value=("value", "sum"),
            n_months=("month", "nunique"),
            n_records=("month", "size"),
        )
        .reset_index()
    )

    # Keep only seasons with all three distinct monthly records
    seasonal = seasonal[
        (seasonal["n_months"] == 3)
        & (seasonal["n_records"] == 3)
    ].copy()

    seasonal = seasonal.rename(columns={"season_year": "year"})
    seasonal["frequency"] = "seasonal"

    print(f"Complete seasonal records: {len(seasonal):,}")

    return seasonal


# --------------------------------------------------
# 4. ASSIGN REGIONS AND CALCULATE WEIGHTED MEANS
# --------------------------------------------------

def calculate_regional(cell_data, regions, frequency):

    # Join each climate grid cell to its region and weight
    merged = cell_data.merge(
        regions[["lat", "lon", "region", "weight"]],
        on=["lat", "lon"],
        how="left",
        validate="many_to_one",
    )

    if merged["region"].isna().any():
        missing = merged.loc[
            merged["region"].isna(), ["lat", "lon"]
        ].drop_duplicates()

        raise ValueError(
            f"{len(missing)} climate grid cells have no regional assignment"
        )

    # Weighted precipitation
    merged["weighted_value"] = merged["value"] * merged["weight"]

    keys = ["model", "scen", "var", "year", "region"]

    if frequency == "seasonal":
        keys.append("season")

    regional = (
        merged.groupby(keys, observed=True)
        .agg(
            weighted_sum=("weighted_value", "sum"),
            weight_sum=("weight", "sum"),
            n_cells=("value", "size"),
        )
        .reset_index()
    )

    regional["value"] = (
        regional["weighted_sum"] / regional["weight_sum"]
    )

    regional["frequency"] = frequency

    # Verify that every region has its expected number of grid cells
    expected_counts = regions["region"].value_counts().to_dict()

    for region, expected in expected_counts.items():
        actual = regional.loc[
            regional["region"] == region, "n_cells"
        ]

        if not actual.eq(expected).all():
            raise ValueError(
                f"{frequency}: unexpected cell count in {region}. "
                f"Expected {expected}, found {actual.unique().tolist()}"
            )

    return regional.drop(columns=["weighted_sum"])


# --------------------------------------------------
# 5. MAIN PIPELINE
# --------------------------------------------------

def main():

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    climate, regions = load_data()

    print("\nCalculating annual precipitation...")
    annual = calculate_annual(climate)

    print("\nCalculating seasonal precipitation...")
    seasonal = calculate_seasonal(climate)

    print("\nCalculating regional annual precipitation...")
    regional_annual = calculate_regional(
        annual, regions, "annual"
    )

    print("\nCalculating regional seasonal precipitation...")
    regional_seasonal = calculate_regional(
        seasonal, regions, "seasonal"
    )

    # Save outputs
    annual_path = DATA_PROCESSED / "precip_annual.parquet"
    seasonal_path = DATA_PROCESSED / "precip_seasonal.parquet"
    regional_path = DATA_PROCESSED / "precip_regional.parquet"

    annual.to_parquet(annual_path, index=False)
    seasonal.to_parquet(seasonal_path, index=False)

    regional = pd.concat(
        [regional_annual, regional_seasonal],
        ignore_index=True,
        sort=False,
    )

    regional.to_parquet(regional_path, index=False)

    print("\nSTEP 4 COMPLETED")
    print("------------------------------")
    print(f"Annual:   {len(annual):,} records")
    print(f"Seasonal: {len(seasonal):,} records")
    print(f"Regional: {len(regional):,} records")

    print("\nGenerated files:")
    print(annual_path)
    print(seasonal_path)
    print(regional_path)


if __name__ == "__main__":
    main()