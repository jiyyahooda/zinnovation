"""Causal measurement-anomaly research, NOT equipment-failure diagnosis.

Each source/entity has its own detector and unit contract. No geographic join,
network call, dispatch operation, or training happens at module import.
"""
from __future__ import annotations
from dataclasses import dataclass
from copy import deepcopy
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.utils.validation import check_is_fitted
from civicflux_core import CONFIGS, SOURCES, canonicalize

VERSION = '1.0.0'
FEATURES = ['value','rolling_mean','rolling_std','rolling_median','rolling_mad',
            'rolling_min','rolling_max','robust_z','rate_change','seasonal_residual',
            'baseline_deviation','missing','invalid','missing_fraction',
            'flat_run','previous_unusual_count','hours_since_valid','hour_sin','hour_cos']

@dataclass(frozen=True)
class SensorSpec:
    sensor: str
    family: str
    entity: str
    unit: str
    cadence: str
    timezone: str | None
    provenance: str
    source_url: str
    window: int = 24
    flat_limit: int = 12
    scale_floor: float = 1.0
    freshness_hours: float = 2.0

def prepare_source(raw, family):
    """Reuse the existing canonicalizer but preserve invalid-input evidence.

    Times remain on each source's wall-clock grid; the timezone contract is
    retained separately. They are NEVER used for cross-source matching.
    """
    cfg=CONFIGS[family].copy()
    if raw.drop_duplicates().duplicated([cfg['time'],cfg['entity']]).any():
        raise ValueError('Conflicting raw entity-time records; resolve before sanitizing values')
    # Delhi scope for environmental series; all benchmark traffic junctions.
    original=pd.to_numeric(raw[cfg['value']],errors='coerce')
    flagged=raw[[cfg['time'],cfg['entity']]].copy()
    flagged['invalid']=((raw[cfg['value']].notna() & original.isna()) |
                        (original.notna() & (~np.isfinite(original) | original.lt(0)))).astype(int)
    safe=raw.copy()
    safe[cfg['value']]=original.where(np.isfinite(original) & original.ge(0))
    h,audit=canonicalize(safe,cfg)
    flagged['time']=pd.to_datetime(flagged[cfg['time']],format=cfg['date_format'],errors='raise')
    flagged['entity']=flagged[cfg['entity']].astype(str)
    if cfg['tz']: h['time']=h.time.dt.tz_localize(None)
    flags=flagged.groupby(['entity','time'],as_index=False).invalid.max()
    h=h.merge(flags,on=['entity','time'],how='left',validate='one_to_one')
    h['invalid']=h.invalid.fillna(0).astype(int)
    h['sensor']=family+':'+h.entity
    specs={}
    for entity in h.entity.unique():
        sensor=family+':'+entity
        daily=cfg['freq']=='D'
        specs[sensor]=SensorSpec(sensor,family,entity,cfg['unit'],cfg['freq'],cfg['tz'],cfg['provenance'],
                                'https://www.kaggle.com/datasets/'+SOURCES[family],
                                30 if daily else 24,5 if daily else 12,.1 if daily else 1.,48. if daily else 2.)
    return h[['sensor','time','value','invalid']],specs,audit

def regularize(history, spec, end=None):
    """Validate one history and materialize missing cadence slots, including tail.

    Duplicate conflicts and off-grid timestamps are rejected. The end argument
    represents an expected scheduled reading, never an observed measurement.
    """
    h=history.copy()
    if h.empty: raise ValueError('History is empty')
    if set(h.sensor.astype(str)) != {spec.sensor}: raise ValueError('Mixed or mismatched sensor identities')
    h['time']=pd.to_datetime(h.time,errors='raise')
    if h.time.dt.tz is not None: raise ValueError('Provide source-local naive timestamps and an explicit SensorSpec timezone')
    h=h.drop_duplicates()
    if h.time.duplicated().any(): raise ValueError('Conflicting timestamps require an auditable resolution')
    h=h.sort_values('time').set_index('time')
    end=pd.Timestamp(end) if end is not None else h.index.max()
    if end<h.index.max(): raise ValueError('History includes future rows beyond the requested observation time')
    grid=pd.date_range(h.index.min(),end,freq=spec.cadence)
    if grid[-1]!=end or not h.index.isin(grid).all(): raise ValueError('Off-grid timestamp')
    if len(grid)>1000000: raise ValueError('Grid too large for this research serving component')
    h=h.reindex(grid).rename_axis('time').reset_index()
    raw=h.value
    value=pd.to_numeric(raw,errors='coerce')
    invalid=(raw.notna() & (value.isna() | ~np.isfinite(value) | value.lt(0)))
    if 'invalid' in h: invalid=invalid | h.invalid.fillna(0).astype(bool)
    h['invalid']=invalid.astype(int)
    h['value']=value.mask(invalid)
    h['sensor']=spec.sensor
    return h[['sensor','time','value','invalid']]

