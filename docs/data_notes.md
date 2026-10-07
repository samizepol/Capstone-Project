# Data notes

Source: datos.gov.py climate projections for Paraguay, saved in `data/raw/` (not in git).
Inventory: `python -m src.inventory` → `outputs/tables/file_inventory.csv`.
Unit check by hand: `notebooks/01_inventory_checks.ipynb`.

## Files

12 CSVs, named `{MODEL}_{SCENARIO}_{VARIABLE}_{START}_{END}_PY.csv`:

| Model (file / config) | historical 1961–2005 | RCP45 2006–2099 | RCP85 2006–2099 |
|---|---|---|---|
| BESM / BESM | ✅ | ✅ | ✅ |
| CANESM2 / CanESM2 | ✅ | ✅ | ✅ |
| HADGEM2-ES / HadGEM2-ES | ✅ | ⚠️ 1127 months | ✅ |
| MIROC5 / MIROC5 | ✅ | ✅ | ✅ |

- Variable: only `PREC` (precipitation) so far.
- The historical scenario is labelled `HISTORICO` in filenames; the inventory maps it to `historical`.
- Model names are uppercase in filenames; the inventory maps them to the names in `src/config.py`.

### Two column layouts

| Files | Columns | Date format | Quoting |
|---|---|---|---|
| `*_HISTORICO_*` | `Data, Hora, Latitude, Longitude, PREC` | `1961/01/01` | none |
| `*_RCP45_*`, `*_RCP85_*` | `Fecha, Latitud, Longitud, PREC` | `2006-01-01` | header and date quoted; some files (CANESM2_RCP45, MIROC5_RCP85) quote every field |

- `Hora` is always `00:00:00` and can be dropped.
- Always select columns **by name**, never by position, because the extra `Hora` column shifts the positions.
- When combining files, convert both date formats to a real date.

## Findings

- **Precipitation units: mm/month (monthly total).**
  - Mean `PREC` in BESM historical is 65.7 (min 0, max 472, no nulls).
  - Read as mm/month, that is about 790 mm/yr on average. Read as mm/day it would be about 24,000 mm/yr, which is impossible.
  - Annual totals per cell follow the expected gradient: about 570 mm/yr in the west (lon < −58°, Chaco) and about 1,050 mm/yr in the east (range 480–1,490).
  - The seasonal cycle is correct: wettest in Oct–Jan (87–103 mm) and driest in Jun–Aug (33–47 mm).
  - All 12 files have plausible means (54–76 mm/month).
  - → To get annual rainfall, **sum** the monthly values.
- **Calendars per model:** every file has one value per cell per month, always dated the 1st, with no Feb‑29 rows. The models' native calendars (e.g. HadGEM2-ES 360-day) are therefore hidden by the monthly aggregation, so no calendar handling is needed.
- **Grid consistency:** all 12 files share the same grid of 882 cells (0.2° spacing, lat −27.4 to −19.4, lon −62.6 to −54.4). Row order differs between layouts, so join on lat/lon, not on row position.
- **Month counts (1128 / 540):**
  - All historical files have 540 months (1961-01 to 2005-12).
  - 7 of 8 future files have 1128 months (2006-01 to 2099-12).
  - **HadGEM2-ES RCP45 has 1127 months: December 2099 is missing.** It has 994,014 rows instead of 994,896, and every month present is complete.
- **Completeness:** in every file, rows = months × 882 cells, with no nulls and no negative values.

## Analysis periods

Defined in `src/config.py`:

| Period | Years | Length | Data used |
|---|---|---|---|
| Baseline | 1976–2005 | 30 yrs | historical runs |
| **mid** term | **2027–2063** | 37 yrs | RCP45 / RCP85 |
| **end** term | **2064–2099** | 36 yrs | RCP45 / RCP85 |

- Projections start in **2027**. 2006–2026 is kept in the Parquet file (the data checks need it) but is not part of any projection term.
- The two terms are contiguous (no gap or overlap) and each is over 30 years, the usual minimum for a climate average.
- `sanity_checks.py` checks that every run fully covers its windows. Only HadGEM2-ES RCP45 `end` gets a WARN: 431 of 432 months, because 2099-12 is missing.

## Step 2: Parquet and sanity checks

- `python -m src.convert_to_parquet [--var precip]` writes `data/processed/climate_precip.parquet`.
  - One tidy table: `model, scen, var, date, year, month, lat, lon, value`. `scen` is `historical`, `RCP45` or `RCP85`; `value` is in mm/month.
  - 9,863,406 rows, the same count as the raw CSVs (the script checks this). The size drops from about 470 MB of CSV to 47 MB.
  - lat/lon are rounded to 3 decimals so cells join exactly across files.
- `python -m src.sanity_checks [--var precip]` writes `outputs/tables/sanity_report.csv` (one row per model × scen × check).
  - Statuses: PASS, WARN or FAIL. The script exits with code 1 if anything FAILs.
  - Result: 145 PASS and 1 WARN (HadGEM2-ES RCP45 is missing 2099-12, as already known).
  - No nulls, negative values or duplicate (date, cell) rows; every model and scenario uses the same 882-cell grid; every month has all cells.
  - The checks were tested on a deliberately corrupted copy, and every injected problem was caught.
- `notebooks/02_sanity_review.ipynb` plots value ranges, the seasonal cycle and annual totals.
  - Monthly values run from 0 to 676 mm/month, below the plausible limit of 1,500 mm/month (`PLAUSIBLE_RANGE` in `config.py`).
  - **HadGEM2-ES has a weak dry season**: about 45–65 mm/month in Jun–Aug, against about 20–35 mm/month in the other three models.
  - Mean levels differ by model, so each model's future is compared with its own 1976–2005 baseline.

## Open questions for advisor

- HadGEM2-ES has a weak Jun–Aug dry season compared with the other models. Should its JJA results be flagged as less reliable?

- HadGEM2-ES RCP45 is missing 2099-12. Should we download it again, end the "end" term (2064–2099) at 2099-11 for every model, or accept 11 months in that model's final year?
- The eastern region looks dry: about 1,050 mm/yr in the BESM historical run versus roughly 1,500+ mm/yr observed. Should we bias-correct, or rely only on relative change (future vs 1976–2005 baseline)?
- The data portal's metadata does not state the unit. Can mm/month be confirmed from the portal documentation?
