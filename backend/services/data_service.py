"""Normalize a deliberately explicit gateway contract without inventing readings."""
import math
from datetime import datetime, timezone

def normalize(payload,city,source):
    if not city['station_mapping']: raise ValueError('Verified station mapping is not configured')
    if payload['source']!=source or payload['city_id']!=city['id']: raise ValueError('Source/city identity mismatch')
    if payload['station_id'] not in city['station_mapping'].get(source,[]): raise ValueError('Unmapped station')
    stamp=datetime.fromisoformat(payload['observed_at'].replace('Z','+00:00'))
    if stamp.tzinfo is None: raise ValueError('Timezone-aware observation required')
    age=(datetime.now(timezone.utc)-stamp).total_seconds()
    if age<0: raise ValueError('Future observation')
    allowed={'IMD':{'rainfall':'mm','temperature':'degC'},'CPCB':{'pm25':'ug/m3','aqi':'index'}}[source]
    for metric,reading in payload['readings'].items():
        if metric not in allowed or reading['unit']!=allowed[metric] or isinstance(reading['value'],bool) or not math.isfinite(reading['value']): raise ValueError('Unsupported measurement or unit')
        if metric!='temperature' and reading['value']<0: raise ValueError('Negative reading')
    if not payload['readings']: raise ValueError('Empty observations')
    return {**payload,'status':'fresh' if age<=10800 else 'stale','age_seconds':age,'kind':'observation','model_input_eligible':False}
