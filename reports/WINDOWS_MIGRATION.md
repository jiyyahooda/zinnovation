# CivicFlux Windows migration report

Verified on **26 October 2026 (Asia/Kolkata)**. Scope was expanded by the user to the full local application after the initial migration inspection.

## Canonical project and archive

Project root: `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux`

Source archive: `C:\Users\kusha\OneDrive\Desktop\civicflux_ml.zip`

All **414 substantive archive files already existed and matched byte for byte** before edits. No redundant extraction or artifact duplication was needed. The transferred macOS virtual environment, caches and Apple resource-fork files were not used. Every substantive file was read and hashed against the archive; the full inventory is in `windows/archive-integrity.json`.

Another complete research copy at `C:\Users\kusha\OneDrive\Desktop\civicflux_ml\civicflux_ml` matches all 414 original substantive files. Its content is equivalent to the ZIP, so filesystem modification times do not establish a newer research version. The canonical copy is the complete copy already in this workspace. No copies were automatically merged or deleted.

A separate app was inspected at `C:\Users\kusha\OneDrive\Desktop\civicflux\civicflux`. It has its own backend/frontend and different demonstration IDs. It was not merged or modified. The research ZIP itself had no FastAPI backend or frontend, so the canonical application's routes are new; compatibility with that separate Desktop application's routes is not claimed.

Final preservation audit: **all artifacts, datasets and notebooks 01–11 remain byte-identical to the ZIP**. Of the original 414 files, 411 remain unchanged. Changed originals: `.gitignore`, `src/civicflux/serving.py`, and `tests/test_review_and_serving.py`. New application/configuration/report files are additive. No notebook builder, notebook execution, production training, artifact conversion, or research metadata regeneration was run. Unit tests may fit disposable fixture estimators in temporary directories; no saved research model is retrained.

## Windows environment

Python: **3.12.14**, executable `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux\.venv-windows\Scripts\python.exe`.

Fresh environment: `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux\.venv-windows`. The original `.venv` records macOS Python 3.13.5 and is preserved but unused. The bundled Windows Python 3.12.14 was available and used; exact Python 3.13 parity was not established. Import and inference results below are evidence for this Windows environment, not a promise of arbitrary pickle portability.

All dependencies in the original `requirements.txt` were installed with their requested pins. `requirements-serving.txt` adds FastAPI, Uvicorn, HTTPX and dotenv. `pip check` passes. A complete measured environment lock is saved in `windows/requirements-windows.lock.txt`.

| Dependency | Installed version | Import |
| --- | --- | --- |
| numpy | 2.3.5 | passed |
| pandas | 2.2.3 | passed |
| scikit-learn | 1.6.1 | passed |
| xgboost | 3.4.1 | passed |
| networkx | 3.7 | passed |
| ortools | 9.14.6206 | passed |
| joblib | 1.4.2 | passed |
| fastapi | 0.162.0 | passed |
| uvicorn | 0.54.0 | passed |

The sandbox initially blocked pip temporary files, network downloads, Node access and pytest temporary paths. Those setup/check commands were rerun through the permission mechanism. No operating-system security setting was changed.

## Selected artifacts and verification

The existing registry remains canonical: `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux\artifacts\model_validation\v1.0.0\model_registry.json`.
Both unversioned and versioned artifact directories were inspected. Older versions remain intact. Selection follows the registry rather than promoting a directory because it is newer. Associated metadata and feature-schema paths are recorded for every component in `windows/migration_inventory.json`; no duplicate model registry was created.

| Component | Selected version | Artifact or code | Positive inference | Check |
| --- | --- | --- | --- | --- |
| rainfall | legacy-unversioned | `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux\artifacts\rainfall\pipeline.joblib` | supported_research | PASS |
| aqi | legacy-unversioned | `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux\artifacts\aqi\pipeline.joblib` | supported_research | PASS |
| traffic | legacy-unversioned | `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux\artifacts\traffic\pipeline.joblib` | abstained | FAIL |
| flood | legacy-unversioned | `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux\artifacts\flood\pipeline.joblib` | abstained | FAIL |
| infrastructure_anomaly | 1.0.0 | `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux\artifacts\infrastructure_anomaly\v1.0.0\detectors.joblib` | supported_research | PASS |
| water_network | 1.1.0 | `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux\artifacts\water_network\v1.1.0\pipeline.joblib` | supported_simulation | PASS |
| cascade_risk | 1.1.0 | `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux\artifacts\cascade_risk\v1.1.0\pipeline.joblib` | supported_simulation | PASS |
| resource_optimization | 1.1.0 | `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux\src\civicflux\optimization.py (CP-SAT code; no fitted artifact)` | supported_simulation | PASS |
| intervention_outcomes | 1.1.0 | `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux\artifacts\intervention_outcomes\v1.1.0\pipeline.joblib` | supported_simulation | PASS |

