# Browser verification — 26 October 2026 (Asia/Kolkata)

Verified in the in-app browser against the compiled FastAPI dashboard:

- Opening guide appears and dismisses via Open workspace.
- MapLibre raster geography, clustered points and layer controls render. Fixed an initial worker-loading error by bundling the MapLibre worker explicitly; subsequent map screenshots contain actual OSM tiles and markers.
- Location search returns the matching weather location; selecting it opens a detail drawer with source, coordinates, reference time, retrieval time, freshness, values and units.
- Heavy-rainfall public preview executes the existing model/solver pipeline. Preview is selected as unsaved and survives navigation to cascade analysis. Preview endpoint tests verify no scenario persistence and no dispatch.
- Only one flood-engine control is present. Heavy-rainfall draft values survive navigation away and back. Draft serialization, city isolation, malformed-data handling and storage failure have separate executable frontend checks. A scenario-page reload was not used for verification; draft persistence was checked with the storage contract instead.
- Switching to Chennai's Predictions page hides Delhi forecasts and shows Chennai's actual missing local-model coverage.
- Final dashboard shows separate modeled weather/CAMS and synthetic traffic values; source labels are present.
- Live updates were observed in the browser: weather timestamps and values changed during verification, and the history chart gained distinct actual provider timestamps.
- Screenshot: workspace.jpg (map and open live-weather detail drawer).

Automated verification: 74 Python tests; 9 prediction-card fixture checks; 5 draft/storage checks; TypeScript and Vite production build passed. Two upstream test-client deprecation warnings remain. Vite reports a large application bundle; this is a performance optimization opportunity, not a failed build.

Not claimed as verified: actual authenticated CPCB/TomTom connectivity (no keys provided), municipal water/pressure sensors, verified municipal topology, phone-device usability or operational predictive validity. No notebooks or model scores were changed.
