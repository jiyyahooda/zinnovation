"""Public model feeds; optional authenticated station/road feeds. No browser secrets."""
import asyncio
import os
from datetime import datetime, timezone
import math
import httpx

class ProviderError(Exception):
    def __init__(self,message,retry_after=120):
        super().__init__(message);self.retry_after=retry_after

async def get_json(url,params):
    # Bounded retries; never include a URL containing credentials in public errors.
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=15,headers={'User-Agent':'CivicFlux/2.1 research dashboard'}) as client:
                response=await client.get(url,params=params)
            if response.status_code==429:
                try: delay=max(120,min(3600,int(response.headers.get('Retry-After','300'))))
                except ValueError: delay=300
                raise ProviderError('Provider rate limit; cached readings retained',delay)
            if response.status_code>=500 and attempt==0:
                await asyncio.sleep(.5);continue
            if response.status_code!=200: raise ProviderError(f'Provider returned HTTP {response.status_code}')
            return response.json()
        except (httpx.HTTPError,ValueError) as error:
            if attempt==0: await asyncio.sleep(.5);continue
            raise ProviderError('Provider connection or response failed') from error
    raise ProviderError('Provider unavailable')

def number(value,minimum=None,maximum=None):
    if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value):raise ValueError('Missing/nonfinite measurement')
    if minimum is not None and value<minimum or maximum is not None and value>maximum:raise ValueError('Measurement outside supported range')
    return float(value)

def point(city_id,source,identifier,lat,lon,stamp,readings,kind,**extra):
    number(lat,-90,90);number(lon,-180,180)
    when=datetime.fromisoformat(stamp.replace('Z','+00:00'))
    if when.tzinfo is None:raise ValueError('Timezone required')
    age=(datetime.now(timezone.utc)-when).total_seconds()
    if age< -300:raise ValueError('Future observation')
    for r in readings.values():number(r['value'])
    return dict(id=identifier,city_id=city_id,source=source,latitude=lat,longitude=lon,observed_at=when.isoformat(),
                retrieved_at=datetime.now(timezone.utc).isoformat(),readings=readings,kind=kind,model_input_eligible=False,**extra)

async def weather(c):
    lat,lon=c['center']; offsets=[(0,0),(.09,0),(-.09,0),(0,.09),(0,-.09)]
    coords=[(round(lat+a,5),round(lon+b,5)) for a,b in offsets]
    payload=await get_json('https://api.open-meteo.com/v1/forecast',dict(latitude=','.join(str(a) for a,b in coords),longitude=','.join(str(b) for a,b in coords),current='temperature_2m,relative_humidity_2m,precipitation,rain,wind_speed_10m',timezone='UTC'))
    rows=payload if isinstance(payload,list) else [payload];out=[]
    if len(rows)!=len(coords):raise ValueError('Incomplete weather response')
    for i,(data,(lat,lon)) in enumerate(zip(rows,coords)):
        current=data['current']; units=data['current_units'];interval=number(current['interval'],1)
        fields={'temperature':('temperature_2m','°C',None),'humidity':('relative_humidity_2m','%',0),'precipitation':('precipitation','mm',0),'wind_speed':('wind_speed_10m','km/h',0)}
        readings={k:dict(value=number(current[src],minimum),unit=unit) for k,(src,unit,minimum) in fields.items()}
        if units['temperature_2m']!='°C' or units['precipitation']!='mm' or units['wind_speed_10m']!='km/h':raise ValueError('Unexpected weather units')
        readings['rainfall_rate']={'value':readings['precipitation']['value']*3600/interval,'unit':'mm/h'}
        out.append(point(c['id'],'Open-Meteo',f"{c['id']}-weather-{i}",lat,lon,current['time']+'+00:00',readings,'modeled_weather',layer='weather',name=f"{c['name']} weather grid {i+1}",accumulation_seconds=interval,provenance='Current weather model estimate at requested coordinate; not a rain gauge',attribution='Open-Meteo · CC BY 4.0'))
    return out

