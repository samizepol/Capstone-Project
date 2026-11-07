"""Step 3 check: map of the grid colored by region -> outputs/figures/region_map.png

Run from the project root:  python -m src.plot_region_map
"""
import geopandas as gpd
import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from src.config import DATA_PROCESSED, OUT_FIGURES, DEPARTMENTS_FILE, CHACO_LABEL, ORIENTAL_LABEL

grid = pd.read_parquet(DATA_PROCESSED / "grid_regions.parquet")
deps = gpd.read_file(DEPARTMENTS_FILE)

fig, ax = plt.subplots(figsize=(7, 8))
deps.boundary.plot(ax=ax, color="#555555", linewidth=0.8)
colors = {CHACO_LABEL: "#d95f02", ORIENTAL_LABEL: "#1b9e77"}
for region, sub in grid.groupby("region"):
    ax.scatter(sub["lon"], sub["lat"], s=14, c=colors[region], label=f"{region} ({len(sub)} cells)")
near = grid[grid["assigned_by"] == "nearest"]
if len(near):
    ax.scatter(near["lon"], near["lat"], s=70, facecolors="none", edgecolors="k",
               label=f"assigned by nearest ({len(near)})")
ax.set(title="Grid cells by region", xlabel="Longitude", ylabel="Latitude")
ax.legend(loc="lower left")
OUT_FIGURES.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT_FIGURES / "region_map.png", dpi=150, bbox_inches="tight")
print("saved", (OUT_FIGURES / "region_map.png").relative_to(OUT_FIGURES.parents[1]))
