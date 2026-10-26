# Notebooks 06–09 execution report

All four notebooks were executed with saved outputs. Each currently has zero notebook error outputs. `./.venv/bin/python -m pytest -q tests` passed 38 tests after the final optimizer-weight regression check.

## Actual results

- **06 Water benchmark:** The best selected model was tuned Logistic Regression. On the 2019 locked test (8,760 hourly rows; 5.21% target prevalence), average precision was 0.0649 and ROC-AUC 0.5773. The validation-selected threshold was 0.95; it produced zero positive alerts on the test (precision/recall/F1 all 0). The hydraulic-change rule reached 87.1% recall but had 88.7% false-positive rate. This is weak/unstable benchmark performance, and should not be used operationally. The honest result is that this experiment did not produce a useful alert policy.
- **07 Cascade simulator:** On 9,120 unseen-graph test node snapshots (9.55% simulated event prevalence), Logistic Regression had average precision 0.4612, ROC-AUC 0.8939, recall 0.7887, precision 0.3164, and Brier 0.0665. The NetworkX reachability rule had 100% recall but lower precision (0.2061) and more false positives. These metrics only show recovery of the documented independent-cascade simulator.
- **08 Optimization:** CP-SAT reached `OPTIMAL` in each of four declared synthetic resource scenarios. Under normal resources, utility was 12.4185 versus 11.2256 severity-greedy and 10.9024 utility-greedy, all feasible under shared constraints. The custom weight path is regression-tested and the notebook rerun after that fix; increasing carbon-penalty weight reduces selected objective/selection as expected. All cost, equity, environment, and inventory inputs are illustrative.
- **09 Outcomes:** For the final synthetic time period (684 verified synthetic records; 54.5% synthetic positive prevalence), success prediction average precision was 0.6189, ROC-AUC 0.5708, Brier 0.2574. The F1-selected threshold was 0.05, yielding 100% recall but no useful ranking separation; treat as a poor toy surrogate. Resolution-time MAE was 8.35h (Ridge), 8.38h (Random Forest), and 8.36h (XGBoost), versus 9.98h training-median baseline. No real-world intervention-effect or outcome claim follows.

## Files

- `notebooks/06_Water_Network_Fault_Research.ipynb`
- `notebooks/07_Cascade_Risk_Analysis.ipynb`
- `notebooks/08_Sustainability_and_Resource_Optimization.ipynb`
- `notebooks/09_Intervention_Outcomes.ipynb`
- `src/civicflux/graph.py`, `cascade.py`, `water.py`, `optimization.py`, `outcomes.py`, `research.py`
- `tests/test_research_06_09.py`
- `artifacts/water_network/v1.0.0/`, `artifacts/cascade_risk/v1.0.0/`, `artifacts/resource_optimization/v1.0.0/`, `artifacts/intervention_outcomes/v1.0.0/`
- `reports/NOTEBOOKS_06_09_AUDIT.md`

The BattLeDIM release is downloaded to `data/raw/battledim/` and ignored by Git because of size/licensing. `download_battledim.py` reproduces acquisition and checksum validation.
