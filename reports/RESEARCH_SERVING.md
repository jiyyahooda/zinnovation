# Research inference and reproducible builds

The existing models are served through one reusable function:

```python
from pathlib import Path
from src.civicflux.integration import fixture
from src.civicflux.serving import serve

root = Path.cwd()  # civicflux_ml directory
request = fixture('rainfall', root)  # actual supported historical data, no training
response = serve('rainfall', request, root)
```

A future existing FastAPI route can call `serve(component, payload, root)` directly. No second web framework or duplicate model implementation is required. The caller must preserve exact scope, units, horizon, historical/simulation mode, as-of clock and component-specific payload. See the saved registry/schema and `fixture()` for executable request examples.

Responses use `civicflux.research.v1`: component/version, status, prediction or null, uncertainty where supported, provenance, validation status, scope, units, horizon and warnings. Invalid inputs abstain; loading failures return `not_ready`. Operational requests abstain. Success estimates are excluded from allocation, and research optimization can only propose work for human review.

On this macOS installation, XGBoost needs the existing OpenMP library path when a Python process starts. The fresh-process check uses the same environment helper as the notebook executor:

```python
import subprocess, sys
from src.civicflux.runtime import research_environment

subprocess.run(
    [sys.executable, 'scripts/check_research_inference.py', 'traffic',
     '--output', 'reports/integration/traffic.json'],
    env=research_environment(), check=True,
)
```

A FastAPI process using these artifacts must launch with that environment too. Runtime setup, source-unit assumptions, unknown traffic clocks, unverified municipal mapping and synthetic validity limits are retained in the reports. Human authentication/approval and a real independently audited outcome API remain application responsibilities; the research helper cannot approve or dispatch.

Authoring sources:

- 06: `build_notebook06.py`; 07: `build_notebook07.py`.
- 08–09: `build_notebooks_08_09.py`.
- Targeted review deltas: `apply_targeted_review.py`, applied after intentional regeneration of 06–09. Existing detailed EDA is preserved.
- 10–11: `build_notebooks_10_11.py`.
- `build_notebooks.py --review-06-09` applies only the review delta; `--reports-10-11` invokes only the two new report builders. Builders protect existing outputs unless an explicit overwrite option is supplied.
- `execute_notebooks.py 06 07 08 09 10 11` executes only these notebooks and retains outputs. Notebook 10/11 do not fit model artifacts. Run Notebook 10 again after fresh checks if its readiness inventory needs refreshing.
- `python -m pytest -q tests` runs the tests, including current-artifact fingerprint checks against the saved fresh-process reports.

The registries are saved in `artifacts/model_validation/v1.0.0/model_registry.json` and `artifacts/end_to_end/v1.0.0/model_registry.json`. Review results are in `reports/TARGETED_REVIEW_AND_FINAL_PIPELINE.md`.
