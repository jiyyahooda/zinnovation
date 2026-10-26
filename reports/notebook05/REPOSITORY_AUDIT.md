# Notebook 05 repository and data audit

Scope: `/Users/jiyahooda/Documents/New project` and `/Users/jiyahooda/Desktop/projects` were inspected by file inventory and targeted code reads. No service was started, no API invoked, and no database altered.

## Existing functionality retained

- `civicflux_ml/` is the existing working project from notebooks 01–04. A separate `civicflux_ml 2/` copy already existed; it is not the target and is untouched.
- Existing notebooks have 107, 105, 107, 99 cells with executed outputs. SHA256 snapshots of all their files and existing artifacts are in `preserved_before.json`; final verification compares the same bytes.
- `civicflux_core.py` provides source configuration, raw canonicalization, temporal forecasting features/splits, forecast/flood bundles and incident-availability filtering. It is reused and unmodified. Its forecast features do not cover robust anomaly references or invalid-reading evidence, so anomaly-specific functions live in `src/civicflux/anomaly.py`.
- `build_notebooks.py` is the existing source generator and writes 01–04 at top level. It is now guarded: regenerating existing outputs requires `--overwrite-legacy`. It is not imported or executed during this extension. `build_notebook05.py` is authoritative only for 05, requires explicit overwrite, and never writes 01–04.
- `execute_notebooks.py` already supports a prefix selector; execution uses `05` only in a clean kernel. Existing `audit_results.py` assumes 13 sections and summarizes only four forecasting/flood tasks. A separate 05 audit adds measured anomaly results without rewriting the legacy report. All new artifacts live under `artifacts/infrastructure_anomaly/v1.0.0/`.
- Existing requirements supply pandas, NumPy, scikit-learn, joblib, notebook execution and plots. No new dependency is required.

## Backend discovery

| Actual path | Observed functionality | Applicability |
|---|---|---|
| `aegisflow-command-center/backend/app/main.py` | FastAPI synthetic tracks; weighted priority; operator actions and hypothetical scenarios | Aerospace demo, not municipal infrastructure. Do not reuse track identity or mutate its actions. |
| `SAGE_2026/backend/app/main.py` | ASTRA-GUARD FastAPI upload/component/lot/alert routes | Electronics burn-in domain, not CivicFlux asset registry. |
| `SAGE_2026/backend/database/ingestion.py` | Validation → preprocessing → DB insertion → inference/risk snapshots | Existing unrelated DB workflow; not a municipal sensor feed. |
| `SAGE_2026/backend/app/schemas/risk.py`, `alert.py` | Component/lot risk and severity schemas | Cannot truthfully map benchmark junctions into these component IDs. |
| `SAGE_2026/backend/app/services/mock_data.py` | Explicitly labeled mock component risk/trajectory values | Not measured municipal observations. |
| `SAGE_2026/scripts/generate_burn_in_dataset.py` | Synthetic electronics measurements and injected test conditions | Different domain; excluded from training and fault evaluation. |
| `Desktop/projects/RASP/server.py` | Flask accident-severity prediction/reference project | Not an infrastructure state/approval interface. |

No CivicFlux FastAPI `main.py`, `data.py`, `simulation.py`, `graph.py`, `optimizer.py`, asset registry, OR-Tools dispatch model or approval/ingestion contract was found in the inspected scope. The current CivicFlux files export research payload JSON only. Therefore live integration is explicitly pending, not represented as completed. A pure, tested evidence adapter returns an unmapped, corroboration-required envelope with dispatch disabled. It does not introduce a competing graph/optimizer or modify unrelated APIs.

## Measurement provenance

| Source | Evidence available | Use in 05 |
|---|---|---|
| Traffic 48,120 rows, 4 anonymous junctions | Publisher-described hourly counts; unknown city/timezone, no faults | Primary historical benchmark, independent per-junction detectors. Junction 4 first appears after training cutoff and must abstain. |
| Rainfall 204,876 state-day rows | Reported actual mm and upstream WRIS claim; aggregation/reporting lineage limited | Delhi state-average independent environmental stream; rainfall extremes are not equipment failures. |
| PM2.5 219,125 city-hour rows | Publisher-described processed pollutant series; no station IDs; units and real/synthetic lineage unverified | Delhi independent benchmark stream with inherited provenance warning. |
| `data/flood_scenarios.csv` | Real rainfall reference plus synthetic drainage parameters and depth labels | Audit only. These independent scenario rows are NOT observed chronological water-level sensors. |
| Real water-level, pressure, flow, verified incidents | Not present | Blocked experiment; no precision/accuracy against nonexistent fault labels. |

Full original schemas, acquisition links, licensing and geographic limitations remain in `DATASET_GUIDE.md`. Sources are never combined into one physical asset. Additional perturbations are isolated fixtures, never overwrites of original records.
