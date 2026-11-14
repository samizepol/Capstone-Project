
import pandas as pd
import numpy as np
from scipy.stats import kendalltau, theilslopes

from src.config import (
    DATA_PROCESSED,
    OUT_TABLES,
    FUTURE_WINDOWS,
    MODELS,
    SCENARIOS,
)

ALPHA = 0.05


def analyze_series(group):
    """Calculate Mann-Kendall and Sen's slope for one time series."""

    group = group.sort_values("year").dropna(subset=["value"])

    x = group["year"].to_numpy(dtype=float)
    y = group["value"].to_numpy(dtype=float)

    if len(y) < 3 or np.all(y == y[0]):
        return {
            "n_years": len(y),
            "kendall_tau": np.nan,
            "p_value": np.nan,
            "sen_slope": np.nan,
            "trend": "insufficient_or_constant",
        }

    tau, p_value = kendalltau(x, y)
    slope, intercept, low, high = theilslopes(y, x)

    if p_value < ALPHA:
        if slope > 0:
            trend = "increasing"
        elif slope < 0:
            trend = "decreasing"
        else:
            trend = "no_trend"
    else:
        trend = "no_significant_trend"

    return {
        "n_years": len(y),
        "kendall_tau": tau,
        "p_value": p_value,
        "sen_slope": slope,
        "sen_slope_low": low,
        "sen_slope_high": high,
        "trend": trend,
    }

def prepare_data():
    path = DATA_PROCESSED / "precip_regional.parquet"

    data = pd.read_parquet(path)

    data = data[
        (data["scen"].isin(SCENARIOS))
        & (data["model"].isin(MODELS))
        & (data["region"].isin(["Chaco", "Oriental"]))
    ].copy()

    return data

def run_analysis():
    results = []

    data = prepare_data()

    for frequency in ["annual", "seasonal"]:
        frequency_data = data[
            data["frequency"] == frequency
        ].copy()

        for window, (start, end) in FUTURE_WINDOWS.items():
            period_data = frequency_data[
                frequency_data["year"].between(start, end)
            ].copy()

            dimensions = [
                "model",
                "scen",
                "region",
            ]

            if frequency == "seasonal":
                dimensions.append("season")

            for keys, group in period_data.groupby(dimensions):
                if not isinstance(keys, tuple):
                    keys = (keys,)

                metadata = dict(zip(dimensions, keys))
                metrics = analyze_series(group)

                results.append({
                    **metadata,
                    "frequency": frequency,
                    "window": window,
                    "period_start": start,
                    "period_end": end,
                    **metrics,
                })

    trends = pd.DataFrame(results)

    OUT_TABLES.mkdir(parents=True, exist_ok=True)

    output_path = OUT_TABLES / "trends.csv"
    trends.to_csv(output_path, index=False)

    print(f"Trend analysis saved: {output_path}")
    print(f"Total records: {len(trends)}")

    print("\nTrend classification:")
    print(
        trends.groupby(
            ["frequency", "window", "trend"]
        ).size().to_string()
    )

    return trends


if __name__ == "__main__":
    run_analysis()
