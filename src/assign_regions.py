"""Step 3: assign every grid cell to a department and a region (Chaco / Oriental) + cos(lat) weight.

Needs: data/external/departamentos/PRY_ADM1.geojson and data/processed/climate_{var}.parquet
Output: data/processed/grid_regions.parquet with columns
    lat, lon, department, region, weight, assigned_by, dist_km

A cell is assigned to the department polygon that contains it. Cells outside every polygon
(coast/border) get the nearest department (assigned_by = 'nearest', distance in dist_km).

Run from the project root:
    python -m src.assign_regions
"""
import argparse
import unicodedata

import duckdb
import geopandas as gpd
import numpy as np
from src.config import (DATA_PROCESSED, VARIABLES, ACTIVE_VARIABLE, DEPARTMENTS_FILE, DEPARTMENT_NAME_FIELD,
                        CHACO_DEPARTMENTS, CHACO_LABEL, ORIENTAL_LABEL)

PROJECTED_CRS = "EPSG:32721"   # UTM 21S (metres), used only to measure distances


def norm(name):
    """'Boquerón' and 'BOQUERON' both -> 'BOQUERON' (strip accents, uppercase)."""
    return unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().strip().upper()


def assign_regions(var):
    pq = DATA_PROCESSED / f"climate_{var}.parquet"
    cells = duckdb.sql(f"SELECT DISTINCT lat, lon FROM '{pq.as_posix()}' ORDER BY lat, lon").df()

    deps = gpd.read_file(DEPARTMENTS_FILE).to_crs("EPSG:4326")
    deps["department"] = deps[DEPARTMENT_NAME_FIELD]
    deps["_key"] = deps["department"].map(norm)
    chaco_keys = {norm(d) for d in CHACO_DEPARTMENTS}
    if chaco_keys - set(deps["_key"]):
        raise SystemExit(f"Not found in {DEPARTMENTS_FILE.name}: {sorted(chaco_keys - set(deps['_key']))}. "
                         f"Available: {sorted(deps['department'])}")

    pts = gpd.GeoDataFrame(cells, geometry=gpd.points_from_xy(cells["lon"], cells["lat"]), crs="EPSG:4326")
    cols = ["department", "_key", "geometry"]

    # 1) polygon that contains the cell (a cell exactly on a shared border matches twice: keep the first)
    j = gpd.sjoin(pts, deps[cols], how="left", predicate="within")
    j = j[~j.index.duplicated(keep="first")]
    j["assigned_by"] = np.where(j["department"].notna(), "within", "")
    j["dist_km"] = 0.0

    # 2) cells outside every polygon -> nearest department
    out = j["department"].isna()
    if out.any():
        near = gpd.sjoin_nearest(pts.loc[out].to_crs(PROJECTED_CRS), deps[cols].to_crs(PROJECTED_CRS),
                                 how="left", distance_col="d_m")
        near = near[~near.index.duplicated(keep="first")]
        j.loc[out, ["department", "_key"]] = near[["department", "_key"]]
        j.loc[out, "assigned_by"] = "nearest"
        j.loc[out, "dist_km"] = near["d_m"] / 1000.0

    j["region"] = np.where(j["_key"].isin(chaco_keys), CHACO_LABEL, ORIENTAL_LABEL)
    j["weight"] = np.cos(np.radians(j["lat"]))
    res = j[["lat", "lon", "department", "region", "weight", "assigned_by", "dist_km"]].reset_index(drop=True)

    assert len(res) == len(cells) and res["department"].notna().all()
    assert not res.duplicated(["lat", "lon"]).any()
    out_path = DATA_PROCESSED / "grid_regions.parquet"
    res.to_parquet(out_path, index=False)

    print(f"Wrote {out_path.relative_to(DATA_PROCESSED.parents[1])}: {len(res)} cells")
    print("\nCells per region:\n" + res["region"].value_counts().to_string())
    print("\nCells per department:\n" + res.groupby(["region", "department"]).size().to_string())
    print(f"\nCells outside every polygon (assigned to nearest): {(res['assigned_by'] == 'nearest').sum()}")
    if (res["assigned_by"] == "nearest").any():
        print(f"  max distance: {res.loc[res['assigned_by'] == 'nearest', 'dist_km'].max():.1f} km")
    return res


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--var", default=ACTIVE_VARIABLE, choices=list(VARIABLES))
    assign_regions(p.parse_args().var)
