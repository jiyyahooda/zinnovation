# Coverage against the supplied RTA notebook

The reference has 110 cells. Its structure is preserved where scientifically appropriate, with forecasting-specific corrections.

| RTA step | Corresponding CivicFlux treatment |
|---|---|
| Load original CSV | Section 02; immutable source checksum and exact acquisition guide |
| Head, shape, dtypes, cardinality | Section 03 in every notebook |
| Missingness table/graph | Sections 03 and 05; forecast labels never imputed |
| Duplicates | Exact duplicate audit; conflicting geographic-time keys rejected |
| Target distributions | Section 04; flood class imbalance explicitly graphed |
| Time parsing and buckets | Section 05/06; documented timezone and future-calendar values |
| Categorical encoding | One-hot location identity inside training-fold pipelines |
| Scaling | Ridge/Logistic only, inside CV; no full-dataset scaling |
| Leakage-prone feature removal | Explicit identifier/outcome exclusion and feature allowlists |
| Weather, road and lighting comparisons | Replaced with available pollutant/rainfall/junction/physical scenario EDA, not invented unavailable columns |
| Calendar and geography EDA | Month, weekday, hour, trends and group summaries |
| Correlation heatmap | Development-source correlations and feature/physics inspection |
| Train/test split | Chronological development/calibration/test, horizon purge and grouped timestamps |
| SMOTE comparison | Not meaningful for continuous regression; flood compares unweighted/weighted Logistic and tuned class weights without global oversampling |
| Baseline model training | Forecast persistence/seasonal/Ridge/RF/XGBoost; flood prior/Logistic/XGBoost |
| Cross-validation | Expanding chronological folds, never shuffled time rows |
| Hyperparameter search | Actual randomized searches with saved trial tables and plots |
| Select best model | Development CV only; test-set winner selection from the reference is not copied |
| Confusion matrix/report | Flood plus rainfall wet-day diagnostic; forecast errors for regression |
| Feature importance | Permutation importance of the selected model |
| SHAP summary and individual waterfall | All four notebooks; auxiliary tree explicitly labeled if a baseline wins |
| Feature reduction and retraining | Not automatically done after test importance; such selection would require nested training-only selection and a new held-out study |
| Export model/encoders/features/metadata | Full raw-history bundle or physical-scenario bundle, preprocessing, schema, source hash, calibration, versions and round-trip test |
| Added requested research steps | Prediction intervals/probability calibration, error slices, physical checks, CivicFlux typed payloads and separate synthetic disruption scenarios |

The notebooks do not copy exploratory findings or unavailable road-accident variables from the reference. Attached notebook contents are treated as reference material, not instructions to execute its installations or overwrite its files.
