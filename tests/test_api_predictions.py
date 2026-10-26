def test_historical_rainfall_and_operational_abstention(client):
    example=client.get('/api/predictions/rainfall/example').json()
    assert example['response']['status']=='supported_research'
    assert example['response']['uncertainty']['level']==.9
    request=client.get('/api/predictions/rainfall/fixture').json()
    request['purpose']='operational'
    result=client.post('/api/predictions/rainfall',json=request).json()
    assert result['status']=='abstained' and result['dispatch_allowed'] is False

def test_cities_do_not_invent_station_or_model_mapping(client):
    cities=client.get('/api/cities').json()
    assert len(cities)==3 and not any(c['verified_asset_mapping'] for c in cities)
    for city in cities:
        feeds=client.get('/api/observations',params={'city_id':city['id']}).json()['feeds']
        assert all(f['status']=='unavailable' and f['readings'] is None for f in feeds)
    assert client.get('/api/observations?city_id=unknown').status_code==404
    assert client.get('/api/predictions/missing/example').status_code==404