def causal_features(history, spec, end=None):
    """Features at t use the current reading plus history STRICTLY before t.

    Reference rolling statistics, seasonal expectations and previous unusual
    counts exclude the current reading. No train/test fitted seasonal lookup
    is reused retroactively: same-slot means expand and shift by one.
    """
    h=regularize(history,spec,end)
    v=h.value
    past=v.shift(1)
    r=past.rolling(spec.window,min_periods=3)
    f=h.copy()
    f['rolling_mean']=r.mean();f['rolling_std']=r.std()
    f['rolling_median']=r.median()
    def mad(a):
        med=np.nanmedian(a)
        return float(np.nanmedian(np.abs(a-med)))
    f['rolling_mad']=r.apply(mad,raw=True)
    f['rolling_min']=r.min();f['rolling_max']=r.max()
    denominator=np.maximum(1.4826*f.rolling_mad,spec.scale_floor)
    f['robust_z']=(v-f.rolling_median)/denominator
    f['rate_change']=v-past
    # Each seasonal slot learns only from its own earlier observations.
    slot=h.time.dt.month if spec.cadence=='D' else h.time.dt.dayofweek*24+h.time.dt.hour
    seasonal=v.groupby(slot).transform(lambda x:x.shift(1).expanding(min_periods=2).mean())
    causal_global=past.expanding(min_periods=3).mean()
    f['seasonal_expected']=seasonal.fillna(causal_global)
    f['seasonal_residual']=v-f.seasonal_expected
    scale=np.maximum(past.expanding(min_periods=3).std(),spec.scale_floor)
    f['baseline_deviation']=(v-causal_global)/scale
    f['missing']=v.isna().astype(int)
    f['missing_fraction']=past.isna().rolling(spec.window,min_periods=1).mean()
    equal=v.notna() & past.notna() & v.eq(past)
    runs=(~equal).cumsum()
    f['flat_run']=equal.groupby(runs).cumcount()+1
    f.loc[v.isna(),'flat_run']=0
    unusual=f.robust_z.abs().gt(6) & f.robust_z.notna()
    f['previous_unusual_count']=unusual.shift(1,fill_value=False).rolling(spec.window,min_periods=1).sum()
    last_valid=h.time.where(v.notna()).ffill()
    f['hours_since_valid']=(h.time-last_valid).dt.total_seconds()/3600
    f['hour_sin']=np.sin(2*np.pi*h.time.dt.hour/24)
    f['hour_cos']=np.cos(2*np.pi*h.time.dt.hour/24)
    f['ready']=past.expanding().count().ge(spec.window)
    return f

def assign_periods(features):
    """60/20/20 within each source clock; all traffic junctions share cutoffs.

    A late-appearing junction with no development history remains unsupported.
    There is no forecast target or horizon purge for contemporaneous detection.
    """
    frames=[]; boundaries={}
    for family,f in features.groupby(features.sensor.str.split(':').str[0]):
        times=np.sort(f.time.unique());a,b=times[int(.6*len(times))],times[int(.8*len(times))]
        g=f.copy();g['period']=np.where(g.time<a,'train',np.where(g.time<b,'validation','test'))
        boundaries[family]={'train_end_exclusive':str(a),'test_start':str(b)}
        frames.append(g)
    return pd.concat(frames,ignore_index=True),boundaries

