# CivicFlux dashboard on this Mac

Double-click **Start_CivicFlux_Mac.command** to launch the dashboard and open your browser.

Default address: http://127.0.0.1:8000. If that port is occupied, the launcher chooses another local port and prints its address.

Demo admin login: **ADMIN001** / **001**, unless overridden in `.env`.

Keep the launcher Terminal window open while using the application. Press Control-C to stop it. Launching again reopens this project's existing server.

Terminal alternative:

```sh
./.venv/bin/python run_mac_app.py
```

The compiled frontend is served by the existing FastAPI backend; no Node development server is required. A local Python 3.13 environment was recreated using the bundled Mac scientific packages and this Mac's existing compatible serving packages. Windows environments and node_modules were excluded from extraction. The launcher configures the macOS OpenMP library path required by XGBoost.

Fresh Mac checks are saved in `reports/macos/inference/`. The dashboard reads these reports instead of the archived Windows checks. All nine saved components passed on this Mac, including traffic and flood. Original notebooks, trained models and Windows reports were retained.

Backend/API checks use temporary test databases; the included application records are retained in `var/civicflux.sqlite3`. The application remains research/demo software and preserves its existing review and dispatch restrictions.

## Geographic workspace upgrade

The dashboard now includes a geographic map, live weather/CAMS feeds, source status, city-scoped coverage, scenario previews, persistent planning drafts and explainable cascade traces. See [LIVE_WORKSPACE.md](LIVE_WORKSPACE.md) for provider setup and data semantics. Optional station and traffic keys belong in the project-root `.env`; they are never sent to the frontend.
