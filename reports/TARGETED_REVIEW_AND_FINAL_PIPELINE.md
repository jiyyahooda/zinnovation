# CivicFlux: targeted review of 06–09 and completed notebooks 10–11

## Scope and preservation

The original EDA, datasets, architecture and working model candidates are retained. Notebooks 06–09 contain targeted source corrections and appended diagnostic sections, with new experiment exports under `v1.1.0`. Their existing `v1.0.0` artifacts are retained byte-for-byte. Notebooks 01–05 and every original artifact were compared with the pre-review hash manifest: **147 protected files unchanged**. Pre-review source/output copies of 06–09 are retained under `reports/targeted_review/original_notebooks/`.

New notebooks:

- `notebooks/10_Model_Comparison_and_Validation.ipynb`: 13 sections, 46 cells, 11 saved figures; no model fitting.
- `notebooks/11_End_to_End_CivicFlux.ipynb`: 13 sections, 46 cells, 4 saved figures plus research tables, JSON responses, graph traces, audit records and process checks; no artifact model training.

## Actual before/after metrics

| Component | Before | After targeted review | Interpretation |
|---|---|---|---|
| Water threshold | 0.95 after all coarse-grid validation F1 scores were zero | 0.01846993 from validation scores | The old search excluded useful low-score cutoffs. No 2019 labels select the new threshold. |
| Water hourly precision / recall / F1 | 0 / 0 / 0 | 0.06235 / 0.66667 / 0.11403 | More detections, but an unusably high false-alert burden. |
| Water AP / ROC-AUC | 0.06488 / 0.57728 | 0.06488 / 0.57728 | **No discrimination improvement.** |
| Water complete event windows recovered | 0 of 19 | 17 of 19 | Network-level overlap, not leak localization. |
| Water false-alert hours / episodes | 0 / 0 | 4,572 / 180 | 55.1% of negative hours alert; operational fault prediction remains unsupported. |
| Cascade selected model / threshold | Tuned Logistic Regression / 0.15 | Same | NetworkX rule retained; no added estimator. |
| Cascade AP / ROC-AUC / F1 | 0.46124 / 0.89392 / 0.45168 | Same | Diagnostic coverage improved; original held-out scores unchanged. |
| Outcome success threshold | 0.05, effectively everyone positive | 0.50737937, validation balanced-accuracy diagnostic | A research operating point, never an allocation policy. |
| Outcome precision / recall / F1 | 0.54532 / 1 / 0.70577 | 0.60000 / 0.53083 / 0.56330 | F1 decreased; reporting an improved F1 would be false. Test balanced accuracy is about 0.553. |
| Outcome AP / ROC-AUC / Brier | 0.61892 / 0.57079 / 0.25740 | Same | Success probabilities remain weak and worse calibrated than a training-rate baseline (Brier 0.24820). |
| Selected duration model / MAE | Ridge / 8.34856 h, chosen with test MAE | Ridge / 8.34856 h, chosen with validation MAE 8.20185 h | Selection leakage repaired; no score gain claimed. Median baseline MAE is 9.97890 h. |

These are retrospective repairs of already-inspected test periods. Validation-only threshold/model selection does not restore a pristine test set; genuinely new future data is still required for prospective confirmation.

## 06: what the investigation found

Validation has only two new-onset episodes. All old 0.05–0.95 cutoffs had zero F1; taking the highest tie selected 0.95 without useful evidence. New operating-point searches cover the validation score distribution. The validation score median is 0.03269; the 2019 median is 0.02123 versus training 0.04588. Several pressure-sensor test medians shifted downward by about 1.25 training standard deviations. These are descriptive signs of temporal shift, not causal fault explanations.

Baselines now include a training prior, the original hydraulic-change rule and a train-only directional seasonal-residual rule. Every baseline threshold is selected on validation. Event recovery is paired with false-alert hours, complete-window detection delays and episode counts. An always-alert prior has perfect event recovery and zero wholly false episodes because its single long episode intersects positives; its 8,304 false-alert hours expose why episode count alone is insufficient.

The bundle and common adapter explicitly abstain for operational fault requests. Historical simulated onset scores remain available for research only.

## 07: false positives and dependency conditions

The original test still has 1,484 false-positive node snapshots and 184 false negatives. Error slices now cover each held-out graph, node type, seen/unseen topology and load band. False-positive candidate routes expose dependency directions, delays, resilience and conditional transmission factors without claiming an actual or causal failure path.

The new condition study uses six events per held-out graph and three stochastic repetitions. Pooled event-node metrics avoid averaging a zero recall into no-event cases. Under doubled delays, Logistic precision is 0.2402 and FPR 0.1967, whereas the NetworkX rule has precision 0.3596 and FPR 0.1135, with recall 1.0. The classifier's features omit edge delays, so its scores cannot respond to that change. This limitation is retained; no extra complexity is justified by these diagnostics.

