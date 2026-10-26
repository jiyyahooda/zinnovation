# Civic Flux — premium interface

The existing React/Vite app is redesigned in place. Existing FastAPI routes, scientific models, notebooks, artifacts, preview scenarios, OR-Tools allocation and review rules are reused. No model scores or municipal facts have been invented.

## Run and build

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm build
cd ..
.venv/bin/python run_mac_app.py
```

The existing FastAPI server serves `frontend/dist`. There is no separate serving framework. Fresh clones need the Python dependencies and source datasets required by historical fixtures; see `DATASET_GUIDE.md` and `MAC_START.md`.

## Interface source

- `frontend/src/App.tsx`: floating navigation, responsive rail/menu, hash-based routes, theme switch, dashboard reveal, accessible credentials/guide dialogs and existing backend integration.
- `frontend/src/components/premium/SplitHero.tsx`: original CSS 3D civic structure, pointer tilt, synchronized left/right scroll splitting and introduction. Two identical structures are clipped into complementary halves. A requestAnimationFrame scroll handler writes CSS variables without rerendering the app on every frame. Reduced motion disables the split/float/tilt.
- `frontend/src/premium.css`: responsive editorial typography, strict palettes, geometric structure, map workbench, analytics and modal styles. Syne and Inter use Google Fonts with display swapping and system fallbacks. No stock imagery or third-party artwork is required.
- `frontend/src/components/CityMap.tsx`: search, layer filters, location browser, source drawer and map-provider fallback.
- `frontend/src/components/premium/GoogleMapCanvas.tsx`: official Google loader, advanced markers, clustering, native light/dark maps and Google TrafficLayer. Maps are recreated on color-scheme changes because Google defines colorScheme as an initialization option. Marker rendering follows each new map instance.
- `frontend/src/components/premium/LibreMapCanvas.tsx`: existing geographic map provider retained as a lazy-loaded fallback.
- `frontend/src/components/premium/DashboardAnalytics.tsx`: animated recorded-activity area chart, scenario dependency bar chart, crew-allocation donut and resource/connectivity progress rings.
- `frontend/src/components/premium/analytics.ts`: city-filtered, pure metric derivation with empty states.

## Google Maps configuration

The user-provided browser key is stored only in the ignored `frontend/.env.local`. Its value is not included in documentation, test reports or tracked source. Like all browser Maps keys, Vite places it in the browser bundle; a browser key is not a server secret. Restrict it to the intended HTTP referrers and Maps JavaScript API in Google Cloud. The compiled output is ignored by Git.

```
VITE_GOOGLE_MAPS_API_KEY=your_restricted_browser_key
VITE_GOOGLE_MAPS_MAP_ID=your_production_map_id
```

Rebuild after changing these values. The loader uses Google's `DEMO_MAP_ID` for local development when no Map ID is supplied. Replace this with your own Map ID before public production deployment. This concerns map styling/marker configuration, not the application's data sources. No billing account, account permissions or Cloud Console settings were changed.

Google TrafficLayer displays provider road-condition colors and refreshes them. It does not expose road-speed values to the application. Numeric traffic cards therefore retain their existing provider/scenario identity. This overlay is separate from the optional TomTom measurement feed. Weather/CAMS ingestion remains in the backend.

Official references:
- https://developers.google.com/maps/documentation/javascript/load-maps-js-api
- https://developers.google.com/maps/documentation/javascript/mapcolorscheme
- https://developers.google.com/maps/documentation/javascript/advanced-markers/start
- https://developers.google.com/maps/documentation/javascript/trafficlayer

## Metrics and source semantics

- Feed connectivity: number of fresh backend feeds / configured feeds. It is not model accuracy, city coverage or system uptime.
- Community activity: city-filtered local complaint, scenario and review records across seven days. These are workspace records, not municipal engagement statistics.
- Budget/pump utilization: selected scenario's solver-used capacity / declared inventory. Inventories remain planning assumptions until actual municipal data are supplied.
- Crew mix: allocated crew-hours per skill from the existing CP-SAT result.
- Dependency scores: mean/maximum saved scenario scores by node type, retaining the 60-minute horizon. They are not verified Delhi failure probabilities.
- No replacement sustainability index, emissions savings or causal intervention benefit is fabricated.
- No fake historical points are inserted to make charts look busy. No-data states remain available.

Source information is available in marker details, source status and scenario explanations. Existing geographic coverage guards and weak-model operational abstention remain unchanged.

## Accessibility and verification

Navigation works with keyboard and browser back/forward. Dialogs trap focus, restore focus when closed and close with Escape. Buttons retain accessible labels when their text is hidden on mobile. Reduced-motion preferences disable CSS motion and Recharts animation. The map also exposes a searchable location list.

Tests/reports are in `reports/premium_ui/` and `frontend/test-premium.cjs`. Existing `frontend/test-contracts.cjs` still checks nine model output cards and draft storage. Python tests exercise the preserved backend.

Before public deployment: configure your own restricted Maps key/Map ID, replace default admin credentials through server environment variables, choose production HTTPS/session settings and validate provider quotas and deployment-specific asset/data paths. This change is a locally verified implementation, not a claim that research models are validated for municipal dispatch.
