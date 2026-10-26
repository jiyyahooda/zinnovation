# Notebook 05 inference and evidence contract

Version: `civicflux.anomaly-evidence.v1`; model component `infrastructure_measurement_anomaly`, version `1.0.0`.

The actual CivicFlux infrastructure-risk layer, graph, optimizer, approval schema and asset registry were not found in the inspected project. No live API compatibility is claimed. The pure adapter is suitable as a future schema boundary, requiring backend-owner validation. Unrelated SAGE and AegisFlow schemas/services are not modified or reused as municipal telemetry.

## Standalone use

From `civicflux_ml/`, with its Python environment active:

```python
import joblib
import pandas as pd
from src.civicflux.anomaly import prepare_source, evidence_adapter

service = joblib.load('artifacts/infrastructure_anomaly/v1.0.0/detectors.joblib')
raw = pd.read_csv('data/raw/aqi/processed_aqi_data.csv')
history, _, _ = prepare_source(raw, 'aqi')
history = history.loc[history.sensor.eq('aqi:Delhi')]
output = service.predict(
    sensor='aqi:Delhi',
    history=history,
    observation_time=history.time.max(),
    detected_at=pd.Timestamp.now(tz='UTC'),
)
evidence = evidence_adapter(output)
```

The provided source is historical, so freshness is stale today. This is not a live monitor. Keep `src/` and `civicflux_core.py` importable, use recorded dependency versions, and only load trusted joblib files.

## Input contract

- Exactly one **source-qualified** sensor/entity, e.g. `traffic:1`; IDs are not municipal asset mappings.
- DataFrame fields `sensor`, `time`, `value`; optional `invalid`. Use `prepare_source` for downloaded schemas.
- Source-local naive observation timestamps with a registered `SensorSpec` clock. Indian source timezone is an explicit research assumption; traffic timezone is unknown. No implicit UTC conversion for unknown clocks.
- `detected_at` must be aware; default is actual current UTC. Future observations are rejected when the source clock is known. History beyond the requested observation is rejected.
- Provide full preceding history for identical expanding seasonal/global baselines. The service is stateless; it does not remember prior requests. Minimum finite prior context is required but merely meeting this minimum does not make a truncated history identical to full-history inference.
- Missing interior/tail cadence slots are materialized, invalid measurements become missing with a retained flag, conflicts/off-grid rows are rejected. No future interpolation.
- Detection timestamp is not a source receipt timestamp. No latency-adjusted online validity is claimed because source receipt-time fields are absent.

## Output semantics

Output contains component/version, supported entity, source URLs, geographic scope, units, observation time/timezone, UTC detection time, current-detection horizon, anomaly score, threshold, threshold-result flags, violated rules, contributing feature diagnostics, input freshness/last-valid age, provenance, validation status, synthetic/research flags and warnings.

`anomaly_score = -IsolationForest.score_samples`; higher is more unusual, **not** a probability. `isolation_alert` uses strict score > threshold. `quality_alert` independently covers missing/invalid/flatline candidate readings. `alert` means either warrants review. It is not a predicted equipment failure. The research rule and robust detector comparisons are separately saved in notebook experiment tables.

`synthetic=true` identifies an explicitly injected fixture. For AQI with unresolved upstream real/synthetic provenance, `synthetic=null`; it is not silently labeled verified real. All outputs remain `research_only=true`. Fixture provenance is carried by `history.attrs['synthetic_fixture']=True` in the testing helper; callers must preserve/set that flag when loading a fixture CSV according to its manifest.

Unknown/untrained sensor → `supported_sensor=false`, score/threshold/alert null and an abstention warning. No different sensor's model is substituted. Junction 4 is deliberately untrained under the common traffic cutoff. Insufficient history also abstains. Missing inputs may still receive a numerical imputed score, but a separate quality alert and warning prevent interpreting it as a normal measurement.

## Evidence-layer boundary

`evidence_adapter` has no network, database, graph mutation, approval or dispatch behavior. It returns:

- `asset_id: null`, `requires_verified_asset_mapping: true`
- `requires_corroboration: true`
- `confirmed_failure: false`
- `eligible_for_operational_risk_fusion: false`
- `automatic_dispatch_allowed: false`
- `approval_status: not_requested`

Nested output flags are also forced to research-only/non-failure/no-dispatch. Existing graphs may ingest this only as unmapped research evidence under their own contract validation; assigning an asset, changing a failure state or triggering resources is not implemented. Future operational use requires independently verified measurements/incidents, mapping, freshness policy, and explicit backend approval logic.