class DetectorSuite:
    """One fitted suite per source-qualified sensor; no identity pooling."""
    def __init__(self,spec,n_estimators=100,max_samples=256,contamination=.02,seed=42):
        self.spec=spec;self.n_estimators=n_estimators;self.max_samples=max_samples
        self.contamination=contamination;self.seed=seed
    def fit(self,train):
        if not 0<self.contamination<=.5: raise ValueError('contamination must be in (0, .5]')
        if set(train.sensor)!={self.spec.sensor}: raise ValueError('Training identity mismatch')
        x=train.loc[train.ready].copy()
        if len(x)<100: raise ValueError('At least 100 ready historical observations required')
        self.train_end_=x.time.max()
        self.fit_rows_=len(x)
        self.upper_=max(float(x.value.quantile(.995)),self.spec.scale_floor)
        self.jump_=max(float(x.rate_change.abs().quantile(.995)),self.spec.scale_floor)
        self.pipeline_=Pipeline([('impute',SimpleImputer(strategy='median',keep_empty_features=True)),
            ('forest',IsolationForest(n_estimators=self.n_estimators,max_samples=min(self.max_samples,len(x)),
                                     contamination=self.contamination,random_state=self.seed,n_jobs=2))])
        self.pipeline_.fit(x[FEATURES])
        self.reference_=x[FEATURES].median().fillna(0)
        self.reference_scale_=(x[FEATURES].quantile(.75)-x[FEATURES].quantile(.25)).clip(lower=self.spec.scale_floor)
        self.isolation_threshold_=-float(self.pipeline_.named_steps['forest'].offset_)
        self.train_scores_=-self.pipeline_.score_samples(x[FEATURES])
        return self
    def score(self,features,allow_training=False):
        check_is_fitted(self,'pipeline_')
        if set(features.sensor)!={self.spec.sensor}: raise ValueError('Unknown/mixed sensor cannot use another sensor model')
        if not allow_training and (features.time<=self.train_end_).any():
            raise ValueError('Out-of-sample scoring must be after training cutoff')
        f=features.copy()
        if f.empty: raise ValueError('No feature rows')
        flat=f.flat_run.ge(self.spec.flat_limit)&f.value.notna()
        if self.spec.family=='rainfall':flat &= f.value.gt(0) # Dry spells are not automatically flatlined sensors.
        quality=f.missing.astype(bool)|f.invalid.astype(bool)|flat
        upper=f.value.gt(self.upper_);jump=f.rate_change.abs().gt(self.jump_)
        rule=(quality|upper|jump)
        rule_score=pd.concat([f.value/self.upper_,f.rate_change.abs()/self.jump_,quality.astype(float)*2],axis=1).max(axis=1)
        robust=f.robust_z.abs()
        isolation=-self.pipeline_.score_samples(f[FEATURES])
        result=f[['sensor','time','value','ready','missing','invalid','hours_since_valid']].copy()
        result['rule_score']=rule_score;result['rule_alert']=rule
        result['robust_score']=robust;result['robust_alert']=robust.gt(6)
        result['isolation_score']=isolation;result['isolation_alert']=isolation>self.isolation_threshold_
        result['quality_alert']=quality
        result['review_alert']=quality|result.isolation_alert
        result['violated_rules']=[','.join(name for name,yes in [('missing_reading',m),('invalid_reading',i),('flatline_candidate',fl),('above_train_p995',u),('abrupt_change',j)] if yes)
                                 for m,i,fl,u,j in zip(f.missing,f.invalid,flat,upper,jump)]
        return result
    def diagnose(self,row,top=5):
        """Controlled model-score sensitivity, not causal attribution or SHAP.

        Replace one feature with its training median while holding others
        fixed. Correlated/inconsistent combinations limit interpretation.
        """
        check_is_fitted(self,'pipeline_')
        x=row[FEATURES].iloc[[0]].copy()
        original=-float(self.pipeline_.score_samples(x)[0])
        diagnostics=[]
        for name in FEATURES:
            changed=x.copy();changed[name]=self.reference_[name]
            score=-float(self.pipeline_.score_samples(changed)[0])
            value=x.iloc[0][name]
            diagnostics.append({'feature':name,'value':None if pd.isna(value) else float(value),
                                'training_median':float(self.reference_[name]),
                                'score_drop_on_median_replacement':original-score})
        return sorted(diagnostics,key=lambda z:abs(z['score_drop_on_median_replacement']),reverse=True)[:top]

