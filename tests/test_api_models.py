def test_inventory_uses_existing_registry_and_fresh_windows_checks(client):
    rows=client.get('/api/models').json()
    assert len(rows)==9
    water=next(r for r in rows if r['component']=='water_network')
    assert water['version']=='1.1.0'
    assert all(r['operational_supported'] is False for r in rows)
    assert client.get('/api/health').json()['automatic_dispatch'] is False

def test_registry_selection_ignores_unregistered_newer_version(tmp_path):
    import json
    from src.civicflux.serving import directory_for
    registry=tmp_path/'artifacts/model_validation/v1.0.0';registry.mkdir(parents=True)
    (registry/'model_registry.json').write_text(json.dumps([{'component':'water_network','artifact_directory':'artifacts/water_network/v1.0.0'}]))
    (tmp_path/'artifacts/water_network/v99.0.0').mkdir(parents=True)
    assert directory_for(tmp_path,'water_network').name=='v1.0.0'
