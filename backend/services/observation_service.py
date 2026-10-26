from datetime import datetime, timezone
from backend.integrations import imd,cpcb
from .city_service import city
from .data_service import normalize

async def observations(identifier):
    configuration=city(identifier);results=[]
    for source,adapter in [('IMD',imd),('CPCB',cpcb)]:
        try:
            if not configuration['station_mapping']: raise ValueError('Verified station mapping and supported source endpoint are not configured')
            payload=await adapter.fetch()
            if payload is None: raise ValueError('Source endpoint is not configured')
            results.append(normalize(payload,configuration,source))
        except Exception as error:
            results.append({'source':source,'status':'unavailable','readings':None,'reason':str(error),'kind':'observation'})
    from .live_service import snapshot
    results.extend(snapshot(identifier)['points'])
    return {'city_id':identifier,'checked_at':datetime.now(timezone.utc).isoformat(),'feeds':results}