async def air(c):
    lat,lon=c['center']
    payload=await get_json('https://air-quality-api.open-meteo.com/v1/air-quality',dict(latitude=lat,longitude=lon,current='pm2_5,pm10,us_aqi',timezone='UTC'))
    current=payload['current'];units=payload['current_units']
    if units['pm2_5'] not in ('μg/m³','µg/m³'):raise ValueError('Unexpected pollutant units')
    readings={k:dict(value=number(current[src],0),unit=unit) for k,src,unit in [('pm25','pm2_5','µg/m³'),('pm10','pm10','µg/m³'),('us_aqi','us_aqi','US AQI')]}
    return [point(c['id'],'Open-Meteo CAMS',f"{c['id']}-cams",lat,lon,current['time']+'+00:00',readings,'modeled_air_quality',layer='air',name=f"{c['name']} CAMS grid estimate",provenance='CAMS global modeled concentration, approximately 45 km resolution; not a monitoring station or Indian NAQI',attribution='CAMS ENSEMBLE / Open-Meteo · CC BY 4.0')]

async def stations(c):
    key=os.getenv('CIVICFLUX_DATA_GOV_KEY')
    if not key:raise ProviderError('Station API credential is not configured',600)
    data=await get_json('https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69',{'api-key':key,'format':'json','limit':1000,'filters[city]':c['name']})
    from zoneinfo import ZoneInfo
    grouped={}
    for r in data.get('records',[]):
        if r.get('city','').lower()!=c['name'].lower():continue
        metric={'PM2.5':'pm25','PM10':'pm10'}.get(r.get('pollutant_id'))
        if not metric or r.get('pollutant_avg') in (None,'NA',''):continue
        stamp=datetime.strptime(r['last_update'],'%d-%m-%Y %H:%M:%S').replace(tzinfo=ZoneInfo('Asia/Kolkata')).isoformat()
        ident=(r['station'],stamp); item=grouped.setdefault(ident,dict(r=r,readings={}))
        item['readings'][metric]={'value':number(float(r['pollutant_avg']),0),'unit':'µg/m³'}
    out=[point(c['id'],'CPCB / data.gov.in',f"{c['id']}-cpcb-{i}",float(v['r']['latitude']),float(v['r']['longitude']),stamp,v['readings'],'station_observation',layer='air',name=name,provenance='CPCB pollutant_avg from OGD; provider aggregation window applies; no Indian AQI inferred') for i,((name,stamp),v) in enumerate(grouped.items())]
    if not out:raise ProviderError('No valid station readings returned for selected city')
    return out

async def traffic(c):
    key=os.getenv('CIVICFLUX_TOMTOM_KEY')
    if not key:raise ProviderError('Traffic API credential is not configured',600)
    lat,lon=c['center'];data=await get_json('https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/15/json',dict(key=key,point=f'{lat},{lon}',unit='kmph'))
    r=data['flowSegmentData'];line=[[number(p['longitude'],-180,180),number(p['latitude'],-90,90)] for p in r['coordinates']['coordinate']]
    if len(line)<2:raise ValueError('Missing road geometry')
    readings={'speed':{'value':number(r['currentSpeed'],0),'unit':'km/h'},'free_flow_speed':{'value':number(r['freeFlowSpeed'],0),'unit':'km/h'},'confidence':{'value':number(r['confidence'],0,1),'unit':'ratio'}}
    # This API supplies no measurement timestamp. Do not fabricate one.
    p=point(c['id'],'TomTom',c['id']+'-traffic',line[0][1],line[0][0],datetime.now(timezone.utc).isoformat(),readings,'provider_current_traffic',layer='traffic',name='Provider road segment near city centre',geometry={'type':'LineString','coordinates':line},provenance='Current flow response; provider measurement timestamp unavailable')
    p['observed_at']=None;p['measurement_time_available']=False
    return [p]
