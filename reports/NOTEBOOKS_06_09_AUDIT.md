# CivicFlux research notebooks 06–09 — provenance and build notes

This work adds only notebooks 06–09 and their helpers/artifacts. Notebooks 01–05 were checked against `reports/preserved_before_06_09.json` after execution and should remain byte-identical.

## Notebook 06 — water-network fault research

- **Dataset:** BattLeDIM/L-TOWN, Zenodo record [4017659](https://zenodo.org/records/4017659), official benchmark description [BattLeDIM data page](https://battledim.ucy.ac.cy/?page_id=33).
- **License:** CC BY 4.0 as recorded by Zenodo. The source manifest records each required file's size and SHA-256 after validating the publisher's MD5.
- **What it represents:** a hypothetical town model based on a Cyprus water system; its SCADA streams and leak episodes are simulated benchmark data. It contains no real Delhi incidents or confirmed CivicFlux failures.
- **Measurements:** 2018–2019 five-minute data; pressure in metres, flow in cubic metres/hour, tank levels in metres. Source timestamps are timezone-naive; the dataset documentation does not establish an operational timezone. The research experiment samples exact hourly instants, not future-window aggregates.
- **Labels:** publisher leakage-flow tables are converted to a benchmark onset target: at least one new leak starts in the preceding 24 hours. Negative means no new onset in that window, not no active old leak. Validation uses 2018-09 through 2018-12; the final test uses 2019. Training ends 2018-08-31.
- **Acquisition:** from this repository run `./.venv/bin/python download_battledim.py`. It reads the official Zenodo API record, downloads only the required release files with resumable transfers, and rejects any MD5 mismatch. Manual acquisition is available from the Zenodo record's Files section. No API key is required. Retain CC BY attribution if redistributing.
- **Used columns:** pressure/flow/level sensor measurements, causal one-step changes, backward 24-hour means, missing indicators, hour-of-day, and weekday. EPANET nominal topology is used for EDA only; the classifier predicts onset, not location.
- **Limitations:** simulated benchmark only; timezone and input receipt delay are unspecified; temporal fit is weak on the held-out year. It is not an official challenge score or municipal-fault validity claim.

## Notebook 07 — cascade risk

No verified cross-sector municipal graph or event labels exist in the workspace. The NetworkX water topology is kept separate from a directed, seeded synthetic dependency graph across drainage, road, water, pump, and facility node types. Independent 60-minute cascade simulation supplies labels. Events are grouped; entire graph seeds and higher-load conditions are held out. Model metrics measure fidelity to that simulator only.

## Notebook 08 — sustainability and resource optimization

The repository audit found no existing CivicFlux OR-Tools optimizer, municipal crew/pump inventory, verified costs, or approval API. The notebook reuses the shared graph readers and adds `src/civicflux/optimization.py` as a pure CP-SAT experiment. Costs (illustrative INR), candidate interventions, capacities, environmental effects, and equity proxies are synthetic. CP-SAT and severity/utility greedy baselines share budget, pump, and crew-hour constraints. Outputs require human approval and set dispatch false.

## Notebook 09 — intervention outcomes

No verified historical intervention records or independent outcome labels exist. The notebook therefore generates a fully synthetic, selection-biased study and reports classification and duration metrics only for that generator. Inputs are pre-assignment fields; completion/verification and post-treatment columns are excluded. The prediction bundle is explicitly marked synthetic and has no causal-effect, approval, or dispatch authority. Real use requires completed records and independent verification.

## Build and execution

- Notebook 06 source: `build_notebook06.py`; reusable data/model logic: `src/civicflux/water.py` and `src/civicflux/research.py`.
- Notebook 07 source: `build_notebook07.py`; graph and simulator logic: `src/civicflux/graph.py` and `src/civicflux/cascade.py`.
- Notebooks 08–09 source: `build_notebooks_08_09.py`; reusable components: `src/civicflux/optimization.py` and `src/civicflux/outcomes.py`.
- Execute a selected notebook with `./.venv/bin/python execute_notebooks.py 06` (or 07, 08, 09). Execution saves outputs back into the notebook and writes versioned artifacts under `artifacts/`.
- The legacy `build_notebooks.py` remains the authoring source for 01–04; it deliberately protects existing executed notebooks. Use the per-notebook builders above for 06–09. The dependency pins for the shared modules are in `requirements.txt`.
