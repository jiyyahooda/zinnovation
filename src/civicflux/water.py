"""BattLeDIM recent-leak-onset research; not real-city failure diagnosis."""
from pathlib import Path
import numpy as np
import pandas as pd

VERSION='1.0.0'
UNITS={'pressure':'m','flow':'m3/h','level':'m'}

def read_scada(path):
    d=pd.read_csv(path,sep=';',decimal=',')
    d['Timestamp']=pd.to_datetime(d.Timestamp,format='%Y-%m-%d %H:%M:%S',errors='raise')
    if d.Timestamp.duplicated().any():raise ValueError('Duplicate SCADA timestamps')
    return d.set_index('Timestamp').sort_index().apply(pd.to_numeric,errors='raise')

def load_benchmark(root):
    root=Path(root);measurements={}
    for kind in ['Pressures','Flows','Levels']:
        measurements[kind]=pd.concat([read_scada(root/f'{year}_SCADA_{kind}.csv') for year in [2018,2019]])
    leakages=pd.concat([read_scada(root/f'{year}_Leakages.csv') for year in [2018,2019]]).fillna(0)
    for d in list(measurements.values())+[leakages]:
        if not d.index.equals(measurements['Pressures'].index):raise ValueError('SCADA and label timestamps do not align exactly')
    return measurements,leakages

def water_features(measurements):
    """Downsample exact hourly instants; rolling windows end at observation t.

    Current readings are available for contemporaneous detection; all deltas
    and history windows are backward-looking. No leak-label columns are inputs.
    """
    blocks=[]
    for kind,prefix in [('Pressures','pressure'),('Flows','flow'),('Levels','level')]:
        d=measurements[kind].copy()
        if not d.index.is_monotonic_increasing or d.index.has_duplicates:raise ValueError('Unordered/duplicate time index')
        d=d.loc[(d.index.minute==0)&(d.index.second==0)].asfreq('h')
        d=d.replace([np.inf,-np.inf],np.nan)
        if prefix in ['pressure','level']:d=d.mask(d<0)
        for col in d:
            s=d[col];name=prefix+'__'+col
            blocks.append(pd.DataFrame({name:s,name+'__delta1':s.diff(),name+'__mean24':s.rolling(24,min_periods=12).mean(),name+'__missing':s.isna().astype(int)}))
    f=pd.concat(blocks,axis=1)
    f['hour_sin']=np.sin(2*np.pi*f.index.hour/24);f['hour_cos']=np.cos(2*np.pi*f.index.hour/24)
    f['weekday']=f.index.dayofweek
    return f

def onset_labels(leakages,index,hours=24):
    """Ground truth from first positive leakage flow per contiguous pipe episode.

    Label = one or more newly initiated leaks during preceding 24h. Negative
    does NOT mean leak-free; older continuing leaks can be present.
    """
    events=[]
    for pipe in leakages:
        active=leakages[pipe].gt(1e-6)
        starts=leakages.index[active & ~active.shift(1,fill_value=False)]
        for i,t in enumerate(starts):events.append({'event_id':f'{pipe}:{i}','pipe':pipe,'onset':t,'window_end':t+pd.Timedelta(hours=hours)})
    events=pd.DataFrame(events).sort_values('onset').reset_index(drop=True)
    target=pd.Series(0,index=index,dtype=int)
    for r in events.itertuples():target.loc[(index>=r.onset)&(index<r.window_end)]=1
    return target,events

def split_water(f,y,events):
    """Fixed calendar split; exclude onset windows crossing a split boundary."""
    boundaries=[pd.Timestamp('2018-09-01'),pd.Timestamp('2019-01-01')]
    labels=np.where(f.index<boundaries[0],'train',np.where(f.index<boundaries[1],'validation','test'))
    keep=f.index>=f.index.min()+pd.Timedelta(hours=24)
    for boundary in boundaries:
        for r in events.itertuples():
            if r.onset<boundary<r.window_end:
                keep &= ~((f.index>=r.onset-pd.Timedelta(hours=24))&(f.index<r.window_end+pd.Timedelta(hours=24)))
    d=f.copy();d['target']=y;d['period']=labels
    return d.loc[keep]

class WaterRule:
    """Train-only pressure drop / flow-rise reference rule, no label fitting."""
    def fit(self,X,y=None):
        self.cols_=[c for c in X if '__delta1' in c and c.startswith(('pressure__','flow__'))]
        self.median_=X[self.cols_].median();self.scale_=(X[self.cols_]-self.median_).abs().median().clip(lower=.05)*1.4826
        return self
    def predict_proba(self,X):
        score=((X[self.cols_]-self.median_)/self.scale_).abs().max(axis=1).fillna(0)
        p=np.clip(score/12,0,1).to_numpy()
        return np.column_stack([1-p,p])

class WaterBundle:
    def __init__(self,model,feature_names,sensors,threshold,metadata):
        self.model=model;self.features=feature_names;self.sensors=sensors;self.threshold=threshold;self.metadata=metadata
    def predict(self,measurements,units,network_id='L-TOWN',detected_at=None,purpose='research'):
        base={'component':'water_recent_leak_onset','version':self.metadata.get('version',VERSION),'network_id':network_id,'research_only':True,'synthetic_benchmark':True,
              'confirmed_failure':False,'dispatch_allowed':False,'provenance':'BattLeDIM simulated benchmark; not Delhi incidents',
              'status':'supported_research','operational_supported':False,
              'target':'a benchmark leak began within the preceding 24 hours','probability':None,'alert':None,'warnings':[]}
        if purpose!='research':
            base['status']='abstained';base['warnings']=['Operational fault prediction is unsupported: weak temporal validation.'];return base
        if network_id!='L-TOWN' or units!=UNITS:
            base['status']='abstained';base['warnings'].append('Unsupported network or units; abstained.');return base
        if set(measurements)!=set(self.sensors):raise ValueError('Missing sensor family')
        for kind,expected in self.sensors.items():
            d=measurements[kind]
            if list(d.columns)!=expected:raise ValueError('Unsupported sensor IDs/order')
            if d.index.tz is not None:raise ValueError('Benchmark timezone is unspecified; use documented naive source timestamps')
            if d.index.has_duplicates or not d.index.is_monotonic_increasing:raise ValueError('Invalid timestamps')
            if len(d)<24*12:base['status']='abstained';base['warnings'].append('Insufficient 24-hour context; abstained.');return base
            if not d.index.equals(measurements['Pressures'].index):raise ValueError('Unaligned sensor timestamps')
        f=water_features(measurements)
        if f.empty:raise ValueError('No exact hourly observations supplied')
        missing=float(f.iloc[-1][[c for c in self.features if c.endswith('__missing')]].mean())
        if missing>.1:
            base['status']='abstained'
            base['warnings'].append('More than 10% of current readings missing/invalid; abstained.');return base
        if f.index[-1]<=pd.Timestamp(self.metadata['train_end']):raise ValueError('Observation predates model cutoff')
        p=float(self.model.predict_proba(f[self.features].tail(1))[0,1])
        base.update(probability=p,alert=p>=self.threshold,threshold=self.threshold,observation_time=str(f.index[-1]),
                    detection_time=pd.Timestamp.now(tz='UTC').isoformat() if detected_at is None else pd.Timestamp(detected_at).isoformat(),
                    units=units,input_freshness='unknown: source timezone unspecified',missing_fraction=missing)
        base['warnings']=['Benchmark distribution only; recent-onset detection is not leak localization or proof of a fault.',
                          'Source clock/receipt latency is unspecified; no operational freshness claim.']
        return base
