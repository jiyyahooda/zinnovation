def run(client,**changes):
    body=client.get('/api/scenarios/defaults').json();body.update(changes)
    response=client.post('/api/scenarios',json=body)
    assert response.status_code==200,response.text
    return response.json()

def test_public_cannot_mutate_scenarios(client):
    assert client.post('/api/scenarios',json={}).status_code==401

def test_same_graph_flood_cascade_and_resource_constraints(admin_client):
    result=run(admin_client)
    assert result['flood']['component']=='flood_mass_balance'
    assert result['flood']['prediction'][0]['depth_m']>=0
    assert result['cascade']['status']=='supported_simulation'
    assert result['cascade']['graph_fingerprint']==result['graph_fingerprint']
    allocation=result['allocation']['comparisons']['CP-SAT']
    assert allocation['status'] in {'OPTIMAL','FEASIBLE'}
    assert allocation['used']['budget']<=result['inputs']['resources']['budget']
    assert allocation['used']['pumps']<=result['inputs']['resources']['pumps']
    assert result['review_status']=='pending' and result['dispatch_allowed'] is False
    graph=admin_client.get('/api/scenarios/graph').json()
    assert all(c['node_id'] in {n['id'] for n in graph['nodes']} for c in result['allocation']['candidates'])
    for candidate in result['allocation']['candidates']:
        assert abs(sum(candidate['score_breakdown'].values())-candidate['utility'])<1e-9

def test_zero_inventory_and_missing_crew(admin_client):
    result=run(admin_client,resources={'budget':0,'pumps':0,'crew_hours':{'water':0,'road':0,'drain':0}})
    assert result['allocation']['comparisons']['CP-SAT']['selected']==[]
    body=admin_client.get('/api/scenarios/defaults').json();body['resources']['crew_hours']={}
    assert admin_client.post('/api/scenarios',json=body).status_code==422

def test_unknown_assets_and_unsupported_load_rejected(admin_client):
    body=admin_client.get('/api/scenarios/defaults').json()
    body['initial']=['Delhi_real_pump'];assert admin_client.post('/api/scenarios',json=body).status_code==422
    body['initial']=['pump_0'];body['load']=2
    assert admin_client.post('/api/scenarios',json=body).status_code==422

def test_incompatible_graph_manifest_rejected(admin_client,monkeypatch):
    import backend.services.scenario_service as service
    original=service.graph_fingerprint
    monkeypatch.setattr(service,'graph_fingerprint',lambda graph:'unmapped')
    body=admin_client.get('/api/scenarios/defaults').json()
    assert admin_client.post('/api/scenarios',json=body).status_code==409

def test_trained_flood_failure_is_explicit_without_fallback(admin_client):
    from pathlib import Path
    import json
    import os,sys
    root=Path(__file__).resolve().parents[1]
    checks=Path(os.environ.get('CIVICFLUX_CHECKS_DIR',str(root/'reports'/('macos' if sys.platform=='darwin' else 'windows')/'inference')))
    report=json.loads((checks/'flood.json').read_text())
    body=admin_client.get('/api/scenarios/defaults').json();body['flood_engine']='trained_surrogate'
    response=admin_client.post('/api/scenarios',json=body)
    if report['passed']: assert response.status_code==200
    else:
        assert response.status_code==409
        assert response.json()['detail']['flood']['prediction'] is None
