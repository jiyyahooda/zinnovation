# CivicFlux municipal command centre

Implemented in the existing project on 26 October 2026. The React/TypeScript, FastAPI, SQLite, Google Maps/MapLibre, NetworkX, model-serving and OR-Tools architecture is retained. No notebook was rewritten and no model was retrained.

## Navigation and working screens

One primary navigation contains **City Overview**, **City Map**, **Incidents**, **Action Plans**, and **Reviews & Reports**. Administrator connection/account/model diagnostics are secondary settings. Legacy page links redirect to an appropriate municipal view. The orange light theme, green dark theme, typography and interactive civic structure are retained; the introduction is compact so the map is easier to reach.

- **City Overview:** selected-city weather, report counts, attention queue, planning capacity, map and source health. Counts come from stored reports, not fabricated incident estimates.
- **City Map:** real Google Maps with traffic overlay, clusters, searchable location list, six issue filters, priority/status/source filtering and source-detail drawer. Weather estimates, air estimates, optional station/road readings, citizen reports and supplied verified assets use separate record types. Conceptual graph assets are excluded from the municipal map. Filters change marker contents and persist in the URL. Changing cities clears incompatible results while preserving each city's planning draft.
- **Incidents:** public report submission, optional coordinates/evidence reference, queue filters, officer review, confirmation, assignment to an authorized account, work progress, evidence-backed completion and separate authenticated officer verification. Records and audit stay in the existing SQLite database. No government complaint submission or dispatch occurs.
- **Action Plans:** seven intentional what-if presets, city-scoped persistent drafts, rainfall/drainage settings, one assessment-method control, resource controls and actual streamed processing stages. Duplicate clicks are disabled; successful results scroll into view, receive focus and are highlighted. Depth and classifier score outputs have separate semantics. Recommended, benefit-first and urgency-first alternatives show actual costs, pump units, crew-hours and unresolved candidates. Comparisons use the existing optimizer and identical feasibility constraints. Human-readable graph labels and dependency routes explain possible propagation. Internal review records which alternative was reviewed.
- **Reviews & Reports:** pending saved assessments, report review, completion/verification history and authenticated city audit. Internal plan approval does not imply dispatch, real incident confirmation or independently proven intervention benefit.
- **First-use guide:** explains connected estimates, source inspection, compatible historical models, conceptual scenarios and separate verification. Reopen with the help button.

## Live connections and coverage

Working without additional keys:

| Connection | Available information | Actual scope |
| --- | --- | --- |
| Open-Meteo | Temperature, precipitation/rate, humidity, wind | Five requested grid locations near each configured city; modeled estimates, not rain gauges |
| Open-Meteo / CAMS | PM2.5 and PM10 concentrations | One coarse modeled grid location per city; not a CPCB station |
| Google Maps | Base geography, clustering, Google visual traffic overlay | Provider coverage; visual traffic is not numeric speed data supplied to the backend |
| MapLibre / OpenStreetMap fallback | Base geography and application markers | Used if Google Maps is unavailable; it does not supply a Google traffic overlay |

The available configured cities are Delhi, Chennai and Chandigarh. Live requests and report queues are city-specific. Forecast benchmark coverage is not extended by changing a city name. No verified municipal pressure/depth telemetry or infrastructure inventory has been supplied. Resources and graph topology remain explicit planning assumptions. Historic anonymous-junction traffic counts are never converted to road speeds.

Optional backend connections are implemented but **not verified against live credentialed responses in this session**:

