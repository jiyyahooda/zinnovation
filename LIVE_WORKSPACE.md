# CivicFlux geographic and live-data workspace

Start the Mac app with `Start_CivicFlux_Mac.command`. The launcher prints and opens the actual localhost URL. Existing notebooks, trained artifacts and database records are preserved. No models are retrained by this upgrade.

## Available now

- MapLibre geographic map with OpenStreetMap tiles, clustering, layer toggles, location search, a keyboard-accessible location list, marker details, coordinate display and severity borders.
- Delhi, Chennai and Chandigarh have separate city-centre coordinates and separately collected API results. Local model coverage remains Delhi rainfall/AQI only; anonymous traffic and L-TOWN benchmark models remain in the research registry.
- Open-Meteo current weather at five query locations per city. Precipitation is an accumulation over the returned `interval`; the displayed mm/h is the equivalent rate over that interval, not a fabricated hourly rain-gauge total.
- Open-Meteo CAMS air estimates at each city centre: PM2.5, PM10 and US AQI. India uses the global CAMS product (~45 km grid). These are model estimates, not station observations or Indian NAQI. No pollution heatmap is interpolated from one coarse-grid estimate.
- Synthetic map points expose explicit planning likelihoods, pressures/depths or traffic values. Coordinates are illustrative. They have **no mapping** to synthetic graph asset IDs, and their likelihoods are not calibrated model output.
- Community reports can include coordinates; reports remain unverified and local. Both coordinates must be supplied and must lie within ±0.5 degrees of the chosen city centre (an approximate reporting-area guard, not a municipal boundary).
- `config/geography/verified_assets.geojson` accepts supplied point assets with `properties.city_id`, `verified: true`, `source`, `name` and optional `verified_at`. It starts empty. The flag represents the data maintainer's attestation; it does not independently verify municipal ownership.
- Existing NetworkX graph, Logistic Regression cascade scores, dependency traces, mass-balance flood simulator, flood surrogate and OR-Tools allocator are reused. What-if previews do not write scenarios/audit records or bypass human review. Sign in to persist scenarios.
- Hash navigation supports browser back/forward and page/city refresh. Drafts are saved by city in local browser storage. A storage failure is reported. Existing source data remain visible during a refresh, but previous-city data are hidden immediately.

## Optional station and traffic credentials

Create a project-root `.env` (ignored by version control), using `.env.example` as a template. Set your own keys server-side:

```
CIVICFLUX_DATA_GOV_KEY=your_data_gov_in_key
CIVICFLUX_TOMTOM_KEY=your_tomtom_key
```

Do not place these in frontend `VITE_` variables. Restart the Mac launcher after setting them. No account has been created, no private key has been borrowed, and these authenticated providers have not been verified with actual credentials.

- CPCB/OGD: https://www.data.gov.in/catalog/real-time-air-quality-index
  Resource: https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69
  Uses your registered API key, city-filtered station records, provider coordinates, pollutant averages, and IST timestamps. `pollutant_avg` retains the provider's aggregation semantics; no NAQI is computed from incomplete pollutant data. PM units are interpreted as standard µg/m³. License/publisher policy: check OGD NDSAP and the resource before reuse. The resource can change and requires a keyed smoke test before claiming station connectivity.
- TomTom: https://developer.tomtom.com/ and https://docs.tomtom.com/traffic-api/documentation/tomtom-maps/v1/traffic-flow/flow-segment-data
  Register for your own developer key and review current quotas/licensing. The adapter queries the road segment nearest the city centre. It displays current/free-flow speed in km/h, confidence and the returned road geometry. It does **not** represent complete city traffic coverage. The endpoint does not supply a measurement timestamp, so `observed_at` is null and retrieval time is shown explicitly. Tests use a controlled fixture until a real key is configured.
- Open-Meteo: https://open-meteo.com/en/docs and https://open-meteo.com/en/docs/air-quality-api
  Current JSON APIs require no key for eligible noncommercial evaluation. Attribution is required; paid/commercial service terms differ: https://open-meteo.com/en/pricing
- MapLibre: https://maplibre.org/ . Map tiles use https://tile.openstreetmap.org with visible attribution and browser caching. No prefetch/offline downloader. Review https://operations.osmfoundation.org/policies/tiles/ before scaling. Set `VITE_MAP_TILE_URL` at build time to use another licensed raster tile provider.

## Polling and failure behavior

`backend/integrations/live.py` → validated points → `live_feeds` / `live_history` SQLite tables → `/api/workspace` → map and section cards. `/api/observations` also includes collected live points alongside existing configured gateways.

- A background task checks all configured cities every minute. Successful provider results are cached for ten minutes; dashboard refresh does not hammer providers.
- Separate observation/reference and retrieval timestamps, finite numeric and unit checks, future-time rejection, UTC storage with explicit IST station parsing.
- Two bounded attempts for connection errors/5xx; 429 keeps last-good data and respects bounded backoff (120–3600 seconds).
- Failed/malformed responses preserve previous readings and expose stale status, last successful retrieval, next attempt and a sanitized reason. Readings older than three hours are stale even if recently retrieved.
- Seven days of local ingestion history are retained; charts only appear after distinct real provider timestamps exist. No synthetic history fills missing live data.
- Source-native gateway validation from the original backend is preserved.
- All new feed points are `model_input_eligible: false`. Online forecast inference requires a separate lineage/unit/history validation against the trained model. Displaying live conditions does not certify the historical models for those feeds.

## Resources, sustainability and incidents

Synthetic budget ₹50,000, 4 mobile pumps and 24 crew-hours in each skill match the existing backend defaults. Categories are informed by NDMA urban-flood guidance on pump sets and emergency squads; **the quantities are not sourced municipal inventory**:
https://www.niti.gov.in/sites/default/files/2021-03/Annexure-NDMA-Guidelines-compressed.pdf

The existing optimizer's utility and factor breakdown are displayed. Utility capture = selected utility / total positive candidate utility. It is a planning metric, not a measured city sustainability index. Environmental/service benefit factors are existing synthetic assumptions; no causal CO2 savings, water savings, affected population or effectiveness percentages are fabricated. Weak water-fault and outcome-success estimates do not enter allocation as operational facts. Waste-management features are excluded.

## Verification

- `reports/live_upgrade/full_tests.txt`: full Python test results.
- `frontend/test-contracts.cjs`: nine prediction-card fixtures and five draft/error checks.
- `reports/live_upgrade/live_status.json`: actual configured-city HTTP/source snapshot (generated during verification).
- `reports/live_upgrade/browser_checks.md`: manual browser checks and limitations.

Frontend build: use the project's pnpm lockfile and `pnpm build` from `frontend/`. MapLibre's worker is bundled explicitly for Vite. The compiled dashboard is served by the existing FastAPI application. No duplicate serving framework or notebook modifications.
