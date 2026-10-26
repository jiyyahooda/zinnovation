# Executed research results

These numbers come from executed notebooks on the downloaded source files. Model selection used development CV only. Historical forecasts beyond each file end are not current-day forecasts.

| Task | CV-selected model | Final test metric | Interpretation |
|---|---|---|---|
| rainfall | Random Forest tuned | MAE 2.691; RMSE 7.779; R² 0.110 | MAE improvement over persistence 8.4%; interval coverage 88.1% |
| aqi | Ridge tuned | MAE 12.794; RMSE 15.967; R² 0.700 | MAE improvement over persistence 29.2%; interval coverage 90.9% |
| traffic | XGBoost tuned | MAE 3.249; RMSE 5.498; R² 0.958 | MAE improvement over persistence 14.6%; interval coverage 86.5% |
| flood | XGBoost tuned | AP 0.897; recall 0.980; precision 0.653 | Synthetic scenario labels only; not real flood validation |

Units: rainfall mm/day; traffic vehicles/hour; PM2.5 source concentration scale (µg/m³ is provisional, not verified upstream). The rainfall winner has limited explained variance and does not establish reliable extreme-event warning. PM2.5 provenance is unresolved. Flood scores measure approximation of an uncalibrated deterministic mass-balance simulator.

## Execution verification

- 01_Rainfall_Research.ipynb: 107 total cells, 46 executed code cells, 22 embedded figures, all 13 sections, zero errors.
- 02_AQI_Research.ipynb: 105 total cells, 45 executed code cells, 21 embedded figures, all 13 sections, zero errors.
- 03_Traffic_Research.ipynb: 107 total cells, 46 executed code cells, 22 embedded figures, all 13 sections, zero errors.
- 04_Flood_Research.ipynb: 99 total cells, 42 executed code cells, 19 embedded figures, all 13 sections, zero errors.

All four notebook export/reload checks passed. Eight separate integrity tests passed, covering future perturbation, missing interval labels, conflicting duplicates, temporal purges, scenario grouping, unit consistency, incident reporting availability and deterministic generation.

Three-fold temporal CV and six randomized settings per tuned family are a finite research budget. The full source table is inspected, but the default rainfall/PM2.5 model scope is Delhi only. Neither source publication latency nor local physical deployment validity has been established.
