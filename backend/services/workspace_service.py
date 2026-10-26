"""Separate geographic observations, reported incidents and synthetic assumptions."""
import json,math,random
from backend.services.city_service import city
from backend.services.live_service import snapshot
from backend.db import repository as repo
from project_paths import CONFIG

def workspace(identifier):
    c=city(identifier);out=snapshot(identifier);lat,lon=c['center'];rng=random.Random(identifier+'planning-v1');synthetic=[]
    for i in range(12):
        kind=['waterlogging','water','traffic','air_quality'][i%4];likelihood=round(rng.uniform(.15,.88),2)
        readings={'scenario_likelihood':{'value':likelihood*100,'unit':'%'}}
        if kind=='water':readings.update(pressure={'value':round(rng.uniform(1,4),1),'unit':'bar'},water_depth={'value':round(rng.uniform(.1,.8),2),'unit':'m'})
        if kind=='traffic':readings.update(speed={'value':round(rng.uniform(12,45),1),'unit':'km/h'},vehicle_count={'value':round(rng.uniform(100,600)),'unit':'vehicles/h'})
        synthetic.append(dict(id=f'{identifier}-scenario-{i}',city_id=identifier,name=f"What-if {kind.replace('_',' ')} {i+1}",latitude=round(lat+rng.uniform(-.065,.065),5),longitude=round(lon+rng.uniform(-.075,.075),5),layer='scenario',category=kind,source='Seeded planning assumptions v1',kind='synthetic_scenario',status='scenario',observed_at=None,retrieved_at=None,readings=readings,severity='high' if likelihood>.7 else 'medium' if likelihood>.4 else 'low',provenance='Illustrative coordinates and likelihood inputs; not detected incidents or calibrated model probabilities',model_input_eligible=False))
    reports=[dict(id=r['id'],name=r['location'],latitude=r['latitude'],longitude=r['longitude'],layer='reports',category=r['category'],kind='reported_incident',source='Community report',observed_at=r['created'],retrieved_at=r['created'],readings={},status=r['status'],severity=r.get('severity','unassessed'),provenance=r['provenance'],description=r['description'],report_id=r['id'],assigned_to=r.get('assigned_to')) for r in repo.all_records('complaint') if r['city_id']==identifier and r.get('latitude') is not None]
    assets=[]
    for f in json.loads((CONFIG/'geography/verified_assets.geojson').read_text()).get('features',[]):
        p=f.get('properties',{});g=f.get('geometry',{});coords=g.get('coordinates',[])
        if p.get('city_id')!=identifier or p.get('verified') is not True or not p.get('source') or g.get('type')!='Point':continue
        if len(coords)!=2 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in coords) or not (-180<=coords[0]<=180 and -90<=coords[1]<=90):continue
        assets.append(dict(id=str(f.get('id',p.get('id','asset'))),name=p.get('name','Verified asset'),longitude=coords[0],latitude=coords[1],source=p['source'],layer='assets',kind='verified_asset',category=p.get('category','infrastructure'),readings={},status='inventory',observed_at=p.get('verified_at'),retrieved_at=None,provenance=p.get('provenance',p['source'])))
    from backend.integrations.indian_aqi import unavailable
    station_points=[p for p in out['points'] if p['kind']=='station_observation']
    valid=[p for p in station_points if p.get('indian_aqi',{}).get('status')=='official' and p['status']=='fresh']
    out['indian_aqi']=valid[0]['indian_aqi'] if len(valid)==1 else unavailable()
    out['station_coverage']={'available_stations':len(station_points),'live_coverage_verified':bool(station_points),'scope':'Returned stations for the selected city only; no coverage is assumed when credentials or readings are missing.'}
    out.update(synthetic_points=synthetic,reported_points=reports,asset_points=assets,resources=dict(kind='synthetic_inventory',budget=50000,pumps=4,crew_hours={'water':24,'road':24,'drain':24},basis='Planning assumption, not municipal inventory. Resource categories informed by NDMA guidance; quantities illustrative.',source_url='https://www.niti.gov.in/sites/default/files/2021-03/Annexure-NDMA-Guidelines-compressed.pdf'))
    return out
