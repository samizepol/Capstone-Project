
import pandas as pd
import matplotlib.pyplot as plt

from src.config import (
    DATA_PROCESSED,
    OUT_TABLES,
    OUT_FIGURES,
    MODELS,
    BASELINE,
    PROJECTION_PERIOD,
)


def load_data():
    regional = pd.read_parquet(
        DATA_PROCESSED / "precip_regional.parquet"
    )

    changes = pd.read_csv(
        OUT_TABLES / "change_by_region.csv"
    )

    trends = pd.read_csv(
        OUT_TABLES / "trends.csv"
    )

    agreement = pd.read_csv(
        OUT_TABLES / "agreement.csv"
    )

    return regional, changes, trends, agreement


def plot_annual_precipitation(data):
    annual = data[data["frequency"] == "annual"].copy()

    fig, axes = plt.subplots(4, 2, figsize=(15, 18))

    scenarios = {
        "historical": ("Historical", "black", "-"),
        "RCP45": ("RCP45", "blue", "--"),
        "RCP85": ("RCP85", "red", "--"),
    }

    for i, model in enumerate(MODELS):
        for j, region in enumerate(["Chaco", "Oriental"]):
            ax = axes[i, j]

            subset = annual[
                (annual["model"] == model)
                & (annual["region"] == region)
            ]

            for scenario, (label, color, style) in scenarios.items():
                selected = subset[subset["scen"] == scenario].copy()

            if scenario == "historical":
                selected = selected[
                    selected["year"].between(1961, 2005)
                ]
            else:
                selected = selected[
                    selected["year"].between(
                        PROJECTION_PERIOD[0],
                        PROJECTION_PERIOD[1]
                    )
                ]

                ax.plot(
                    selected["year"],
                    selected["value"],
                    color=color,
                    linestyle=style,
                    linewidth=1.2,
                    label=label
                )

            ax.set_title(f"{model} - {region}")
            ax.set_xlabel("Year")
            ax.set_ylabel("Precipitation (mm/year)")
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8)

    fig.suptitle(
        "Annual precipitation: Historical and Future Projections",
        fontsize=15
    )

    fig.tight_layout()

    fig.savefig(
        OUT_FIGURES / "annual_precipitation.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close(fig)



def plot_seasonal_precipitation(data):
    seasonal = data[
        data["frequency"] == "seasonal"
    ].copy()

    scenarios = {
        "historical": ("Historical", "black", "-"),
        "RCP45": ("RCP45", "blue", "--"),
        "RCP85": ("RCP85", "red", "--"),
    }

    for model in MODELS:
        fig, axes = plt.subplots(4, 2, figsize=(15, 16))

        for i, season in enumerate(["DJF", "MAM", "JJA", "SON"]):
            for j, region in enumerate(["Chaco", "Oriental"]):
                ax = axes[i, j]

                subset = seasonal[
                    (seasonal["model"] == model)
                    & (seasonal["season"] == season)
                    & (seasonal["region"] == region)
                ]

                for scenario, (label, color, style) in scenarios.items():
                    selected = subset[subset["scen"] == scenario].copy()

                    if scenario == "historical":
                        selected = selected[
                            selected["year"].between(1961, 2005)
                        ]
                    else:
                        selected = selected[
                            selected["year"].between(
                                PROJECTION_PERIOD[0],
                                PROJECTION_PERIOD[1]
                            )
                        ]

                    ax.plot(
                        selected["year"],
                        selected["value"],
                        color=color,
                        linestyle=style,
                        linewidth=1.2,
                        label=label
                    )

                ax.set_title(f"{season} - {region}")
                ax.set_xlabel("Season year")
                ax.set_ylabel("Precipitation (mm/season)")
                ax.grid(True, alpha=0.3)
                ax.legend(fontsize=8)

        fig.suptitle(
            f"{model} - Seasonal precipitation projections",
            fontsize=15
        )

        fig.tight_layout()

        fig.savefig(
            OUT_FIGURES / f"seasonal_precipitation_{model.lower()}.png",
            dpi=300,
            bbox_inches="tight"
        )

        plt.close(fig)

def plot_annual_change(changes):
    annual = changes[
        changes["frequency"] == "annual"
    ].copy()

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for ax, region in zip(axes, ["Chaco", "Oriental"]):
        subset = annual[annual["region"] == region]

        for window in ["mid", "end"]:
            window_data = subset[
                subset["window"] == window
            ]

            labels = [
                f"{row.model}\n{row.scen}"
                for row in window_data.itertuples()
            ]

            ax.bar(
                [f"{window}\n{x}" for x in labels],
                window_data["change_pct"],
                alpha=0.75,
                label=window
            )

        ax.axhline(0, linewidth=0.8)
        ax.set_title(f"{region} - Annual change")
        ax.set_ylabel("Change (%)")
        ax.tick_params(axis="x", labelrotation=90)
        ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(
        OUT_FIGURES / "annual_change.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close(fig)


def plot_seasonal_change(changes):
    seasonal = changes[
        changes["frequency"] == "seasonal"
    ].copy()

    for region in ["Chaco", "Oriental"]:
        region_data = seasonal[
            seasonal["region"] == region
        ]

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        for ax, season in zip(axes.flat, ["DJF", "MAM", "JJA", "SON"]):
            subset = region_data[
                region_data["season"] == season
            ]

            for window in ["mid", "end"]:
                selected = subset[
                    subset["window"] == window
                ]

                for scenario in ["RCP45", "RCP85"]:
                    values = selected[
                        selected["scen"] == scenario
                    ]

                    ax.plot(
                        values["model"],
                        values["change_pct"],
                        marker="o",
                        label=f"{window} {scenario}"
                    )

            ax.axhline(0, linewidth=0.8)
            ax.set_title(season)
            ax.set_ylabel("Change (%)")
            ax.grid(True, alpha=0.3)

        axes[0, 0].legend(fontsize=7)

        fig.suptitle(f"{region} - Seasonal precipitation change")
        fig.tight_layout()

        fig.savefig(
            OUT_FIGURES / f"seasonal_change_{region.lower()}.png",
            dpi=300,
            bbox_inches="tight"
        )
        plt.close(fig)


def plot_trends(trends):
    summary = (
        trends.groupby(["frequency", "window", "trend"])
        .size()
        .unstack(fill_value=0)
    )

    ax = summary.plot(
        kind="bar",
        figsize=(10, 6)
    )

    ax.set_title("Climate precipitation trend analysis")
    ax.set_xlabel("Frequency and period")
    ax.set_ylabel("Number of series")
    ax.legend(title="Trend classification")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig(
        OUT_FIGURES / "trend_analysis.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()



def plot_agreement(agreement):
    summary = (
        agreement.groupby(["frequency", "agreement_count"])
        .size()
        .unstack(fill_value=0)
    )

    ax = summary.plot(
        kind="bar",
        figsize=(10, 6)
    )

    ax.set_title("Agreement among Climate Models")
    ax.set_xlabel("Frequency")
    ax.set_ylabel("Number of cases")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
    ax.legend(title="Models agreeing (out of 4)")
    ax.grid(axis="y", alpha=0.3)

    ax.text(
        0.5,
        -0.25,
        "Note: 2/4 represents a 2–2 split, not a majority consensus.",
        transform=ax.transAxes,
        ha="center",
        fontsize=9
    )

    plt.tight_layout()

    plt.savefig(
        OUT_FIGURES / "model_agreement.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

def main():
    OUT_FIGURES.mkdir(parents=True, exist_ok=True)

    regional, changes, trends, agreement = load_data()

    plot_annual_precipitation(regional)
    plot_seasonal_precipitation(regional)
    plot_annual_change(changes)
    plot_seasonal_change(changes)
    plot_trends(trends)
    plot_agreement(agreement)

    print("Figures generated successfully:")
    for file in sorted(OUT_FIGURES.glob("*.png")):
        print(f"- {file.name}")


if __name__ == "__main__":
    main()
