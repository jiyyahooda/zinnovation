# CivicFlux application verification

Verified on 26 October 2026 (Asia/Kolkata). Canonical application: `CivicFlux` in the current workspace.

## Completed pages

| Page | Connected API/data | Behavior |
| --- | --- | --- |
| Overview | `/api/models`, `/api/cities`, `/api/observations`, `/api/scenarios`, `/api/predictions/rainfall/series` | Research coverage, source availability, saved evaluation chart, latest scenario |
| Predictions | `/api/predictions/{component}/example`, `/fixture`, `/series`, POST `/{component}` | Real serving calls, scoped benchmark fixtures, uncertainty/freshness, saved forecast charts, admin JSON input |
| Infrastructure | `/api/scenarios/graph` | Interactive 40-node, 96-edge schematic; keyboard selection, zoom, dependency inspection; no fabricated map coordinates |
| Cascade analysis | Saved scenario cascade response | 60-minute synthetic risk scores and human review flags; declared outage seeds highlighted |
| Planning | `/api/scenarios/defaults`, GET/POST `/api/scenarios` | Explicit flood-engine choice, rainfall/outage/load controls, budget/pumps/crew hours, factor weights, persisted scenario, CP-SAT/greedy comparisons |
| Operations | `/api/feedback`, `/api/complaints`, `/api/audit` | Civilian complaint submission/tracking; authenticated complaint transitions, defer/reject review, separate simulation outcome evidence and admin audit trail |
| Model validation | `/api/models`, existing registry/metadata/metrics and fresh Windows reports | Versions, readiness, provenance, metrics, artifact/schema paths and research limitations |

White/orange light theme and black/green dark theme are toggleable and remembered locally. City selection supports Delhi, Chandigarh and Chennai without relocating benchmark models. Typed API modules, loading/error handling, retry, minute refresh and responsive layouts are implemented. Civilian analysis is read-only; complaint submission is intentionally public. Admin authentication uses a random HttpOnly SameSite session cookie, hashed session tokens, expiry and server-side mutation checks. The requested local credentials are ADMIN001 / 001 and can be overridden in `.env`.

## Measured checks

- Standard frontend build: `pnpm build` passes TypeScript and Vite compilation. Vite reports a nonblocking large JavaScript chunk warning (approximately 672 kB before gzip).
- Combined regression suite: **67 passed**, no failures/errors. One upstream Starlette TestClient deprecation warning remains. The updated research verification test checks fresh platform reports and expects failed model loads to remain not ready; it does not relabel failed inference as successful.
- Nine independent model workers: **7 pass / 2 fail**, with 75 negative cases abstaining. Details are in `windows/inference` and the migration report.
- Live HTTP integration: 13 representative URLs returned HTTP 200, including the compiled frontend, health, inventory, city and observation endpoints, graph, scenario defaults/history, feedback, complaints, rainfall/PM2.5 examples and OpenAPI. Results: `windows/http-integration.json`; captured schema: `windows/openapi.json`.
- Browser: verified public dashboard, admin login, scenario execution, saved allocation output, sign-out, both themes, historical prediction value/interval/freshness, and the interactive infrastructure page. No captured browser console errors on the inspected pages. Mobile viewport check at 390 px showed a 375 px content width with no horizontal overflow. The browser tool's mobile screenshot rendering was scaled; responsive evidence also includes DOM dimensions.
- Browser-created example: **Monsoon stress test**, mass-balance flood, saved graph 100, initial `pump_0` outage, load 1.1, ₹50,000 budget, four pumps and 24 hours for each crew type. CP-SAT returned **OPTIMAL**, selected **10** candidates, used **₹48,949** and **3 pumps**, objective **4.848**. Utility-greedy selected five (₹49,661, objective 3.067); severity-greedy selected six (₹48,534, objective 3.536). This explicitly synthetic example remains saved locally.

API tests cover unauthenticated admin denial, wrong credentials, cross-origin admin denial, logout, unknown city/assets, unsupported cascade load, mismatched graph evidence, no trained-surrogate fallback, zero inventory, missing crew types, feasibility, score breakdowns, review persistence, forbidden approval, separate verifier records, chronology, complaint transitions and durable audit records. Tests use isolated temporary databases.

## Approval and outcome behavior

Every proposal starts pending. The existing `review_proposal` permits pending, defer and reject only; approval returns HTTP 409. There is no dispatch path. Reviewer opinions never imply an independently verified success label. Outcome records are stored separately, require named non-reviewer evidence and consistent chronology, and remain `simulation_evidence_recorded` with `real_outcome_verified=false`. The prototype cannot authenticate an external verifier or real field evidence. No real intervention completion is asserted.

## Limitations and remaining work

Traffic and trained flood joblib snapshots fail in native XGBoost restoration with `input stream corrupted`; models are not replaced or modified. The existing mass-balance simulator is a separate explicit scenario engine. Rainfall and PM2.5 examples are historical research, not current operational forecasts. Saved traffic evaluation charts remain archived results even while its Windows inference is unavailable.

IMD/CPCB feeds remain unavailable until verified gateways and station mappings exist. Their adapters validate source, identity, units, timestamps and freshness rather than synthesize data. No supported traffic observation source exists. Chandigarh/Chennai have no supplied trained forecasts. Geographic infrastructure mapping, real inventory, authorized operational approval, evidence authentication, model recovery and any future retraining remain separate work.

The separate Desktop application was inspected and left intact. It was not silently merged into this project; its independent route compatibility is not claimed. No cloud deployment was attempted because the requested FastAPI research environment, trained artifacts and local SQLite database are prepared on this Windows machine.

Start the application with `../START-CIVICFLUX.cmd`, then visit `http://127.0.0.1:8000`. Source and development instructions: `../APPLICATION.md`.
