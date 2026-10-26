"""Focused contracts for caching, geography, preview isolation and provider errors."""
import asyncio,json
from datetime import datetime,timezone,timedelta
import pytest
from backend.services import live_service as svc
from backend.integrations.live import point,ProviderError,number
from backend.db.connection import connection

def sample():
    return point('delhi','fixture','d1',28.61,77.20,datetime.now(timezone.utc).isoformat(),{'temperature':{'value':25.,'unit':'°C'}},'modeled_weather',name='Fixture grid',layer='weather',provenance='test')

def test_last_good_cache_and_backoff(client,monkeypatch):
    calls=[]
    async def good(c):calls.append(c['id']);return [sample()]
    monkeypatch.setitem(svc.PROVIDERS,'weather',good)
    asyncio.run(svc.refresh('delhi','weather'));asyncio.run(svc.refresh('delhi','weather'))
    assert calls==['delhi']
    assert svc.snapshot('delhi')['points'][0]['status']=='fresh'
    with connection() as db:db.execute("UPDATE live_feeds SET next_attempt=?",((datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat(),))
    async def limited(c):raise ProviderError('Provider rate limit',600)
    monkeypatch.setitem(svc.PROVIDERS,'weather',limited)
    asyncio.run(svc.refresh('delhi','weather'))
    data=svc.snapshot('delhi');assert data['points'][0]['status']=='stale'
    assert data['feeds'][0]['last_success'] and data['feeds'][0]['reason']=='Provider rate limit'
    assert data['points'][0]['observed_at']!=None
    history=client.get('/api/workspace/history').json();assert len(history)==1
    assert 'retrieved_at' in history[0]

def test_stale_time_and_nonfinite(client):
    p=sample();p['observed_at']=(datetime.now(timezone.utc)-timedelta(hours=4)).isoformat();clock=datetime.now(timezone.utc).isoformat()
    with connection() as db:db.execute('INSERT INTO live_feeds VALUES (?,?,?,?,?,?,?)',('delhi','weather',json.dumps([p]),clock,clock,clock,None))
    assert svc.snapshot('delhi')['points'][0]['status']=='stale'
    for v in [float('nan'),float('inf'),True,None]:
        with pytest.raises(ValueError):number(v)
    with pytest.raises(ValueError):point('delhi','x','x',100,77,clock,{},'x')
    with pytest.raises(ValueError):point('delhi','x','x',28,77,'2020-01-01T00:00:00',{},'x')

def test_city_scope_and_geolocated_reports(client):
    body=dict(city_id='delhi',category='water',location='Test place',description='Test reading needs review',latitude=28.61,longitude=77.20)
    assert client.post('/api/complaints',json=body).status_code==201
    d=client.get('/api/workspace?city_id=delhi').json();ch=client.get('/api/workspace?city_id=chennai').json()
    assert len(d['reported_points'])==1 and not ch['reported_points']
    assert all(p['city_id']=='chennai' for p in ch['synthetic_points'])
    assert ch['coverage']['research_components']==[]
    assert client.get('/api/workspace?city_id=bogus').status_code==404
    assert client.post('/api/complaints',json={**body,'latitude':None}).status_code==422
    assert client.post('/api/complaints',json={**body,'city_id':'chennai'}).status_code==422
    assert d['synthetic_points']==client.get('/api/workspace?city_id=delhi').json()['synthetic_points']
    assert all(p['kind']=='synthetic_scenario' for p in d['synthetic_points'])

def test_preview_no_records_no_dispatch_and_trace(client):
    defaults=client.get('/api/scenarios/defaults').json()
    p=client.post('/api/scenarios/preview',json=defaults)
    assert p.status_code==200,p.text
    result=p.json();assert result['preview'] and not result['dispatch_allowed']
    assert client.get('/api/scenarios').json()==[]
    assert result['dependency_traces'] and any(t['paths'] for t in result['dependency_traces'])
    trace=client.get('/api/scenarios/trace?node=drainage_0').json()
    assert trace['horizon_minutes']==60
    assert client.get('/api/scenarios/trace?node=unknown').status_code==422
    assert client.get('/api/scenarios/trace?node=drainage_0&load=nan').status_code==422

def test_provider_http_retry_and_secret_sanitizing(monkeypatch):
    import httpx
    from backend.integrations import live
    count=[]
    class Fake:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,url,params):
            count.append(1)
            return httpx.Response(429,headers={'Retry-After':'999999'},request=httpx.Request('GET','https://test.invalid/?key=secret'))
    monkeypatch.setattr(live.httpx,'AsyncClient',lambda **kw:Fake())
    with pytest.raises(ProviderError) as e:asyncio.run(live.get_json('https://test.invalid',{'key':'secret'}))
    assert len(count)==1 and e.value.retry_after==3600 and 'secret' not in str(e.value)

def test_weather_air_and_traffic_contracts(monkeypatch):
    from backend.integrations import live
    from backend.services.city_service import city
    monkeypatch.setenv('CIVICFLUX_TOMTOM_KEY','test-only')
    stamp=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M')
    async def response(url,params):
        if 'forecast' in url:
            return [dict(current=dict(time=stamp,interval=900,temperature_2m=25,relative_humidity_2m=50,precipitation=1,wind_speed_10m=10),current_units={'temperature_2m':'°C','precipitation':'mm','wind_speed_10m':'km/h'}) for _ in range(5)]
        if 'air-quality' in url:return dict(current=dict(time=stamp,pm2_5=20,pm10=30,us_aqi=60),current_units={'pm2_5':'μg/m³'})
        assert params['unit']=='kmph'
        return dict(flowSegmentData=dict(currentSpeed=20,freeFlowSpeed=40,confidence=.9,coordinates={'coordinate':[{'latitude':28.61,'longitude':77.2},{'latitude':28.62,'longitude':77.21}]}))
    monkeypatch.setattr(live,'get_json',response)
    w=asyncio.run(live.weather(city('delhi')));a=asyncio.run(live.air(city('delhi')));t=asyncio.run(live.traffic(city('delhi')))
    assert w[0]['readings']['rainfall_rate']=={'value':4.,'unit':'mm/h'}
    assert a[0]['kind']=='modeled_air_quality' and a[0]['readings']['us_aqi']['unit']=='US AQI'
    assert t[0]['geometry']['coordinates'][0]==[77.2,28.61] and t[0]['observed_at'] is None
    assert all(not p['model_input_eligible'] for p in w+a+t)

def test_station_city_filter_coordinates_and_ist(monkeypatch):
    from backend.integrations import live
    from backend.services.city_service import city
    from zoneinfo import ZoneInfo
    monkeypatch.setenv('CIVICFLUX_DATA_GOV_KEY','test-only')
    stamp=datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%d-%m-%Y %H:%M:%S')
    async def response(*args):return {'records':[dict(city='Delhi',station='Test station',latitude='28.61',longitude='77.20',last_update=stamp,pollutant_id='PM2.5',pollutant_avg='42'),dict(city='Chennai',pollutant_id='PM2.5',pollutant_avg='900')]}
    monkeypatch.setattr(live,'get_json',response)
    rows=asyncio.run(live.stations(city('delhi')))
    assert len(rows)==1 and rows[0]['kind']=='station_observation'
    assert rows[0]['observed_at'].endswith('+05:30')
    assert rows[0]['readings']['pm25']['value']==42