class AnomalyService:
    """Stateless historical-history inference. Caller retains full causal history.

    A registered clock is required. Unknown identities abstain rather than use
    a different asset's detector. detection_time is UTC; observation_time is
    source-local and tagged with its declared/unknown timezone.
    """
    def __init__(self,suites,specs,version=VERSION):
        self.suites=suites;self.specs=specs;self.version=version
    def predict(self,sensor,history,observation_time,detected_at=None):
        now=pd.Timestamp.now(tz='UTC') if detected_at is None else pd.Timestamp(detected_at)
        if now.tzinfo is None: raise ValueError('detection_time must be timezone-aware')
        now=now.tz_convert('UTC')
        observation=pd.Timestamp(observation_time)
        if observation.tzinfo is not None: raise ValueError('observation_time must be source-local naive')
        spec=self.specs.get(sensor)
        base={'component':'infrastructure_measurement_anomaly','version':self.version,'sensor':sensor,
              'supported_sensor':sensor in self.suites,'observation_time':str(observation),
              'detection_time':now.isoformat(),'horizon':'contemporaneous detection',
              'anomaly_score':None,'threshold':None,'alert':None,'detector_type':'IsolationForest + independent quality rules',
              'contributing_indicators':[],'input_freshness':{'status':'unknown','age_hours':None},
              'provenance':spec.provenance if spec else 'unregistered input',
              'input_sources':[spec.source_url] if spec else [],'entity':spec.entity if spec else sensor,
              'geographic_scope':'unmapped benchmark entity','units':spec.unit if spec else 'unknown',
              'observation_timezone':spec.timezone if spec else None,'research_only':True,
              'synthetic':None if spec is None or spec.family=='aqi' else False,'validation_status':'historical benchmark + injected-fixture testing only',
              'confirmed_failure':False,'dispatch_allowed':False,'warnings':['Unusual measurements are not confirmed equipment failures.']}
        if sensor not in self.suites:
            base['warnings'].append('Unknown/untrained sensor: abstained; onboard and validate separately.')
            base['input_freshness']['status']='unassessed'
            return base
        suite=self.suites[sensor]
        f=causal_features(history,spec,end=observation).tail(1)
        if history.attrs.get('synthetic_fixture',False):base['synthetic']=True
        if base['synthetic']:base['warnings'].append('Injected test fixture, not an observed incident.')
        if observation<=suite.train_end_:raise ValueError('Serving observation must be later than model training cutoff')
        if spec.timezone:
            base['warnings'].append('Source timezone/reporting delay is a documented research assumption, not device-verified metadata.')
            instant=observation.tz_localize(spec.timezone).tz_convert('UTC')
            if instant>now:raise ValueError('Observation is in the future relative to detection_time')
            age=(now-instant).total_seconds()/3600
            base['input_freshness']={'status':'stale' if age>spec.freshness_hours else 'fresh','age_hours':float(age)}
            if age>spec.freshness_hours:base['warnings'].append('Stale observation: not current operational evidence.')
        else:
            base['warnings'].append('Unknown source timezone: wall-clock freshness cannot be verified.')
        gap=f.hours_since_valid.iloc[0]
        base['input_freshness']['hours_since_valid_on_source_clock']=None if pd.isna(gap) else float(gap)
        if pd.notna(gap) and gap>spec.freshness_hours:
            base['input_freshness']['status']='stale'
            base['warnings'].append('Last valid reading is stale on the source clock.')
        if pd.isna(gap):
            base['input_freshness']['status']='no_valid_history'
        if not f.ready.iloc[0]:
            base['warnings'].append('Insufficient historical context: abstained.')
            return base
        score=suite.score(f).iloc[0]
        base.update(anomaly_score=float(score.isolation_score),threshold=float(suite.isolation_threshold_),
                    alert=bool(score.review_alert),isolation_alert=bool(score.isolation_alert),
                    quality_alert=bool(score.quality_alert),violated_rules=score.violated_rules.split(',') if score.violated_rules else [],
                    contributing_indicators=suite.diagnose(f),score_semantics='negative IsolationForest score_samples; larger is more unusual, not a probability')
        if score.missing:base['warnings'].append('Current value unavailable; numeric score uses train-fitted imputation and must be read with the quality flag.')
        return base

