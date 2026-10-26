# CivicFlux local application

Start `START-CIVICFLUX.cmd` from this folder, then open http://127.0.0.1:8000.
The Windows environment and compiled frontend are already prepared on this computer.
Admin login: **ADMIN001**, password **001**, unless overridden in `.env`.
The server listens on loopback only. These are the requested local hackathon credentials;
set the environment values before using a shared deployment.

## Development

From the project root:

```powershell
.\.venv-windows\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
# In another terminal:
cd frontend
pnpm dev
```

Vite proxies `/api` to the backend. For a single-server production build, run
`pnpm build` inside `frontend` and restart FastAPI. Its static mount serves that build.
OpenAPI and interactive API documentation: `/openapi.json` and `/docs`.
`setup-windows.ps1 -Python <python-executable>` supports recreating a Windows environment.
The transferred macOS `.venv` must not be activated.

## Pages and access

Overview, Predictions, Infrastructure, Cascade analysis, Planning, Operations,
and Model validation use the FastAPI API. Civilians can view saved analyses and submit
complaints. Admin sessions enable research requests, scenario inputs, resource and
policy-weight changes, complaint status updates, defer/reject reviews, and separate
simulation evidence records. Credentials and authorization are checked server-side.
Reviews, outcomes, complaints, sessions and append-only application audit events persist
in `var/civicflux.sqlite3`. Tests use isolated databases.

The original research review function forbids approval. Approve requests return 409,
and no code dispatches interventions. The civilian portal cannot call admin mutations.
Review notes never become independently verified outcome labels. External verifier names
are attestations; their identities are not authenticated by this prototype.

## Research and scenario boundaries

Models are selected from `artifacts/model_validation/v1.0.0/model_registry.json`.
No duplicate inference pipeline or model registry was introduced. The API imports
`src.civicflux.serving.serve`. Windows checks are separate in `reports/windows/inference`;
the old macOS reports remain intact and cannot certify a changed interface.

The application scenario is declared in `config/scenarios/research.yaml`. It uses saved
synthetic graph 100 with its exact fingerprint. The old graph-42 planning manifest does
not match the graph regenerated on this Windows environment, so its risk evidence is
not fused. The new application scenario explicitly assigns the existing fictional cost
and policy template to matching graph-100 asset IDs, discards old cascade scores, and
recomputes scores using the saved cascade model on graph 100. Known outage seeds are
declared failed assumptions, not predicted probabilities. OR-Tools and two greedy
baselines use identical budgets, pumps and crew-hour limits. Factor breakdowns are shown.

The default flood engine is the existing `civicflux_core.simulate_depth` mass-balance
simulator. It is explicitly distinct from the trained flood surrogate. Selecting the
trained surrogate reports its Windows deserialization error without fallback. Flood
and cascade run as parallel scenario evidence: no unvalidated flood-to-asset dependency
is invented. Uncertainty is unavailable for mass-balance simulation and is shown as such.

Traffic and flood XGBoost snapshots currently fail to restore (`input stream corrupted`)
on Windows despite matching the pinned XGBoost package version. The other seven serving
components pass fresh-process inference and abstention checks. Historical saved charts
remain labeled as evaluation results; they are never presented as live predictions.

Delhi has only aggregate rainfall and PM2.5 research support. AQI research forecasts
PM2.5, not an official AQI index. Chandigarh and Chennai have no supplied model or
station mapping. Anonymous traffic and L-TOWN water research are not relocated to cities.

IMD/CPCB adapters accept only explicitly configured JSON gateways and verified station
mappings; no endpoints, readings or coordinates are guessed. All cities currently show
unavailable observations. Gateway payload contract: `source`, `city_id`, `station_id`,
timezone-aware `observed_at`, and `readings` mapping metric names to `{value, unit}`.
Supported units are declared in `backend/services/data_service.py`. Source configuration
must be independently verified before adding mappings. No supported live traffic source
is configured.

## Verification

```powershell
.\.venv-windows\Scripts\python.exe scripts\verify_windows.py
.\.venv-windows\Scripts\python.exe -m pytest tests -q
cd frontend
pnpm build
```

The model verification script deliberately exits nonzero while any saved model fails.
See `reports/WINDOWS_MIGRATION.md` and `reports/APPLICATION_VERIFICATION.md` for the
measured results and remaining limitations. No notebooks or trained artifacts were
regenerated or retrained. Model training remains a future, separately authorized step.
