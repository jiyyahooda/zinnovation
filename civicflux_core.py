"""Auditable temporal features and deployable CivicFlux research bundles.

Shared serving code keeps notebook training and inference transformations identical.
No download, fitting, or external side effect happens at import time.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.model_selection import TimeSeriesSplit

SEED = 42
SOURCES = {
 'rainfall': 'wydoinn/daily-rainfall-data-india-2009-2024',
 'aqi': 'aniket0712/delhi-ncr-hourly-air-quality-dataset-20192024',
 'traffic': 'fedesoriano/traffic-prediction-dataset',
}
CONFIGS = {
 'rainfall': dict(file='rainfall/daily-rainfall-at-state-level.csv', time='date', entity='state_name', value='actual', freq='D', tz='Asia/Kolkata', unit='mm/day', lags=[1,2,3,7,14,30], windows=[3,7,14,30], selected='Delhi', date_format='%Y-%m-%d', provenance='reported real state aggregate; upstream lineage not independently audited'),
 'aqi': dict(file='aqi/processed_aqi_data.csv', time='timestamp', entity='location_name', value='pm25', freq='h', tz='Asia/Kolkata', unit='ug/m3 (working assumption; source unit metadata incomplete)', lags=[1,2,3,24,48,168], windows=[3,24,168], selected='Delhi', date_format='%Y-%m-%d %H:%M:%S', provenance='publisher-described measurements; station lineage and real/synthetic status unverified'),
 'traffic': dict(file='traffic/traffic.csv', time='DateTime', entity='Junction', value='Vehicles', freq='h', tz=None, unit='vehicles/hour', lags=[1,2,3,24,48,168], windows=[3,24,168], selected=None, date_format='%Y-%m-%d %H:%M:%S', provenance='observational benchmark; city, coordinates and timezone not supplied'),
}

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def canonicalize(raw, cfg):
    """Keep exact duplicates once; reject conflicting location-time observations.

    Negative concentrations/counts/rain become unavailable, never zero rain.
    No interpolation, future filling, or quantile clipping occurs here.
    """
    d = raw.drop_duplicates().copy()
    audit = {'raw_rows': len(raw), 'exact_duplicates_removed': len(raw)-len(d)}
    parsed = pd.to_datetime(d[cfg['time']], format=cfg['date_format'], errors='coerce')
    audit['invalid_timestamp_rows'] = int(parsed.isna().sum())
    if audit['invalid_timestamp_rows'] or d[cfg['entity']].isna().any():
        raise ValueError('Invalid timestamp/entity: inspect and repair explicitly before training')
    if cfg['tz']:
        parsed = parsed.dt.tz_localize(cfg['tz'], ambiguous='raise', nonexistent='raise')
    d['time'] = parsed
    d['entity'] = d[cfg['entity']].astype(str)
    d['value'] = pd.to_numeric(d[cfg['value']], errors='coerce')
    audit['negative_values_to_missing'] = int(d.value.lt(0).sum())
    d.loc[d.value.lt(0), 'value'] = np.nan
    key_dupes = d.duplicated(['entity','time'], keep=False)
    if key_dupes.any():
        raise ValueError(f'{key_dupes.sum()} conflicting entity-time rows; no arbitrary averaging allowed')
    if cfg.get('selected') is not None:
        d = d[d.entity.eq(str(cfg['selected']))]
    if d.empty:
        raise ValueError('Selected geography has no observations')
    pieces = []
    for entity, group in d.groupby('entity', sort=True):
        group = group.set_index('time').sort_index()
        grid = pd.date_range(group.index.min(), group.index.max(), freq=cfg['freq'])
        if not group.index.isin(grid).all():
            raise ValueError('Off-grid timestamps: document aggregation before training')
        q = group[['value']].reindex(grid).rename_axis('time').reset_index()
        q['entity'] = entity
        q['source_missing'] = q.value.isna().astype(int)
        pieces.append(q)
    result = pd.concat(pieces, ignore_index=True).sort_values(['time','entity']).reset_index(drop=True)
    audit['selected_rows_before_grid'] = len(d)
    audit['regular_grid_rows'] = len(result)
    audit['unavailable_values'] = int(result.value.isna().sum())
    return result, audit

def make_features(history, cfg, with_target=True):
    """Origin t is after the measurement for interval t is available.

    Label is t+one cadence, never the next irregular row. Grid regularization
    precedes this function. Historical rolling windows end at t, not t+1.
    """
    out = []
    for entity, g in history.groupby('entity', sort=True):
        g = g.sort_values('time').copy()
        x = g[['time','entity','source_missing']].copy()
        x['current'] = g.value
        for lag in cfg['lags']:
            x[f'lag_{lag}'] = g.value.shift(lag)
        for w in cfg['windows']:
            r = g.value.rolling(w, min_periods=1)
            x[f'mean_{w}'] = r.mean()
            x[f'std_{w}'] = r.std()
            x[f'coverage_{w}'] = r.count() / w
        x['change_1'] = g.value - g.value.shift(1)
        target_time = g.time + pd.tseries.frequencies.to_offset(cfg['freq'])
        x['target_time'] = target_time
        x['hour'] = target_time.dt.hour
        x['weekday'] = target_time.dt.dayofweek
        x['month'] = target_time.dt.month
        x['weekend'] = (x.weekday >= 5).astype(int)
        x['hour_sin'] = np.sin(2*np.pi*x.hour/24)
        x['hour_cos'] = np.cos(2*np.pi*x.hour/24)
        x['year_sin'] = np.sin(2*np.pi*target_time.dt.dayofyear/365.25)
        x['year_cos'] = np.cos(2*np.pi*target_time.dt.dayofyear/365.25)
        # Retain wet-hour/day information without asserting observed incident labels.
        x['positive_fraction'] = g.value.gt(0).where(g.value.notna()).rolling(cfg['windows'][-1], min_periods=1).mean()
        if with_target:
            x['target'] = g.value.shift(-1)
        out.append(x)
    return pd.concat(out).sort_values(['time','entity']).reset_index(drop=True)

def temporal_folds(frame, n_splits=3):
    """Split unique origins globally; purge labels at/after validation start.

    All junctions/scenarios on a date stay together. This avoids a row-wise
    TimeSeriesSplit accidentally training on another location's future.
    """
    times = np.sort(frame.time.unique())
    folds = []
    for tr, va in TimeSeriesSplit(n_splits=n_splits).split(times):
        start = times[va[0]]
        train = np.flatnonzero(frame.time.isin(times[tr]) & (frame.target_time < start))
        valid = np.flatnonzero(frame.time.isin(times[va]))
        if len(train) == 0 or len(valid) == 0:
            raise ValueError('Insufficient dates for temporal cross-validation')
        assert frame.iloc[train].target_time.max() < frame.iloc[valid].time.min()
        folds.append((train,valid))
    return folds

def partition(frame):
    """60% development, 20% calibration, 20% final test by unique origin."""
    times = np.sort(frame.time.unique())
    c1,c2 = times[int(.60*len(times))],times[int(.80*len(times))]
    dev = frame[(frame.time < c1) & (frame.target_time < c1)].copy()
    cal = frame[(frame.time >= c1) & (frame.time < c2) & (frame.target_time < c2)].copy()
    test = frame[frame.time >= c2].copy()
    return tuple(x.reset_index(drop=True) for x in (dev,cal,test))

class BaselineRegressor(RegressorMixin, BaseEstimator):
    """Persistence or train-only entity/calendar mean with train global fallback."""
    def __init__(self, strategy='persistence'):
        self.strategy = strategy
    def fit(self, X, y):
        self.fallback_ = float(np.mean(y))
        d = X.copy(); d['_y'] = np.asarray(y)
        self.keys_ = ['entity','month'] if X.hour.nunique() == 1 else ['entity','weekday','hour']
        self.lookup_ = d.groupby(self.keys_, observed=True)._y.mean()
        return self
    def predict(self, X):
        if self.strategy == 'persistence':
            return X.current.fillna(self.fallback_).to_numpy()
        keys = pd.MultiIndex.from_frame(X[self.keys_])
        return self.lookup_.reindex(keys).fillna(self.fallback_).to_numpy()

def regression_metrics(y, pred):
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    p = np.maximum(0, pred)
    return dict(MAE=float(mean_absolute_error(y,p)), RMSE=float(np.sqrt(mean_squared_error(y,p))), R2=float(r2_score(y,p)), bias=float(np.mean(p-y)))

class ForecastBundle:
    """Raw downloaded-schema history -> canonical grid -> features -> predictor.

    Model, schema, feature recipe, timezone and interval are exported together.
    No state from a prior request is kept. Caller must supply enough history.
    """
    def __init__(self, model, cfg, features, interval_radius, metadata):
        self.model, self.cfg, self.features = model, cfg, features
        self.interval_radius, self.metadata = float(interval_radius), metadata
    def predict(self, raw_history):
        h, _ = canonicalize(raw_history, self.cfg)
        f = make_features(h,self.cfg,with_target=False)
        last = f.sort_values('time').groupby('entity').tail(1).copy()
        counts = h.groupby('entity').size()
        if (counts < max(self.cfg['lags'])+1).any():
            raise ValueError('Supply at least max(lags)+1 regularly spaced history records per entity')
        pred = np.maximum(0,self.model.predict(last[self.features]))
        last['prediction'] = pred
        last['lower_90'] = np.maximum(0,pred-self.interval_radius)
        last['upper_90'] = pred+self.interval_radius
        return last[['entity','time','target_time','prediction','lower_90','upper_90','source_missing']].reset_index(drop=True)

FLOOD_FEATURES = ['rain_mm','duration_h','area_m2','runoff_coefficient','drain_mm_h','blockage','ponding_fraction','initial_storage_mm']

def simulate_depth(df):
    """Simple lumped mass balance, NOT a calibrated hydrodynamic solver.

    C*P is effective runoff depth; C lumps infiltration/interception losses.
    Q_capacity = drain_mm_h/1000 * catchment area * (1-blockage).
    Over a uniform storm of duration D, storage=max(0,S0+C*P-q*D).
    Ponding depth=storage/(1000*ponding_fraction). Maximum includes S0.
    No river overflow, backwater, topography, routing or pipe surcharge.
    """
    effective = df.rain_mm * df.runoff_coefficient
    capacity = df.drain_mm_h * (1-df.blockage) * df.duration_h
    storage = np.maximum(df.initial_storage_mm, np.maximum(0,df.initial_storage_mm+effective-capacity))
    return np.asarray(storage/(1000*df.ponding_fraction))

def generate_scenarios(rain_history, repeats=4, seed=SEED):
    """One observed state-day produces a group of independent hypothetical assets.

    No fitting to test-period distributions: each dated rainfall observation
    supplies its own forcing; all its scenario siblings share the split date.
    """
    rng=np.random.default_rng(seed)
    r=rain_history.dropna(subset=['value']).sort_values('time')
    d=r.loc[r.index.repeat(repeats),['time','value']].reset_index(drop=True)
    n=len(d)
    d=d.rename(columns={'value':'rain_mm'})
    d['event_id']=d.time.astype(str)
    d['scenario_id']=np.arange(n)
    d['duration_h']=rng.uniform(1,12,n)
    d['area_m2']=rng.uniform(10000,100000,n)
    d['runoff_coefficient']=rng.uniform(.3,.95,n)
    d['drain_mm_h']=rng.uniform(.2,8,n)
    d['blockage']=rng.uniform(0,.9,n)
    d['ponding_fraction']=rng.uniform(.03,.2,n)
    d['initial_storage_mm']=rng.uniform(0,2,n)
    d['depth_m']=simulate_depth(d)
    d['target']=(d.depth_m>=.15).astype(int)
    d['target_time']=d.time+pd.Timedelta(days=1)
    d['source_quality']='synthetic uncalibrated drainage; real state-level rain forcing'
    return d

class FloodBundle:
    def __init__(self, model, calibrator, threshold, metadata):
        self.model,self.calibrator,self.threshold,self.metadata=model,calibrator,float(threshold),metadata
    def predict(self, scenarios):
        X=scenarios[FLOOD_FEATURES].copy()
        if X.isna().any().any() or not np.isfinite(X.to_numpy()).all():
            raise ValueError('All documented scenario inputs must be finite')
        if (X[['rain_mm','initial_storage_mm']]<0).any().any() or (X[['duration_h','area_m2','drain_mm_h','ponding_fraction']]<=0).any().any():
            raise ValueError('Invalid physical units/ranges')
        if ((X[['runoff_coefficient','blockage','ponding_fraction']]<0)|(X[['runoff_coefficient','blockage','ponding_fraction']]>1)).any().any():
            raise ValueError('Fractions must be between zero and one')
        raw=self.model.predict_proba(X)[:,1]
        p=self.calibrator.predict(raw)
        return pd.DataFrame({'simulated_flood_probability':p,'scenario_alert':p>=self.threshold,'synthetic':True})

def historical_incidents(queries, incidents, window_days=30):
    """Optional true incident history, filtered by event AND report availability.

    None is unavailable, not zero incidents. No supplied dataset has such labels.
    """
    if incidents is None:
        return pd.Series(np.nan,index=queries.index)
    counts=[]
    for row in queries.itertuples():
        valid=incidents.entity.eq(row.entity)&(incidents.event_time<=row.time)&(incidents.reported_at<=row.time)&(incidents.event_time>row.time-pd.Timedelta(days=window_days))
        counts.append(int(valid.sum()))
    return pd.Series(counts,index=queries.index)