## 09: predictable signal, calibration and verification

The training-rate baseline has AP 0.5453, historical type rates AP 0.5758, and the selected classifier AP 0.6189. The generator oracle has AP 0.6488 and ROC-AUC 0.6128: even its true latent probabilities have limited discrimination under the simulated Bernoulli noise. The oracle is never a feature, exported predictor or model-selection input.

Success inference exposes a clearly named research score only in the raw research bundle and returns no operational success probability. The common adapter exposes research resolution time and a null success probability. Allocation rejects success-score fields. The duration study remains among completed synthetic records, with censoring and selection limitations documented.

Verification validates completion and assignment timestamps, nonempty independent-verifier/evidence fields, matching status/label and chronological verification. Synthetic outcomes cannot be promoted into real verified success. The research approval helper supports pending/defer/reject only and cannot approve or dispatch.

## 10: consolidated evaluation

The notebook discovers nine existing components, their schemas, metadata/model cards, artifact paths and versions. It distinguishes forecasts, simulated classifiers, unsupervised detectors, graph rules and CP-SAT. Comparisons remain task-specific; rainfall, AQI and traffic are not ranked by incompatible MAE units.

**54 reported metric values were independently recomputed and matched.** The raw flood Brier score cannot be recomputed because the original test export contains calibrated probabilities only; it is explicitly reported as unavailable. Artifact inventory includes all versions of the nine components and excludes generated evaluation reports to avoid self-referential hashes.

Reports: `artifacts/model_validation/v1.0.0/`, including `metric_consistency.csv`, `forecast_baselines.csv`, interval coverage, validation/readiness matrices, provenance, missing/incompatible evidence, and `model_registry.json`.

## 11: fresh-process serving and end-to-end evidence

All nine component workers loaded and executed through `src/civicflux/serving.py` in ordinary Python processes without importing Jupyter. Five registered anomaly sensor suites were individually exercised. **75 incompatible requests abstained**, including wrong scope/units/horizon, operational purpose, stale clocks, missing payload/readings, unknown entities/sensors, unsupported loads, false synthetic provenance and forbidden success estimates.

Classification of available components:

| Status | Components | Meaning |
|---|---|---|
| Backend-ready for research inference | Rainfall, AQI, Traffic, Infrastructure anomaly | Supported historical fixtures load and predict; provenance, clock, unit and geographic limitations remain. |
| Simulation/demo only | Flood, Water network, Cascade risk, Resource optimization, Intervention outcomes | Technically functional synthetic/benchmark inference; no real municipal validity or operational authority. |
| Not ready | None for the tested research contracts | Missing, changed or incompatible artifacts would be reported here rather than replaced. |

The synthetic decision lane uses exactly matching graph identity and fingerprint for cascade nodes and optimization cases. Delhi aggregate forecasts, unlocated junctions and L-TOWN inputs remain outside that lane. Normal and scarce-budget CP-SAT scenarios produce feasible research proposals, require human review and never dispatch. Synthetic completion is distinct from independently verified success.

Reports: `artifacts/end_to_end/v1.0.0/`, including registry, example API responses, process checks, abstention checks, historical forecasts, allocation decisions, route traces, scenario results, review audit, outcome-verification refusal and `tests.txt`.

## Tests and changed files

**53 automated tests passed**, including prior tests plus changed-behavior tests for sub-0.05 threshold search, false-alert duration, directional propagation, stale artifact evidence, missing exports, input/unit/scope validation, unsupported outcome suppression, forbidden allocation inputs, serialization, verification chronology and metric consistency. All code cells in notebooks 06–11 executed with zero saved error outputs.

Modified existing files:

- Notebooks 06–09 (targeted corrections and appendices).
- `src/civicflux/water.py`, `cascade.py`, `outcomes.py`.
- `build_notebooks.py` (scoped build entry points/documentation).
- `requirements.txt` (the existing test runtime pin, pytest 8.3.4).

New source files:

- `src/civicflux/review.py`, `contracts.py`, `serving.py`, `runtime.py`, `integration.py`, `validation.py`.
- `apply_targeted_review.py` (idempotent source delta after intentional regeneration of 06–09).
- `build_notebooks_10_11.py` and notebooks 10–11.
- `scripts/check_research_inference.py`.
- `tests/test_review_and_serving.py`.

New versioned experiments: `water_network`, `cascade_risk`, `resource_optimization`, `intervention_outcomes` under `v1.1.0`; evaluation and end-to-end reports under `v1.0.0`.