- `CIVICFLUX_DATA_GOV_KEY` in the project-root `.env`: CPCB pollutant snapshots through the [OGD resource](https://www.data.gov.in/resource/real-time-air-quality-index-various-locations), [registration/help](https://www.data.gov.in/help). Parsing includes selected-city filtering, coordinates, Asia/Kolkata timestamps, stable station identities and pollutant units. The resource does not establish full AQI averaging/completeness; the app does not infer a complete Indian AQI from it.
- `CIVICFLUX_TOMTOM_KEY` in project-root `.env`: [Flow Segment API](https://docs.tomtom.com/traffic-api/documentation/tomtom-maps/v1/traffic-flow/flow-segment-data). Adapter supports returned geometry, current/free-flow speed, travel times, confidence and closure flags. The current query is one road fragment near each city centre, not a citywide survey. The provider measurement timestamp is unavailable and remains null; retrieval time is separate. A separate TomTom incident-details ingestion service is not implemented.

[TomTom market coverage](https://docs.tomtom.com/traffic-api/documentation/tomtom-maps/v1/product-information/market-coverage) lists India. At review time, [official pricing](https://docs.tomtom.com/pricing) listed 20,000 monthly free Flow Segment requests; account eligibility, current quotas and usage terms still require the user's own account. Polling is cached for 30 minutes, with persistent default budgets of 18,000/month and 600/day (`CIVICFLUX_TOMTOM_MONTHLY_LIMIT`, `CIVICFLUX_TOMTOM_DAILY_LIMIT`). Actual retry attempts count toward limits. Other provider caches: weather/air 10 minutes, CPCB stations 60 minutes. Last-good data, last success/attempt, failure reason and stale status remain visible. Credentials remain server-side except Google's intentionally browser-scoped Maps key, configured in the ignored frontend environment file.

Indian AQI uses the official six category names. CAMS US AQI is not displayed as Indian AQI. Full NAQI remains unavailable until a suitable validated full-index source is connected. See [CPCB methodology](https://cpcb.nic.in/displaypdf.php?id=bWFudWFsLW1vbml0b3JpbmcvQVFJX05BTVBfUmVwX1NlcHRlbWJlcjIwMTYucGRm): pollutant averaging windows, minimum pollutants and completeness are necessary. A category utility is tested, but is not a substitute for a validated full-index source.

## Evidence and decision boundaries

No calculated utility is presented as a percentage reduction in real harm. Before/after intervention effects remain awaiting evidence. The optional drainage comparison calls the existing water-balance calculation while holding rainfall/catchment fixed and varying only drainage assumptions; it does not establish pump effectiveness. Candidate templates can include preventative work even with no initial outage. Selected candidates are not confirmed incidents.

Weak water-fault and intervention-success estimates remain excluded from operational allocation. The saved serving/abstention contracts are unchanged. A no-initial-outage scenario uses the existing no-spontaneous-failure propagation assumption and returns zeros as a scenario rule, not measured reliability.

Completion and verification are distinct. Verification requires evidence and a different authenticated officer from assignment/work/completion recorders. Evidence references are officer attestations; documents are not externally authenticated. File uploads and private contact storage are not implemented. Existing historical complaint routes remain for compatibility; the new municipal workflow uses the stricter review endpoint. Internal planning approval is separate from the legacy research endpoint, which continues to reject operational approval.

This remains a local research/municipal workflow application. Public Internet hosting needs deployment hardening, real officer account provisioning, a changed environment-configured administrator password, TLS, abuse protection and evidence retention policies. Existing development login defaults were not changed or embedded in the frontend. No external dispatch service is connected.

## Validation performed

- **80 Python tests passed**, including the original model-serving/abstention suite, report chronology and authorization, assignment account validation, distinct verification, internal-plan approval/alternative identity, streaming progress/error, normal-condition rule, drainage comparison constraints, Indian AQI bands/abstention and persistent traffic budgets/closure validation. Two dependency deprecation warnings remain.
- TypeScript strict project build and Vite production build passed. Vite retains a size warning for the lazy-loaded MapLibre fallback bundle.
- Frontend contract checks passed: nine prediction-card contracts; five draft persistence/error checks; premium analytics/hero checks; municipal geographic filtering, report identity, Indian-AQI abstention and distinct flood outputs.
- Browser checks exercised single navigation, light/dark themes, Google map and clustering, rainfall/air/traffic filters, source health and missing credentials, station marker metadata, Delhi→Chennai recentering, city-specific readings, persistent planning inputs, heavy-rainfall/scarcity previews, real progress/result focus, allocation alternatives and a full report lifecycle in a temporary database.
- Isolated browser workflow: public geolocated report → admin review → confirmed → assigned → in progress → completed with evidence → a second authenticated test officer verified it. A saved assessment was approved for **internal planning only**. Test accounts/reports were not added to the working database.
- Observed browser heavy-rainfall assessment (90 mm/6 h, declared pump outage, mass balance): **0.54 m** hypothetical depth; **12** conceptual services flagged; recommended plan **₹48,949**, **3/4 pumps**, **26 crew-hours**, **10 candidates selected**. Benefit-first selected 5 candidates, leaving ₹339; urgency-first selected 6, leaving ₹1,466. These are planning outputs, not measured outcomes.
- Initial narrow-window layout and 1440px desktop inspected. Desktop document had no horizontal overflow. A complete device/browser matrix and formal accessibility audit were not performed.
- SHA-256 comparison confirms **265 notebook/artifact files unchanged**, including all 11 notebooks. Reports are in `reports/municipal/`.

## Files and running the app

Primary new UI modules: `frontend/src/municipal/{Overview,MapWorkbench,Incidents,ActionPlans,PlanOptions,Settings}.tsx`, `domain.ts`, and `frontend/src/municipal.css`. The existing `App.tsx`, map, graph, shared types and entrypoint connect them. New backend modules are `backend/api/municipal.py`, `backend/services/municipal_service.py`, and the Indian-AQI/quota helpers. Existing authentication, SQLite schema, scenario, ingestion and workspace services were extended in place. Tests are `tests/test_municipal.py` and `frontend/test-municipal.cjs`.

The complete working-tree inventory, including the earlier interactive-design changes retained here, is saved as `reports/municipal/changed_files.txt`. No changes were automatically committed or pushed.

Launch with `.venv/bin/python run_mac_app.py`; open `http://127.0.0.1:8000/`. Build frontend changes with `pnpm build` from `frontend/` before starting the Mac launcher. Add optional provider credentials locally and restart the backend. The browser key must remain restricted to the intended origins/APIs in the user's Google Cloud account.
