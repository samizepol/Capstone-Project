
import pandas as pd

from src.config import (
    DATA_PROCESSED,
    OUT_TABLES,
    APP_DATA,
    HIST_PERIOD,
    PROJECTION_PERIOD,
)


def prepare_regional_precipitation():
    """Prepare historical and projected regional precipitation."""

    data = pd.read_parquet(
        DATA_PROCESSED / "precip_regional.parquet"
    )

    historical = data[
        (data["scen"] == "historical")
        & data["year"].between(*HIST_PERIOD)
    ]

    future = data[
        (data["scen"].isin(["RCP45", "RCP85"]))
        & data["year"].between(*PROJECTION_PERIOD)
    ]

    result = pd.concat(
        [historical, future],
        ignore_index=True
    )

    result = result.sort_values(
        ["frequency", "region", "model", "scen", "year"]
    )

    output = APP_DATA / "regional_precipitation.csv"
    result.to_csv(output, index=False)

    print(f"Regional precipitation: {len(result)} rows")


def prepare_changes():
    """Prepare regional precipitation changes."""

    data = pd.read_csv(
        OUT_TABLES / "change_by_region.csv"
    )

    output = APP_DATA / "change_by_region.csv"
    data.to_csv(output, index=False)

    print(f"Regional changes: {len(data)} rows")


def prepare_trends():
    """Prepare Mann-Kendall and Sen's slope results."""

    data = pd.read_csv(
        OUT_TABLES / "trends.csv"
    )

    output = APP_DATA / "trends.csv"
    data.to_csv(output, index=False)

    print(f"Trend results: {len(data)} rows")


def prepare_agreement():
    """Prepare model agreement results."""

    data = pd.read_csv(
        OUT_TABLES / "agreement.csv"
    )

    output = APP_DATA / "agreement.csv"
    data.to_csv(output, index=False)

    print(f"Model agreement: {len(data)} rows")


def main():
    APP_DATA.mkdir(parents=True, exist_ok=True)

    print("Preparing dashboard datasets...\n")

    prepare_regional_precipitation()
    prepare_changes()
    prepare_trends()
    prepare_agreement()

    print("\nDashboard datasets generated successfully.")

    print("\nGenerated files:")
    for file in sorted(APP_DATA.glob("*.csv")):
        print(f"- {file.name} ({file.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
