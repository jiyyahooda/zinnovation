import json
from datetime import datetime,timezone
from backend import config

def report(client):
    r=client.post('/api/complaints',json={'city_id':'delhi','category':'drainage','description':'Blocked drain needs an inspection.','location':'Test street','latitude':28.61,'longitude':77.20,'severity':'high','evidence_ref':'inspection-reference-1'})
    assert r.status_code==201,r.text
    return r.json()['id']
def login(client,user=None,password=None):
    return client.post('/api/auth/login',json={'username':user or config.ADMIN_ID,'password':password or config.ADMIN_PASSWORD})
def test_report_workflow_assignment_and_separate_verifier(client):
    ident=report(client);path=f'/api/municipal/reports/{ident}/review';body={'note':'Reviewed available evidence'}
    assert client.post(path,json={**body,'status':'under_review'}).status_code==401
    login(client)
    assert client.post(path,json={**body,'status':'completed','evidence_ref':'x-ref'}).status_code==409
    for state in ['under_review','confirmed']:
        assert client.post(path,json={**body,'status':state}).status_code==200
    assert client.post(path,json={**body,'status':'assigned','assigned_to':'unknown','department':'Drainage'}).status_code==422
    assert client.post(path,json={**body,'status':'assigned','assigned_to':config.ADMIN_ID,'department':'Drainage'}).status_code==200
    assert client.post(path,json={**body,'status':'in_progress'}).status_code==200
    assert client.post(path,json={**body,'status':'completed'}).status_code==422
    assert client.post(path,json={**body,'status':'completed','evidence_ref':'completion-record-1'}).status_code==200
    v={**body,'status':'verified','evidence_ref':'verification-record-1','verification_note':'Separate inspection confirms completion.'}
    assert client.post(path,json=v).status_code==422
    credentials={'username':'OFFICER02','password':'test-only-strong-password','department':'Audit'}
    result=client.post('/api/municipal/officers',json=credentials);assert result.status_code==201
    assert 'test-only' not in result.text
    client.post('/api/auth/logout');assert login(client,'OFFICER02',credentials['password']).status_code==200
    r=client.post(path,json=v);assert r.status_code==200,r.text
    assert r.json()['verification']['recorded_by']=='OFFICER02' and not r.json()['dispatch_allowed']
    assert client.post('/api/municipal/officers',json={**credentials,'username':'other'}).status_code==403
    assert len(r.json()['history'])==6
    assert any(a['event']=='report_verified' for a in client.get('/api/audit').json())
def test_analysis_progress_and_internal_planning_approval(client):
    defaults=client.get('/api/scenarios/defaults').json()
    response=client.post('/api/scenarios/analyze',json=defaults);assert response.status_code==200
    events=[json.loads(line) for line in response.text.splitlines()];assert [e['stage'] for e in events if e['event']=='progress' and e['state']=='running']==['Assessing drainage conditions','Checking connected services','Preparing response options']
    assert events[-1]['event']=='result' and events[-1]['result']['preview']
    assert client.post('/api/scenarios/analyze?save=true',json=defaults).status_code==401
    login(client);r=client.post('/api/scenarios/analyze?save=true',json=defaults)
    result=json.loads(r.text.splitlines()[-1])['result'];ident=result['id']
    decision=client.post(f'/api/municipal/plans/{ident}/review',json={'decision':'approve','note':'Approved for internal planning only'})
    assert decision.status_code==200 and not decision.json()['dispatch_allowed']
    assert decision.json()['approval_scope']=='internal_planning_only' and decision.json()['method']=='CP-SAT'
    alternative=client.post(f'/api/municipal/plans/{ident}/review',json={'decision':'defer','method':'utility_greedy','note':'Alternative needs additional capacity'})
    assert alternative.status_code==200 and alternative.json()['method']=='utility_greedy'
    # The legacy research contract remains unchanged.
    assert client.post(f'/api/feedback/{ident}/review',json={'decision':'approve','note':'Legacy contract must abstain'}).status_code==409
    assert result['response_options']['alternatives'][0]['name']=='Recommended plan'
def test_normal_conditions_and_counterfactual(client):
    defaults=client.get('/api/scenarios/defaults').json();defaults['initial']=[];defaults['flood']['rain_mm']=0
    r=client.post('/api/scenarios/preview',json=defaults);assert r.status_code==200,r.text
    assert all(row['risk']==0 for row in r.json()['cascade']['prediction'])
    before={**defaults['flood'],'rain_mm':90};after={**before,'drain_mm_h':6,'blockage':.1}
    c=client.post('/api/scenarios/counterfactual',json={'before':before,'after':after});assert c.status_code==200
    assert c.json()['after_depth_m']<c.json()['before_depth_m'] and not c.json()['causal_intervention_effect']
    assert client.post('/api/scenarios/counterfactual',json={'before':before,'after':{**after,'rain_mm':20}}).status_code==422
    assert client.get('/api/municipal/settings').status_code==401


def test_indian_aqi_bands_do_not_infer_missing_index():
    import pytest
    from backend.integrations.indian_aqi import category,unavailable
    assert [category(v) for v in [0,50,51,100,101,200,201,300,301,400,401,500]]==['Good','Good','Satisfactory','Satisfactory','Moderate','Moderate','Poor','Poor','Very Poor','Very Poor','Severe','Severe']
    for invalid in [-1,501,float('nan'),True,'42']:
        with pytest.raises(ValueError):category(invalid)
    assert unavailable()['value'] is None

def test_persistent_traffic_budget_and_closure_contract(client,monkeypatch):
    import asyncio
    from backend.integrations import quota,live
    from backend.services.city_service import city
    monkeypatch.setenv('CIVICFLUX_TOMTOM_DAILY_LIMIT','2')
    monkeypatch.setenv('CIVICFLUX_TOMTOM_MONTHLY_LIMIT','3')
    assert quota.reserve() and quota.reserve() and not quota.reserve()
    monkeypatch.setenv('CIVICFLUX_TOMTOM_KEY','test-fixture')
    flow={'currentSpeed':10,'freeFlowSpeed':40,'confidence':.9,'currentTravelTime':80,'freeFlowTravelTime':20,'roadClosure':False,'coordinates':{'coordinate':[{'longitude':77.2,'latitude':28.6},{'longitude':77.21,'latitude':28.61}]}}
    async def response(*args):return {'flowSegmentData':flow}
    monkeypatch.setattr(live,'get_json',response)
    row=asyncio.run(live.traffic(city('delhi')))[0]
    assert row['road_closure'] is False and row['observed_at'] is None
    assert row['readings']['currentTravelTime']=={'value':80.,'unit':'s'}
    assert row['congestion_ratio']==.25
    flow['roadClosure']='false'
    import pytest
    with pytest.raises(ValueError):asyncio.run(live.traffic(city('delhi')))

def test_unknown_asset_stream_abstains_and_legacy_status_safe(client):
    defaults=client.get('/api/scenarios/defaults').json();defaults['initial']=['not-a-network-node']
    response=client.post('/api/scenarios/analyze',json=defaults)
    events=[json.loads(line) for line in response.text.splitlines()]
    assert events[-1]['event']=='error' and not any(e['event']=='result' for e in events)
    ident=report(client);login(client)
    for status in ['under_review','confirmed']:
        assert client.post(f'/api/municipal/reports/{ident}/review',json={'status':status,'note':'Checked evidence'}).status_code==200
    assert client.post(f'/api/complaints/{ident}',json={'status':'closed','note':'Cannot skip new workflow'}).status_code==409
    assert client.get('/api/municipal/settings').status_code==200
