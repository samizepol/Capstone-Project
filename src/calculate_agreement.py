
import pandas as pd

from src.config import OUT_TABLES, MODELS


def calculate_agreement():
    input_path = OUT_TABLES / "change_by_region.csv"
    data = pd.read_csv(input_path)

    results = []

    dimensions = [
        "frequency",
        "window",
        "scen",
        "region",
    ]

    if "season" in data.columns:
        data["season"] = data["season"].fillna("annual")
        dimensions.append("season")

    for keys, group in data.groupby(dimensions):
        if not isinstance(keys, tuple):
            keys = (keys,)

        metadata = dict(zip(dimensions, keys))

        # Check that all four models are present
        group = group.drop_duplicates(subset=["model"])

        if set(group["model"]) != set(MODELS):
            print("WARNING: Missing models:", metadata)
            continue

        positive = (group["change_mm"] > 0).sum()
        negative = (group["change_mm"] < 0).sum()
        unchanged = (group["change_mm"] == 0).sum()

        if positive > negative:
            direction = "increase"
            agreement_count = positive
        elif negative > positive:
            direction = "decrease"
            agreement_count = negative
        else:
            direction = "mixed"
            agreement_count = max(positive, negative)

        results.append({
            **metadata,
            "agreement_direction": direction,
            "agreement_count": int(agreement_count),
            "agreement_pct": agreement_count / len(MODELS) * 100,
            "positive_models": int(positive),
            "negative_models": int(negative),
            "unchanged_models": int(unchanged),
            "n_models": len(MODELS),
        })

    agreement = pd.DataFrame(results)

    output_path = OUT_TABLES / "agreement.csv"
    agreement.to_csv(output_path, index=False)

    print(f"Agreement saved: {output_path}")
    print(f"Total records: {len(agreement)}")

    print("\nAgreement distribution:")
    print(
        agreement.groupby(
            ["frequency", "agreement_count"]
        ).size().to_string()
    )

    return agreement


if __name__ == "__main__":
    calculate_agreement()
