# CivicFlux dataset acquisition and measurement contracts

Inspected on 2026-10-25. Actual CSVs and publisher metadata snapshots are included locally. Dataset titles are not evidence of units, geographic precision, sensor lineage, or full-year coverage. The notebooks inspect all source rows, then default to Delhi for rainfall/PM2.5 and all four traffic junctions. Set `cfg['selected']=None` to expand a forecast study, and rerun it completely.

## Download instructions

The three requested dataset downloads succeeded through Kaggle's public API without credentials in this session. This may change with Kaggle access controls. No API key is included in these files.

From this project's directory:

```bash
python download_data.py
```

For each dataset, manual download: open its page below, sign in to Kaggle if requested, click **Download**, and extract the ZIP into the corresponding `data/raw/<name>/` directory. Preserve original filenames.

Authenticated fallback: install the official `kaggle` CLI; create credentials in Kaggle account settings and configure them as described by the [official Kaggle API](https://github.com/Kaggle/kaggle-api). Never paste a key into a notebook or commit it.

```bash
kaggle datasets download -d wydoinn/daily-rainfall-data-india-2009-2024 -p data/raw/rainfall --unzip
kaggle datasets download -d aniket0712/delhi-ncr-hourly-air-quality-dataset-20192024 -p data/raw/aqi --unzip
kaggle datasets download -d fedesoriano/traffic-prediction-dataset -p data/raw/traffic --unzip
```

Dataset metadata snapshots are `data/rainfall_source.json`, `data/aqi_source.json`, and `data/traffic_source.json`. Source CSV checksums appear in exported metadata and `reports/data_inventory.json`. A changed upstream download must be treated as a new data version.

## 1. Daily rainfall

- [Dataset page](https://www.kaggle.com/datasets/wydoinn/daily-rainfall-data-india-2009-2024)
- [Direct ZIP API](https://www.kaggle.com/api/v1/datasets/download/wydoinn/daily-rainfall-data-india-2009-2024)
- [Publisher metadata API](https://www.kaggle.com/api/v1/datasets/view/wydoinn/daily-rainfall-data-india-2009-2024)
- Publisher cites [India-WRIS](https://indiawris.gov.in/wris) as the upstream source. These are reported historical observations/aggregates, not our own sensor collection. Upstream aggregation lineage has not been independently audited.
- License listed by publisher: **CC BY-NC-SA 4.0**. Preserve attribution and the source terms; commercial reuse is not established by this research package.
- Actual file: `daily-rainfall-at-state-level.csv`; **204,876 rows × 8 columns**, 36 state/UT names; dates **2009-01-01 through 2024-07-31**.
- Format: CSV, date string `YYYY-MM-DD`. Geographic support is a state/UT, not a station or city drain.

| Field | Meaning / unit | Role |
|---|---|---|
| id | Source row identifier | Audit only |
| date | Labeled observation day | Parse date; daily grid |
| state_code | State/UT code | Audit; no fabricated spatial join |
| state_name | State/UT name | Exact entity identity |
| actual | Actual rainfall, mm per labeled daily interval | History feature; next-day label |
| rfs | Publisher-described forecast rainfall, mm | Excluded: forecast issue time/horizon not provided |
| normal | Historical normal, mm | Excluded: reference period/availability not established |
| deviation | Percent deviation from normal | Excluded: derived outcome leakage risk |

`actual` has **17,162 missing entries** in the complete download. `rfs`, `normal`, and `deviation` are also incomplete. Negative actual values, if present, are made unavailable and counted in the audit; nonnegative extremes are retained. Labels are subsequent real observed `actual` values only. Date boundaries, accumulation windows and reporting latency are not documented in the CSV: Asia/Kolkata and availability after the labeled day are explicit research assumptions.

CivicFlux supplies: next-day state-average rainfall and a real rainfall reference for hypothetical flood scenarios. State-average rainfall is not localized urban storm intensity.

## 2. Delhi NCR hourly air quality

- [Dataset page](https://www.kaggle.com/datasets/aniket0712/delhi-ncr-hourly-air-quality-dataset-20192024)
- [Direct ZIP API](https://www.kaggle.com/api/v1/datasets/download/aniket0712/delhi-ncr-hourly-air-quality-dataset-20192024)
- [Publisher metadata API](https://www.kaggle.com/api/v1/datasets/view/aniket0712/delhi-ncr-hourly-air-quality-dataset-20192024)
- License listed: **CC0: Public Domain**.
- Actual file: `processed_aqi_data.csv`; **219,125 rows × 18 columns**. Time span **2019-01-01 00:00:00 through 2024-01-01 00:00:00**, not the whole of 2024.
- Locations: Delhi, Faridabad, Ghaziabad, Gurgaon and Noida. Coordinates are city representative points, not verified monitoring-station locations.
- Publisher describes measurements but supplies no identifiable sensor/station lineage in this CSV or metadata snapshot. **Real/synthetic/derived provenance remains unverified**; do not describe it as verified CPCB station measurements. The filename itself says processed, but the exact processing is unspecified.

| Fields | Meaning / unit contract | Role |
|---|---|---|
| timestamp | `YYYY-MM-DD HH:MM:SS`, no offset | Hourly axis; Asia/Kolkata assumption |
| location_name | City label | Exact entity |
| location_lat, location_lon | Representative coordinates, assumed decimal degrees | Audit only, no point sensor matching |
| pm25 | PM2.5 concentration | Next-hour target and historical features; µg/m³ is a provisional convention, not source-verified unit metadata |
| pm10 | PM10 concentration | Alternate target if separately configured and units verified |
| co, no2, o3, so2 | Other pollutants; units not specified in metadata | Excluded from models pending unit/latency validation |
| aqi, aqi_category | Derived index/category with undocumented standard | Excluded; never equated with CO₂ emissions |
| hour, day, month, year, day_of_week, is_weekend | Precomputed calendar | Recomputed from parsed target timestamp |

No conversion is applied without knowing the original unit. The exported bundle carries the provisional PM2.5 unit and provenance limitation. Actual next-hour pollutant values supply regression labels; there are no health or infrastructure incident labels. Very complete/processed tables do not prove natural sensor quality. The notebook plots distributions, station-identity absence, temporal coverage and missingness without inventing provenance.

CivicFlux supplies: next-hour PM2.5 concentration in the source scale, with a residual prediction interval. Live operational thresholds require verified units and reporting latency.

## 3. Hourly traffic

- [Dataset page](https://www.kaggle.com/datasets/fedesoriano/traffic-prediction-dataset)
- [Direct ZIP API](https://www.kaggle.com/api/v1/datasets/download/fedesoriano/traffic-prediction-dataset)
- [Publisher metadata API](https://www.kaggle.com/api/v1/datasets/view/fedesoriano/traffic-prediction-dataset)
- Metadata license: **Data files © Original Authors**. Publisher says the source is confidential, for educational use, and asks research users to credit the author. This is not documented as a broadly permissive commercial data license.
- Actual file: `traffic.csv`; **48,120 rows × 4 columns**, four junctions, observations from **2015-11-01 through 2017-06-30**. Junction coverage differs.
- Format: CSV; `DateTime` is `YYYY-MM-DD HH:MM:SS`, `Junction` a categorical identifier, `Vehicles` the number of vehicles observed per hour, `ID` an encoded identifier.
- Target: Vehicles at the same junction exactly one hour ahead. Features: current/past Vehicles, causal windows, target-calendar values and one-hot junction identity. ID is excluded.
- Real sensor observations according to publisher; confidential upstream source prevents independent geographic/sensor verification. City, coordinates and timezone are not established. Preserve naive local time and do not pretend it is UTC or India time.
- No measured speed, road length, travel time, lane capacity, disruption labels or incident reports. Counts are not speed and cannot alone produce travel times.

CivicFlux supplies: one-hour-ahead vehicle count by anonymous junction. The notebook additionally provides a **separate synthetic capacity-loss simulator**; its assumptions and outputs never enter real forecast evaluation.

## 4. Custom flood scenarios

No additional dataset account or API key is needed. Notebook 04 calls the versioned deterministic generator in `civicflux_core.py`; it writes `data/flood_scenarios.csv`.

- Real reference: valid Delhi state daily rainfall from source 1.
- Four hypothetical configurations per valid real forcing day; fixed seed 42.
- Real forcing date and `event_id` stay attached. Split date groups before fitting; never place siblings from a date in different folds.
- Rainfall in mm; storm duration hours; drainage equivalent mm/hour; catchment area m²; dimensionless runoff coefficient/blockage/ponding fraction; initial equivalent storage mm.
- Synthetic peak depth in meters is calculated by a transparent lumped mass balance. Synthetic flood class = peak depth ≥0.15 m. The threshold and parameter ranges are research assumptions, not engineering standards.
- `depth_m`, target, IDs and source dates are excluded from predictive features. All physical scenario inputs must be supplied at inference. Observed future rainfall is **not** portrayed as available to a live forecaster.
- No river hydraulics, terrain routing, backwater, pipe surcharge or calibrated local infiltration. This is not an implementation of [EPA SWMM](https://www.epa.gov/water-research/storm-water-management-model-swmm); that reference motivates the richer future physical validation work.
- **Synthetic labels only**. No real flood incidents or infrastructure-failure labels are present. Reported classification scores measure simulator approximation, not field flood detection.

The rainfall-derived scenario file retains source attribution and restrictions; this package does not relicense upstream data.

## User-supplied alternatives not used for training

1. [Playground Series S4E5 data](https://www.kaggle.com/competitions/playground-series-s4e5/data): generic synthetic FloodProbability regression is not a substitute for observed incident labels. Download requires a Kaggle account and potentially accepting competition rules. Authenticated command: `kaggle competitions download -c playground-series-s4e5 -p data/alternatives/playground`. Exact downloaded schema/license must be inspected if used; it is not part of these fitted models.
2. [UrbanFloodBench](https://www.kaggle.com/competitions/urban-flood-modelling/data): a potential separate hydrodynamic benchmark. Authenticated command: `kaggle competitions download -c urban-flood-modelling -p data/alternatives/urban`. Account, competition participation/rule acceptance may be required. Files, target schema, spatial/temporal grids and permitted use were **not verified by download**, and no unsupported details or performance claims are supplied.

## Alignment and data availability rules

The primary notebooks perform **no cross-source merge**. Time alignment for supervised targets is exact next regular interval within the same entity (zero temporal mismatch). Missing intervals are inserted as unavailable, not skipped. Exact identities must match (zero cross-identity spatial tolerance).

Future point-to-asset matching requires verified coordinates, a common coordinate reference system, source footprint, and compatible timestamps. An example starting tolerance of ≤1 km and backward-only ≤1 hour would require local validation; it is not applied here. State-level rain requires polygon/area-weighted reasoning and cannot be matched to a drain as if it were a point sensor.

Historical incidents must satisfy both `event_time <= origin` and `reported_at <= origin`, within the chosen historical window and entity. The helper demonstrates this contract; no incident counts are included without a genuine incident feed. Missing history is unknown, never zero.
