# CivicFlux complete archive

This archive contains every regular file in the project folder at packaging time:
all research/model versions, notebooks, datasets, source, frontend build, dependency
files, both virtual environments, reports, caches, and local SQLite/test data.
No project directories were excluded. The enclosing workspace Git repository and
the original input ZIP are outside the project root and are not duplicated here.

Windows node_modules junctions are represented by PACKAGED-LINKS.json, retaining
their targets without recursively duplicating packages or following cycles. All
internal link targets are included. After extraction, run:

  powershell -ExecutionPolicy Bypass -File .\RESTORE-PACKAGED-LINKS.ps1

Alternatively, run pnpm install inside frontend to recreate the dependency links.
Virtual environments contain machine-specific interpreter paths. On another PC,
create a fresh environment using setup-windows.ps1 and a compatible Python; do not
activate the old macOS .venv. See APPLICATION.md for usage and the migration report
for model compatibility limitations. Admin demo credentials: ADMIN001 / 001.

Start with START-CIVICFLUX.cmd after environment setup. The compiled frontend is
included. Trained flood and traffic XGBoost snapshots currently fail to restore on
the verified Windows environment; seven other components pass. No model was
retrained or altered. IMD/CPCB feeds require verified configuration.

PACKAGE-MANIFEST.json records every regular file's byte length and SHA-256 hash.
The entire archive was read back and checked against this manifest.
