# CivicFlux

A research-backed civic resilience workspace with a React dashboard, FastAPI backend, geographic maps, live weather and modeled air-quality feeds, explainable cascade scenarios, OR-Tools allocation and human review.

## Dashboard setup

Use Python 3.13 and Node.js with pnpm. Virtual environments, raw datasets, local records and provider secrets are excluded from Git.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-serving.txt
cd frontend
pnpm install --frozen-lockfile
pnpm build
cd ..
python run_mac_app.py
```

On the configured Mac, double-click `Start_CivicFlux_Mac.command`. Weather and CAMS estimates use live API data; authenticated CPCB station and TomTom traffic feeds require your own optional server-side keys. See [live-data setup and limitations](LIVE_WORKSPACE.md), [Mac startup](MAC_START.md) and [application architecture](APPLICATION.md).

The dashboard separates observations, model estimates, historical research forecasts and synthetic planning assumptions. Existing weak fault/success estimates abstain from operational decisions. No interventions are automatically dispatched. Waste management is outside this implementation.

Verification from the configured Mac: 74 Python tests, nine prediction-card contracts and five draft-storage checks passed. See [verification](reports/live_upgrade/browser_checks.md).

## Original research documentation

# CivicFlux research notebooks

**Delivered execution:** all four notebooks run end-to-end, with 84 embedded figures and eight passing integrity tests. See [measured results](reports/RESULTS.md).

Four substantial, commented notebooks follow the requested 13-section research structure. They use the supplied RTA notebook as a style reference and replace its random-split classification workflow with temporal forecasting or grouped simulation evaluation as appropriate.

| Order | Notebook | Task | Cells |
|---|---|---|---:|
| 1 | [Rainfall](notebooks/01_Rainfall_Research.ipynb) | Next-day Delhi state-average rainfall | 107 |
| 2 | [AQI](notebooks/02_AQI_Research.ipynb) | Next-hour Delhi city PM2.5 | 105 |
| 3 | [Traffic](notebooks/03_Traffic_Research.ipynb) | Next-hour counts at four anonymous junctions | 107 |
| 4 | [Flood](notebooks/04_Flood_Research.ipynb) | Synthetic flood scenario classification | 99 |

Each includes source inspection, EDA graphs, explicit preprocessing policies, leakage checks, feature engineering, temporal splits, baselines, model comparisons, cross-validation, randomized hyperparameter searches, final evaluation, calibration/intervals, error analysis, permutation importance, SHAP global and individual plots, full serving bundles, metadata, feature schemas and typed CivicFlux examples. Traffic also includes a separately labeled disruption simulator.

## Run

Use Python 3.13 for the exact tested environment. A project-local `.venv` is already present on this machine. For a fresh setup:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python download_data.py
python execute_notebooks.py
```

The execution script creates a local Jupyter kernel specification and saves all cell outputs. To execute just one notebook, use `python execute_notebooks.py 01` (or 02, 03, 04). To edit interactively, open a notebook in JupyterLab/VS Code and select the `.venv/bin/python` interpreter; or register it with `python -m ipykernel install --user --name civicflux --display-name 'Python (CivicFlux)'` and launch `jupyter lab`. Run cells top-to-bottom from the project root or notebook directory.

The script `build_notebooks.py` regenerates notebook sources **and clears previous outputs**; do not run it merely to view results. `civicflux_core.py` contains shared temporal and serving logic; the substantive experiments and visualizations are in the notebooks, not hidden behind a one-line trainer.

Read [DATASET_GUIDE.md](DATASET_GUIDE.md) for exact download/API links, licenses, schema, unit contracts and geography. Source files are included locally under `data/raw`. No source file or RTA notebook was edited.

## Research decisions

- Inspect all rows, model Delhi rainfall and Delhi PM2.5 by default; model all traffic junctions. This is explicit scope, not random downsampling. Set `cfg['selected']=None` for broader multi-entity experiments and repeat evaluation.
- 60/20/20 chronological development/calibration/test partitions; three expanding CV folds with horizon purge. Six randomized search trials per tuned family. Increase `N_SPLITS` and `N_SEARCH` in the setup cells for additional compute.
- Forecast candidates: persistence, train-only seasonal mean, Ridge, Random Forest, XGBoost. Tune the top two learned candidates; baselines remain eligible to win. Scaling only for Ridge; fold-local numeric imputation and categorical encoding.
- Flood candidates: prior baseline, unweighted/balanced Logistic Regression, XGBoost. Tune both primary families. Separate probability-calibration and threshold-selection dates. Scenario siblings share temporal splits.
- Final tests never select the winner. Plots/diagnostics after final evaluation must not be used for retuning without declaring a new study and new holdout.
- Forecasting is rolling one-step. Raw-history bundles also emit an actual next interval forecast after the file ends. This does not claim fixed-origin multi-step accuracy.
- A 90% residual interval is calibrated on a later period; time-series dependence prevents an unconditional coverage guarantee. Achieved coverage is reported.
- No LightGBM, NetworkX or OR-Tools dependency is added because these tasks do not yet include measured road travel times, connectivity, capacities or dispatch constraints. Count-to-speed conversion would be unsupported.

## Important data findings

Rainfall: 204,876 state-level records ending July 2024. AQI: 219,125 city-level records ending January 1, 2024; station lineage, pollutant unit metadata and real/synthetic provenance are unverified. Traffic: 48,120 records with unknown city/timezone and educational-use restrictions. Flood: real state rain plus explicitly synthetic, uncalibrated drainage scenarios; no observed flood or infrastructure-failure labels.

## Files and outputs

- `notebooks/`: executed research notebooks with embedded figures/tables.
- `artifacts/<task>/pipeline.joblib`: reloadable serving bundle, including model/preprocessing and feature configuration; flood adds calibrator and threshold.
- `artifacts/<task>/`: feature schema, source hash, metadata, CV trials, metrics, holdout predictions and CivicFlux payload examples.
- `reports/`: source inventory, execution audit and concise measured-results report.
- `tests/test_integrity.py`: meaningful checks for causal features, time gaps, grouping, incident availability, simulator physics and artifact round-trip.

Keep `civicflux_core.py` importable beside a deployed bundle and use the recorded dependency versions. Load only trusted joblib artifacts. These are research demonstrations, not validated real-time public-safety or engineering systems; the provenance and synthetic flags are included in the payloads.

### macOS OpenMP

The execution script automatically points child kernels at scikit-learn's existing bundled `libomp.dylib` on macOS. For an interactive shell/Jupyter session on this machine, activate the environment and run the following **before** starting Jupyter/Python:

```bash
export DYLD_LIBRARY_PATH="$(python -c 'import sklearn; from pathlib import Path; print(Path(sklearn.__file__).parent / ".dylibs")')${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
jupyter lab
```

If your scikit-learn distribution does not bundle OpenMP, follow XGBoost's platform installation instructions. The existing machine's global Python/Homebrew installations were not modified.