def evidence_adapter(output):
    """Pure evidence envelope. No graph mutation, score fusion, HTTP, or dispatch.

    No verified municipal asset mapping exists; asset_id deliberately stays null.
    Future backend integration must validate this versioned contract and retain
    independent corroboration/approval checks before any action is considered.
    """
    if output.get('component')!='infrastructure_measurement_anomaly':raise ValueError('Unsupported component')
    safe_output=deepcopy(output)
    safe_output.update(dispatch_allowed=False,confirmed_failure=False,research_only=True)
    return {'contract_version':'civicflux.anomaly-evidence.v1','evidence_type':'unusual_measurement',
            'entity':output['sensor'],'asset_id':None,'requires_verified_asset_mapping':True,
            'measurement_evidence':safe_output,'requires_corroboration':True,
            'confirmed_failure':False,'research_only':True,'automatic_dispatch_allowed':False,
            'approval_status':'not_requested','eligible_for_operational_risk_fusion':False}

def inject_fixture(history,spec,mechanism,seed=42):
    """Isolated deterministic test perturbations on a COPY, never source data.

    Current fixture bounds are specified without reading detector scores.
    Point labels mean injected intervention support, not verified fault labels.
    """
    h=regularize(history,spec)
    if len(h)<240:raise ValueError('At least 240 observations needed for isolated fixtures')
    rng=np.random.default_rng(seed)
    start=int(rng.integers(len(h)//3,len(h)//2+1));duration=24 if spec.cadence=='h' else 7
    end=min(len(h)-1,start+duration)
    loc=np.arange(start,end)
    scale=max(float(h.iloc[:start].value.std()),spec.scale_floor)
    original=h.copy(deep=True)
    if mechanism=='missing': h.loc[loc,'value']=np.nan
    elif mechanism=='spike':
        loc=np.array([start]);h.loc[loc,'value']=h.loc[loc,'value'].fillna(0)+10*scale
    elif mechanism=='persistent_shift':h.loc[loc,'value']=h.loc[loc,'value'].fillna(0)+5*scale
    elif mechanism=='drift':h.loc[loc,'value']=h.loc[loc,'value'].fillna(0)+np.linspace(0,6*scale,len(loc))
    elif mechanism=='flatline':h.loc[loc,'value']=max(spec.scale_floor,float(h.iloc[start-1].value))
    elif mechanism=='seasonal_shift':
        loc=np.arange(start,len(h));h.loc[loc,'value']=np.maximum(0,h.loc[loc,'value'].fillna(0)+3*scale*np.sin(2*np.pi*np.arange(len(loc))/24))
    elif mechanism=='invalid':h.loc[loc,'value']=-1
    elif mechanism=='data_gap':h=h.drop(index=loc)
    else:raise ValueError('Unknown fixture mechanism')
    manifest={'mechanism':mechanism,'seed':seed,'start':str(original.iloc[loc[0]].time),
              'end':str(original.iloc[loc[-1]].time),'injected_points':len(loc),'scale_from_prior_context':scale,
              'synthetic':True,'labels':'injection support, not actual faults'}
    # Regularization restores removed rows so missing-slot recovery is measurable.
    h=regularize(h,spec,end=original.time.max())
    h['injected']=h.time.isin(original.iloc[loc].time)
    h.attrs['synthetic_fixture']=True
    return h,manifest
