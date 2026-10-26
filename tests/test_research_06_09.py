import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier

from src.civicflux.water import water_features, WaterBundle, UNITS
from src.civicflux.graph import synthetic_graph, graph_config, from_config
from src.civicflux.cascade import node_features, CascadeBundle
from src.civicflux.optimization import solve_cpsat, greedy_allocate, assert_feasible, score_intervention, DEFAULT_WEIGHTS, validate_weights
from src.civicflux.outcomes import validate_outcome_record, verify_outcome, generate_synthetic_outcomes, leakage_safe_features, FEATURES


def _case(name, utility, cost=1, pumps=0, crew='water', hours=1):
    return {'case_id': name, 'urgency': utility, 'cascade': utility, 'service': utility,
            'equity_proxy': utility, 'environmental_benefit': utility, 'carbon_penalty': 0.0,
            'cost': cost, 'pumps_required': pumps, 'crew_type': crew, 'duration_hours': hours}


def test_optimizer_and_baselines_respect_identical_constraints():
    cases = [_case('a', .9, 4, 1), _case('b', .8, 3), _case('c', .7, 3, 1)]
    resources = {'budget': 6, 'pumps': 1, 'crew_hours': {'water': 2}}
    for result in [solve_cpsat(cases, resources), greedy_allocate(cases, resources, 'utility'), greedy_allocate(cases, resources, 'severity')]:
        assert_feasible(result['selected'], resources)
        assert result['dispatch_allowed'] is False
        assert result['approval_required'] is True


def test_water_features_do_not_change_past_when_future_changes():
    idx = pd.date_range('2020-01-01', periods=72, freq='h')
    raw = {'Pressures': pd.DataFrame({'P1': np.arange(72.)}, index=idx),
           'Flows': pd.DataFrame({'F1': np.arange(72.)}, index=idx),
           'Levels': pd.DataFrame({'T1': np.arange(72.)}, index=idx)}
    before = water_features(raw).loc[:idx[48]]
    changed = {k: v.copy() for k, v in raw.items()}
    for frame in changed.values(): frame.loc[idx[49]:] += 10_000
    after = water_features(changed).loc[:idx[48]]
    pd.testing.assert_frame_equal(before, after)


def test_graph_roundtrip_and_cascade_inference_are_reproducible():
    graph = synthetic_graph(seed=10, n_per_type=3)
    restored = from_config(graph_config(graph))
    assert set(graph.edges) == set(restored.edges)
    assert graph.graph['synthetic'] is True
    features = node_features(graph, ['pump_0'], 1.0)
    class FixedModel:
        def predict_proba(self, frame): return np.tile([.8, .2], (len(frame), 1))
    bundle = CascadeBundle(FixedModel(), .5, {})
    result = bundle.predict(restored, ['pump_0'], 1.0, '2024-01-01T00:00:00Z')
    assert len(result['nodes']) == len(features)
    assert result['dispatch_allowed'] is False and result['research_only'] is True
    with pytest.raises(ValueError): bundle.predict(restored, ['pump_0'], 2.0, '2024-01-01T00:00:00Z')


def test_outcome_label_requires_completed_work_and_verification():
    row = generate_synthetic_outcomes(20, seed=2).iloc[0].to_dict()
    features = leakage_safe_features(pd.DataFrame([row]))
    assert list(features.columns) == FEATURES
    for forbidden in ['verified_success', 'resolution_hours', 'verification_time']:
        assert forbidden not in features
    with pytest.raises(ValueError): verify_outcome(row, True, 'reviewer', 'evidence://x')
    assert validate_outcome_record(row)['source_type'] == 'synthetic'


def test_water_bundle_abstains_for_unsupported_network():
    class Model:
        def predict_proba(self, x): return np.array([[.8, .2]])
    bundle = WaterBundle(Model(), [], {}, .5, {'train_end': '2020-01-01'})
    result = bundle.predict({}, UNITS, network_id='Delhi')
    assert result['probability'] is None and result['confirmed_failure'] is False
    assert result['dispatch_allowed'] is False


def test_optimizer_applies_custom_sustainability_weights():
    case = _case('a', .5)
    case.update(urgency=1.0, cascade=0.0, service=0.0, equity_proxy=0.0, environmental_benefit=0.0, carbon_penalty=0.0)
    weights = validate_weights({'urgency': 0.0, 'cascade': 0.0, 'service': 0.0, 'equity_proxy': 0.0, 'environmental_benefit': 1.0, 'carbon_penalty': 0.0})
    result = solve_cpsat([case], {'budget': 2, 'pumps': 0, 'crew_hours': {'water': 1}}, weights=weights)
    assert result['objective'] == score_intervention(case, weights) == 0.0


class PickleableFixedModel:
    def predict_proba(self, frame): return np.tile([.25, .75], (len(frame), 1))


def test_cascade_bundle_artifact_serializes_and_reloads(tmp_path):
    import joblib
    graph = synthetic_graph(seed=11, n_per_type=2)
    bundle = CascadeBundle(PickleableFixedModel(), .5, {'version': 'test'})
    artifact = tmp_path / 'cascade.joblib'
    joblib.dump(bundle, artifact)
    loaded = joblib.load(artifact)
    result = loaded.predict(graph, ['pump_0'], 1.0, '2024-01-01T00:00:00Z')
    assert result['nodes'] and result['nodes'][0]['risk'] == .75
    assert result['dispatch_allowed'] is False


def test_water_bundle_constant_missing_unknown_and_stale_contracts():
    idx = pd.date_range('2020-01-01', periods=24 * 12 + 1, freq='5min')
    measurements = {
        'Pressures': pd.DataFrame({'P1': 20.0}, index=idx),
        'Flows': pd.DataFrame({'F1': 2.0}, index=idx),
        'Levels': pd.DataFrame({'T1': 1.5}, index=idx),
    }
    from src.civicflux.water import water_features
    features = list(water_features(measurements).columns)
    sensors = {key: list(frame.columns) for key, frame in measurements.items()}
    model = PickleableFixedModel()
    bundle = WaterBundle(model, features, sensors, .5, {'train_end': '2019-12-31'})
    assert bundle.predict(measurements, UNITS)['probability'] == .75
    missing = {key: frame.copy() for key, frame in measurements.items()}
    last_hour = idx[-1]
    missing['Pressures'].loc[last_hour, 'P1'] = np.nan
    assert bundle.predict(missing, UNITS)['probability'] is None
    unknown = {key: frame.copy() for key, frame in measurements.items()}
    unknown['Pressures'].columns = ['unknown_sensor']
    with pytest.raises(ValueError, match='Unsupported sensor'):
        bundle.predict(unknown, UNITS)
    stale = WaterBundle(model, features, sensors, .5, {'train_end': '2021-01-01'})
    with pytest.raises(ValueError, match='predates'):
        stale.predict(measurements, UNITS)
    aware = {key: frame.copy() for key, frame in measurements.items()}
    aware['Pressures'].index = aware['Pressures'].index.tz_localize('UTC')
    with pytest.raises(ValueError, match='timezone'):
        bundle.predict(aware, UNITS)
