from test_api_scenarios import run

def test_portal_workflow_persists_across_connections(admin_client):
    scenario=run(admin_client)
    identifier=scenario['id']
    assert admin_client.get('/api/scenarios/'+identifier).json()['id']==identifier
    assert admin_client.post('/api/feedback/'+identifier+'/review',json={'decision':'reject','note':'Resources require independent confirmation'}).status_code==200
    assert admin_client.get('/api/feedback').json()['reviews'][0]['scenario_id']==identifier
    assert len(admin_client.get('/api/audit').json())==2
    schema=admin_client.get('/openapi.json').json()
    assert '/api/scenarios' in schema['paths'] and '/api/complaints' in schema['paths']
