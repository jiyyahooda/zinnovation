"""Indian NAQI classification only; never infer full AQI from incomplete snapshots."""
import math
BANDS=[(50,'Good'),(100,'Satisfactory'),(200,'Moderate'),(300,'Poor'),(400,'Very Poor'),(500,'Severe')]
def category(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=500:raise ValueError('Invalid Indian NAQI')
    return next(name for upper,name in BANDS if value<=upper)
def unavailable():
    return {'value':None,'category':None,'scale':'Indian National AQI','status':'unavailable',
            'reason':'A complete official Indian AQI is not supplied in this pollutant snapshot. Validated averaging windows, at least three pollutants including PM2.5/PM10, and completeness checks are required; no value is inferred.'}