**Seven of nine components pass fresh-process loading, supported historical/synthetic inference, and negative-input abstention checks** using the existing `scripts/check_research_inference.py`. Infrastructure anomaly verification additionally covers all five registered sensors. The nine reports contain 75 negative cases; their responses abstain. Failed positive checks are not certified as serving-ready.

Traffic and flood fail inside `XGBoosterUnserializeFromBuffer` with `input stream corrupted` while restoring the joblib-embedded XGBoost booster. Archive and current artifact hashes match. Installed XGBoost is the recorded 3.4.1; the precise native snapshot incompatibility is not established. Their prior macOS success reports remain unchanged and cannot substitute for a Windows success. No mock, retraining, artifact rewriting, or inference substitution was introduced into `serve()`.

XGBoost distinguishes stable model exports from pickle memory snapshots and does not guarantee snapshot compatibility. See its [official model I/O documentation](https://xgboost.readthedocs.io/en/stable/tutorials/saving_model.html). A separately authorized recovery on the original working environment, including portable model export, may be needed. The original files should remain preserved.

Rainfall retains Delhi state aggregate, mm/day and next-day scope. AQI research retains Delhi aggregate next-hour PM2.5 with incomplete source-unit/station lineage, not an official AQI index prediction. Traffic retains anonymous benchmark junctions and unknown timezone/geography. Flood, L-TOWN water, cascade, optimization and outcome components remain synthetic/research-only. Forecast residual intervals and their coverage limitations, timestamps, freshness, units, provenance, horizons, operational abstention, and dispatch restrictions are preserved in serving responses. Unsupported success predictions are suppressed.

## Paths and source imports for FastAPI

Central configuration: `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux\project_paths.py`; optional override `CIVICFLUX_ROOT`.

| Purpose | Canonical path |
| --- | --- |
| ML source | `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux\src\civicflux` |
| Core bundle classes | `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux\civicflux_core.py` |
| Artifacts | `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux\artifacts` |
| Datasets | `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux\data` |
| Configuration | `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux\config` |
| Backend | `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux\backend` |
| Serving module | `C:\Users\kusha\OneDrive\Documents\ChatGPT\zinnovatio4.0\CivicFlux\src\civicflux\serving.py` |

Run Python from the project root (or put that root on `PYTHONPATH`), then import:

```python
from project_paths import PROJECT_ROOT
from src.civicflux.serving import serve
response = serve(component, request, PROJECT_ROOT)
```

The original artifact metadata contains historical macOS file references; these were not rewritten. They are provenance only, not runtime artifact locators. Runtime paths use `pathlib`. Existing `runtime.research_environment()` applies its OpenMP workaround only on Darwin and does not set macOS paths on Windows.

## Application integration and blockers

The application backend, frontend and SQLite workflow are implemented and tested. The latest combined regression report records **67 tests, 0 failures and 0 errors**. Model-check failures remain explicitly reported above even though the application regression tests pass.

Regenerating graph 42 on this environment yields fingerprint `01b1bbee27a6eb6c879715f6a83e61335d218af8a59b30e6f86dbbd38c167a52`, which differs from the old planning manifest's `0b508b5f61376876d041af90abec8b17845b884ce800aa1318843f3dc1c9e392`. The precise source of that difference is unproven. The old cross-component demonstration is therefore not certified as compatible on Windows. Its manifest and source are unchanged.

The new application workflow explicitly uses saved graph 100 with fingerprint `89aff1766c496c0fba9e3514050502e40f875b8a51201ce911a013aee430d7e8`. Its documented scenario configuration assigns existing fictional cost/policy templates to matching synthetic IDs and recomputes every cascade score on that exact saved graph. No old graph-42 risk evidence is fused. The default flood engine is the existing, explicitly selected mass-balance simulator, distinct from the failed trained surrogate. Selecting the surrogate returns an explicit failure without fallback.

Remaining blockers: traffic/flood native snapshot recovery; verified IMD/CPCB endpoint and station configuration; municipal geographic/asset mappings; real resource inventory and independent field-evidence authentication. Operational model approval and dispatch remain disabled. No municipal forecasts, confidence, coordinates or current readings were fabricated. No deployment was attempted; this Windows FastAPI/SQLite app is prepared for local use.

See `APPLICATION_VERIFICATION.md` for pages, routes, live HTTP checks and scenario results; `../APPLICATION.md` for launch instructions.
