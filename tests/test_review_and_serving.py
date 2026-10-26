from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest
from src.civicflux.review import select_score_threshold,event_metrics
from src.civicflux.cascade import dependency_trace
from src.civicflux.graph import synthetic_graph,graph_fingerprint
from src.civicflux.integration import fixture,compatible_graph_evidence,review_proposal
from src.civicflux.serving import serve,discover
from src.civicflux.outcomes import OutcomeBundle,validate_outcome_record,generate_synthetic_outcomes
from src.civicflux.validation import recompute_metrics

ROOT=Path(__file__).resolve().parents[1]


def test_validation_threshold_covers_sub_grid_scores():
    t,curve=select_score_threshold([0,0,1,1],[.00001,.00002,.0003,.0004])
    assert t<.05
    assert curve.F1.max()==1
    assert np.array_equal(np.array([.00001,.00002,.0003,.0004])>=t,[False,False,True,True])


def test_all_alerts_do_not_hide_false_alert_duration():
    ix=pd.date_range('2020-01-01',periods=48,freq='h')
    y=np.r_[np.ones(24),np.zeros(24)]
    events=pd.DataFrame([{'event_id':'x','onset':ix[0],'window_end':ix[24]}])
    result,_=event_metrics(ix,y,np.ones(48),.5,events)
    assert result['event_recall']==1
    assert result['false_alert_hours']==24
    assert result['false_alert_hours_per_negative_day']==24


def test_trace_respects_direction_and_does_not_claim_realized_path():
    graph=synthetic_graph(42)
    result=dependency_trace(graph,['facility_0'],'pump_0')
    assert not result['paths']
    assert 'not realized' in result['semantics']


def test_unmapped_graph_evidence_cannot_be_fused():
    graph=synthetic_graph(42)
    evidence={'synthetic':True,'graph_id':graph.graph['graph_id'],'graph_fingerprint':graph_fingerprint(graph),'node_id':'pump_0'}
    assert compatible_graph_evidence(evidence,graph)
    assert not compatible_graph_evidence({**evidence,'synthetic':False},graph)
    assert not compatible_graph_evidence({**evidence,'graph_fingerprint':'unverified'},graph)


def test_operational_requests_and_wrong_units_abstain_before_model_load():
    req=fixture('resource_optimization',ROOT)
    for change in [{'purpose':'operational'},{'scope':'Delhi actual assets'},{'units':'USD'},{'horizon':'one year'}]:
        result=serve('resource_optimization',{**req,**change},ROOT)
        assert result['status']=='abstained'
        assert result['prediction'] is None and result['dispatch_allowed'] is False


def test_success_score_cannot_enter_resource_allocation():
    request=fixture('resource_optimization',ROOT)
    request['cases'][0]['success_probability']=.99
    response=serve('resource_optimization',request,ROOT)
    assert response['status']=='abstained'
    assert 'success estimates' in response['warnings'][0]


def test_review_adapter_never_grants_approval():
    proposal={'proposal_id':'SYN-DEMO'}
    assert review_proposal(proposal)['approval_status']=='not_approved'
    with pytest.raises(ValueError):review_proposal(proposal,'approve','automated agent')


def test_outcome_inference_suppresses_unsupported_success_probability():
    import joblib
    from src.civicflux.serving import directory_for
    bundle=joblib.load(directory_for(ROOT,'intervention_outcomes')/'pipeline.joblib')
    record=fixture('intervention_outcomes',ROOT)['record']
    prediction=bundle.predict(record)
    assert prediction['prediction_success_probability'] is None
    assert prediction['allocation_eligible'] is False
    assert prediction['predicted_resolution_hours']>0
    assert bundle.predict(record,purpose='operational')['status']=='abstained'


def test_verification_requires_chronology_and_matching_label():
    data=generate_synthetic_outcomes(100,seed=41)
    row=data[data.outcome_status.eq('verified_success')].iloc[0].to_dict()
    assert validate_outcome_record(row)
    with pytest.raises(ValueError):validate_outcome_record({**row,'verified_success':False})
    with pytest.raises(ValueError):validate_outcome_record({**row,'verification_time':row['assignment_time']})


def test_saved_metrics_are_consistent_and_missing_raw_flood_scores_explicit():
    checks,baselines=recompute_metrics(ROOT)
    assert not checks.status.eq('MISMATCH').any(),checks[checks.status.eq('MISMATCH')].to_dict('records')
    raw=checks[checks.component.eq('flood') & checks.metric.eq('Brier_raw')]
    assert raw.status.eq('not recomputable from saved predictions').all()
    assert set(baselines.component)=={'rainfall','aqi','traffic'}


def test_missing_artifacts_abstain_without_creating_replacements(tmp_path):
    from src.civicflux.serving import SCOPES,UNITS,HORIZONS
    req={'scope':SCOPES['rainfall'],'units':UNITS['rainfall'],'horizon':HORIZONS['rainfall'],'mode':'historical','as_of':'2020-01-01'}
    result=serve('rainfall',req,tmp_path)
    assert result['status']=='abstained' and result['prediction'] is None
    assert not list(tmp_path.iterdir())


def test_fresh_process_reports_cover_every_component_and_registered_sensor():
    from src.civicflux.validation import registry_with_checks
    from backend.services.prediction_service import checks_directory
    check_directory=checks_directory()
    registry=registry_with_checks(ROOT,check_directory)
    assert len(registry)==9
    for row in registry:
        report=json.loads((check_directory/(row['component']+'.json')).read_text())
        assert report['fresh_process'] and not report['jupyter_imported']
        assert (row['readiness']!='Not ready') == report['passed']
        assert all(r['status']=='abstained' and r['prediction'] is None for r in report['negative_cases'].values())
        if row['component']=='infrastructure_anomaly':
            assert set(report['sensor_results'])=={'rainfall:Delhi','aqi:Delhi','traffic:1','traffic:2','traffic:3'}


def test_stale_validation_report_does_not_certify_readiness(tmp_path):
    from src.civicflux.validation import registry_with_checks
    source=ROOT/'reports/integration/rainfall.json'
    report=json.loads(source.read_text());report['artifact_sha256']='wrong-artifact'
    (tmp_path/'rainfall.json').write_text(json.dumps(report))
    registry=registry_with_checks(ROOT,tmp_path)
    rainfall=next(r for r in registry if r['component']=='rainfall')
    assert rainfall['readiness']=='Not ready'


def test_completed_or_verified_record_cannot_omit_its_evidence_time():
    data=generate_synthetic_outcomes(100,seed=41)
    row=data[data.outcome_status.eq('verified_success')].iloc[0].to_dict()
    for change in [{'completion_time':None},{'verified_by':np.nan},{'verification_time':'NaT'},{'evidence_ref':''}]:
        with pytest.raises(ValueError):validate_outcome_record({**row,**change})


def test_simulated_disruptions_stay_within_directed_horizon_reachability():
    from src.civicflux.cascade import simulate_event,propagation_rule
    graph=synthetic_graph(104)
    for _,_,edge in graph.edges(data=True):edge['delay_minutes']*=2
    initial=['pump_0','drainage_0'];possible=propagation_rule(graph,initial,horizon=60)
    for seed in range(5):
        failed=simulate_event(graph,initial,1.2,seed,horizon=60)
        assert set(failed)-set(initial)<=possible
