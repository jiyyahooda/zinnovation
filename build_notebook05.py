"""Authoritative generator ONLY for notebook 05; never import the legacy builder.

Existing 05 outputs are protected unless --overwrite is explicitly supplied.
"""
from pathlib import Path
import sys,textwrap
import nbformat as nbf
ROOT=Path(__file__).resolve().parent
DEST=ROOT/'notebooks/05_Infrastructure_Anomaly_Research.ipynb'
if DEST.exists() and '--overwrite' not in sys.argv:
    raise SystemExit('Preserving executed 05. Supply --overwrite only for intentional source regeneration.')
cells=[]
def m(s):cells.append(nbf.v4.new_markdown_cell(textwrap.dedent(s).strip()))
def c(s):cells.append(nbf.v4.new_code_cell(textwrap.dedent(s).strip()))
def pair(title,text,source):m('### '+title+'\n\n'+text);c(source)
m('''# CivicFlux — Infrastructure Measurement Anomaly Detection

**Notebook 05 · Version 1.0.0 · Historical benchmark + isolated injected fixtures**

An educational monitoring study, not equipment-failure diagnosis. This extension preserves the executed notebooks 01–04 and reuses the existing source canonicalizer. Models and tests run outside Jupyter through `src/civicflux/anomaly.py`. No municipal sensors, fault labels, coordinates or dispatch actions are invented.
''')
m('''## 01. Research objective and evidence boundaries

Flag an unusual current measurement or reporting condition at a source-qualified entity. The horizon is **contemporaneous detection**, after the current reading becomes available. A large score is not a calibrated fault probability. Environmental extremes, traffic growth, reporting delays and sensor malfunction can all produce unusual values; independent evidence is required to distinguish them.

Research questions: (1) Which temporal features are causally available? (2) How do rules, robust deviations and Isolation Forest differ? (3) Are alert rates stable on later periods? (4) Which controlled disturbances are recovered? (5) Can unknown/stale inputs be handled without inventing an asset failure?

There are **no verified municipal fault labels**. Therefore real-data precision, accuracy, recall and PR-AUC are not computed. Injected-event recovery is a separate software/behavior experiment, never evidence of real failure detection quality.
''')
pair('1.1 Reproducible environment and imports','No installation or network access occurs inside the notebook. Training versions and seeds are saved with artifacts.', '''
from pathlib import Path
from dataclasses import asdict
import sys,json,platform,importlib.metadata,subprocess
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from IPython.display import display
import joblib
ROOT=Path.cwd() if (Path.cwd()/'civicflux_core.py').exists() else Path.cwd().parent
assert (ROOT/'civicflux_core.py').exists()
sys.path.insert(0,str(ROOT))
from civicflux_core import CONFIGS,SOURCES,sha256
from src.civicflux.anomaly import (VERSION,FEATURES,SensorSpec,prepare_source,regularize,
    causal_features,assign_periods,DetectorSuite,AnomalyService,evidence_adapter,inject_fixture)
sns.set_theme(style='whitegrid',palette='colorblind')
plt.rcParams.update({'figure.figsize':(11,4),'figure.dpi':110})
SEED=42
OUT=ROOT/'artifacts'/'infrastructure_anomaly'/('v'+VERSION)
OUT.mkdir(parents=True,exist_ok=True)
print('Python',platform.python_version(),'component version',VERSION)
''')
pair('1.2 Repository audit and scope','The audit records discovered paths and incomplete backend dependencies. Neighboring apps are not silently treated as CivicFlux.', '''
print((ROOT/'reports/notebook05/REPOSITORY_AUDIT.md').read_text())
''')
m('''## 02. Dataset inventory and provenance

Reuse the existing downloaded sources and acquisition instructions in `DATASET_GUIDE.md`. No additional dataset is downloaded. Traffic counts are an observational benchmark with confidential origin; Delhi PM2.5 is publisher-described data with unverified station lineage and unit metadata; rainfall is reported state-level daily rainfall. Source-qualified identities such as `traffic:1`, `aqi:Delhi` and `rainfall:Delhi` must never become a single physical asset just because dates or names resemble each other.

`data/flood_scenarios.csv` contains independently generated scenarios, **not a chronological municipal depth sensor**. The neighboring burn-in and aerospace backends are synthetic/unrelated. Real pressure, flow, water-level and equipment-failure experiments remain blocked by missing sources. Historical file time is not current live telemetry.
''')
pair('2.1 Read full sources and fingerprint','All source columns and record counts are inspected before selecting the existing Delhi environmental scope.', '''
raws={};inventory=[];specs={};histories={};audits={}
for family,cfg in CONFIGS.items():
    path=ROOT/'data'/'raw'/cfg['file']
    raw=pd.read_csv(path);raws[family]=raw
    h,ss,audit=prepare_source(raw,family);specs.update(ss);audits[family]=audit
    for sensor,g in h.groupby('sensor'):histories[sensor]=g.reset_index(drop=True)
    inventory.append({'source':family,'rows':len(raw),'columns':len(raw.columns),'file':cfg['file'],
                      'start':raw[cfg['time']].min(),'end':raw[cfg['time']].max(),'sha256':sha256(path),
                      'units':cfg['unit'],'provenance':cfg['provenance']})
inventory=pd.DataFrame(inventory)
display(inventory)
inventory.to_csv(OUT/'source_inventory.csv',index=False)
''')
pair('2.2 Source schema and geography','The primary traffic benchmark has junction IDs rather than verified sensor serial numbers or municipal coordinates.', '''
for family,raw in raws.items():
    print(family,raw.shape)
    display(pd.DataFrame({'dtype':raw.dtypes.astype(str),'unique':raw.nunique(),'missing':raw.isna().sum()}))
    display(raw.head(3))
spec_table=pd.DataFrame([asdict(s) for s in specs.values()])
display(spec_table[['sensor','unit','timezone','cadence','window','provenance']])
''')
pair('2.3 Observed versus derived/synthetic evidence','Synthetic depth and failure-like labels from unrelated apps are not validated incident labels for these measurements.', '''
provenance_table=pd.DataFrame([
 ['Traffic counts','publisher-described benchmark observations','no verified faults','used independently'],
 ['Delhi PM2.5','processed record; measurement lineage unverified','no verified faults','used independently'],
 ['Delhi daily rainfall','reported state-level aggregate','no equipment labels','used independently'],
 ['Flood scenarios','real rain forcing + synthetic parameters/outcomes','synthetic flood classes','audit only'],
 ['Electronics burn-in','synthetic generator in unrelated SAGE project','synthetic electronics labels','excluded'],
 ['Municipal pressure/flow/depth','unavailable','unavailable','blocked pending genuine data']
],columns=['source','status','labels','decision'])
display(provenance_table)
provenance_table.to_csv(OUT/'provenance_inventory.csv',index=False)
''')
m('''## 03. Inspection, reporting quality and coverage

Preserve exact duplicate policy from the existing project: drop identical rows, reject conflicting entity/time keys. Invalid timestamps stop processing. Non-numeric, infinite or negative measurements become unavailable while an **invalid** indicator is retained; genuine nonnegative extremes remain untouched. Missing values never become invented zero observations.
''')
pair('3.1 Duplicate, null and invalid audits','The anomaly wrapper retains invalidity evidence that the forecasting canonicalizer does not need to return.', '''
display(pd.DataFrame(audits).T)
for family,raw in raws.items():
    cfg=CONFIGS[family]
    print(family,'exact duplicates',raw.duplicated().sum(),'repeated keys',raw.duplicated([cfg['time'],cfg['entity']]).sum())
(OUT/'cleaning_audit.json').write_text(json.dumps(audits,indent=2))
''')
pair('3.2 Entity coverage and late-appearing sensors','A late sensor cannot inherit another sensor’s fitted distribution. Coverage determines which inference is supported.', '''
coverage=pd.DataFrame([{'sensor':k,'rows':len(h),'start':h.time.min(),'end':h.time.max(),
                       'missing':h.value.isna().sum(),'invalid':h.invalid.sum()} for k,h in histories.items()])
display(coverage)
coverage.plot.barh(x='sensor',y='rows',title='Benchmark coverage differs by entity',legend=False);plt.tight_layout();plt.show()
''')
pair('3.3 Missing measurements','Missingness is a monitoring signal in its own right. It does not prove a failed instrument.', '''
coverage.assign(missing_percent=100*coverage.missing/coverage.rows).plot.barh(x='sensor',y='missing_percent',legend=False,title='Unavailable measurement fraction',xlabel='% missing')
plt.tight_layout();plt.show()
''')
pair('3.4 Date spacing and reporting assumptions','Regular grids are required for rate-of-change and run-length features. Timestamp offsets/receipt times are not supplied by these files.', '''
for sensor,h in histories.items():
    print(sensor,'interval counts',h.time.diff().value_counts().head(3).to_dict())
print('No receive_time, sequence_number or measured device health field is available.')
''')
pair('3.5 Numeric summaries and extreme records','Extremes are inspected and retained. Counts, rainfall and pollutant values have different units.', '''
for sensor,h in histories.items():
    print(sensor,specs[sensor].unit)
    display(h.value.describe(percentiles=[.01,.5,.95,.99]).to_frame().T)
    display(h.nlargest(3,'value'))
''')
m('''## 04. Exploratory analysis

Descriptive analytical EDA uses the early development period. Full-data coverage and data-quality audits are structural checks, not evidence for tuning a detector on final outcomes. Each panel retains its entity and unit; no cross-source physical interpretation is implied.
''')
pair('4.1 Causal feature materialization and periods','Features are computed forward in time, separately by entity. Each source has a 60% development / 20% validation / 20% final-period split. All traffic junctions share the source cutoff.', '''
feature_frames=[causal_features(h,specs[sensor]) for sensor,h in histories.items()]
features,boundaries=assign_periods(pd.concat(feature_frames,ignore_index=True))
train=features[features.period.eq('train') & features.ready].copy()
validation=features[features.period.eq('validation') & features.ready].copy()
test=features[features.period.eq('test') & features.ready].copy()
eda=features[features.period.eq('train')].copy()
print(json.dumps(boundaries,indent=2))
display(features.groupby(['sensor','period']).size().unstack(fill_value=0))
(OUT/'temporal_boundaries.json').write_text(json.dumps(boundaries,indent=2))
''')
pair('4.2 Per-entity distributions','Raw and log views reveal asymmetry and heavy tails without deleting events or transforming the source measurements.', '''
sensors=list(histories)
fig,axes=plt.subplots(3,2,figsize=(13,10))
for sensor,ax in zip(sensors,axes.flat):
    sample=eda[eda.sensor.eq(sensor)].value
    if len(sample):sns.histplot(sample,bins=45,ax=ax)
    else:ax.text(.2,.5,'No development observations',transform=ax.transAxes)
    ax.set_title(sensor);ax.set_xlabel(specs[sensor].unit)
plt.tight_layout();plt.show()
''')
pair('4.3 Monthly time patterns','A change in traffic demand or pollution season can increase alert rate without any equipment fault.', '''
fig,axes=plt.subplots(3,1,figsize=(12,10))
for family,ax in zip(['traffic','aqi','rainfall'],axes):
    subset=eda[eda.sensor.str.startswith(family+':')]
    for sensor,g in subset.groupby('sensor'):
        g.set_index('time').value.resample('MS').mean().plot(ax=ax,label=sensor)
    ax.set_title(family+' development monthly means');ax.legend()
plt.tight_layout();plt.show()
''')
pair('4.4 Seasonal structure','Known calendar patterns motivate causal seasonal residuals, rather than treating every daily peak as abnormal.', '''
fig,axes=plt.subplots(1,3,figsize=(15,4))
for family,ax in zip(['traffic','aqi','rainfall'],axes):
    subset=eda[eda.sensor.str.startswith(family+':')].copy()
    subset['slot']=subset.time.dt.month if family=='rainfall' else subset.time.dt.hour
    sns.boxplot(data=subset,x='slot',y='value',showfliers=False,ax=ax)
    ax.set_title(family+': month' if family=='rainfall' else family+': hour');ax.tick_params(axis='x',rotation=90)
plt.tight_layout();plt.show()
''')
pair('4.5 Junction differences','Separate models prevent a busy junction’s baseline from being imposed on another junction.', '''
traffic_eda=eda[eda.sensor.str.startswith('traffic:')]
sns.boxplot(data=traffic_eda,x='sensor',y='value',showfliers=False)
plt.title('Development vehicle-count differences');plt.ylabel('Vehicles/hour');plt.show()
''')
pair('4.6 Rolling references around real extremes','The shaded reference uses earlier readings only. An extreme rainfall day can be a genuine event rather than a sensor error.', '''
fig,axes=plt.subplots(3,1,figsize=(12,10))
for sensor,ax in zip(['traffic:1','aqi:Delhi','rainfall:Delhi'],axes):
    g=eda[eda.sensor.eq(sensor)].reset_index(drop=True)
    peak=int(g.value.fillna(-1).argmax());z=g.iloc[max(0,peak-40):peak+40]
    ax.plot(z.time,z.value,label='Observed');ax.plot(z.time,z.rolling_median,label='Prior-window median')
    ax.fill_between(z.time,z.rolling_min,z.rolling_max,alpha=.2,label='Prior min/max')
    ax.set_title(sensor+' extreme context');ax.legend()
plt.tight_layout();plt.show()
''')
pair('4.7 Correlation and redundancy','Rolling mean, median and min/max are correlated. Their isolation diagnostics must not be interpreted as independent causal effects.', '''
correlation=train[train.sensor.eq('traffic:1')][FEATURES].corr()
sns.heatmap(correlation,cmap='coolwarm',center=0,vmin=-1,vmax=1)
plt.title('Traffic 1 feature correlations; constant columns undefined');plt.tight_layout();plt.show()
''')
pair('4.8 Repeated values and reporting anomalies','Repeated integer traffic counts are natural at low flows; sustained identical values are only candidates for investigation. Dry rainfall spells are not flagged as failed sensors.', '''
run_table=eda.groupby('sensor').agg(max_equal_run=('flat_run','max'),missing_fraction=('missing','mean'),invalid_fraction=('invalid','mean'))
display(run_table)
run_table.max_equal_run.plot.barh(title='Longest identical-reading run in development');plt.tight_layout();plt.show()
''')
m('''## 05. Preprocessing and leakage controls

Raw history is ordered and regularized at the declared cadence. Conflicting duplicates and off-grid observations are rejected. Missing intervals remain explicit. Invalidity is retained alongside missingness. Median imputation is fitted on each sensor’s historical development features only; it is not a claim that missing readings are physically normal. Tree-based Isolation Forest does not require feature standardization, and models are not pooled across units or entities.

The temporal question differs from forecasting: the current value is available when detecting a current anomaly. Its reference window must nevertheless exclude the current value. Model training ends before any validation/test score. Calibration scores do not establish fault probability.
''')
pair('5.1 Future perturbation invariant','Changing future measurements cannot change earlier features, including seasonal baselines and previous unusual counts.', '''
sensor='traffic:1';original=histories[sensor];changed=original.copy()
cut=len(original)//2;changed.loc[cut:,'value']=999999
fa=causal_features(original,specs[sensor]);fb=causal_features(changed,specs[sensor])
pd.testing.assert_frame_equal(fa.iloc[:cut],fb.iloc[:cut])
print('PASS: future observations do not alter past features')
''')
pair('5.2 Missing/invalid demonstration on a copy','This is an isolated fixture, not evidence that the original file contained a bad reading.', '''
copy=histories['traffic:1'].head(120).copy()
copy.loc[100,'value']=-1;copy.loc[101,'value']=np.nan
copy=copy.drop(index=102)
check=causal_features(copy,specs['traffic:1'])
display(check.loc[98:104,['time','value','invalid','missing','rolling_median','rate_change']])
assert check.loc[100,'invalid']==1 and check.loc[102,'missing']==1
''')
pair('5.3 Current observation excluded from baseline','A spike should change its deviation, not retrospectively change its own reference median or previous-event count.', '''
h=histories['traffic:1'].head(400).copy();modified=h.copy();modified.loc[300,'value']=100000
before=causal_features(h,specs['traffic:1']);after=causal_features(modified,specs['traffic:1'])
for column in ['rolling_mean','rolling_median','rolling_mad','seasonal_expected','previous_unusual_count']:
    assert before.loc[300,column]==after.loc[300,column]
print('PASS: current reading excluded from reference statistics')
''')
m('''## 06. Feature engineering and interpretation

For hourly series the rolling reference is the previous 24 readings; rainfall uses 30 days. These windows are declared assumptions. The robust scale is `max(1.4826 × prior MAD, unit-scale floor)` so a constant/zero series cannot cause division by zero. Floors are 1 vehicle/source PM2.5 unit and 0.1 mm. They are numerical research choices, not instrument accuracy claims.

Seasonal expectation is an **expanding, shifted same-slot mean**: month for daily rainfall, weekday×hour for hourly series. Sparse slots fall back to the prior global mean. This adapts using past observations and can gradually absorb a persistent shift. No full-sample seasonal profile is used to score earlier rows.
''')
pair('6.1 Feature schema','Previous unusual-event count means prior robust-threshold crossings, not known incidents or confirmed faults.', '''
feature_schema=pd.DataFrame([
 ['value','Current cleaned reading','source units'],
 ['rolling_mean / std / median / MAD / min / max','Strictly preceding reference window','source units'],
 ['robust_z','(current − prior median) / floored scaled MAD','dimensionless'],
 ['rate_change','Current minus preceding cadence reading','source units per cadence'],
 ['seasonal_residual','Current minus past-only same-slot baseline','source units'],
 ['baseline_deviation','Deviation from past-only expanding mean/std','dimensionless'],
 ['missing / invalid','Current reporting quality','binary'],
 ['missing_fraction','Missing share in preceding reference window','fraction'],
 ['flat_run','Consecutive identical observed values, including current','readings'],
 ['previous_unusual_count','Prior abs(robust_z)>6 crossings in window','count, not incidents'],
 ['hours_since_valid','Time since most recent finite nonnegative reading','hours'],
 ['hour_sin / cos','Known time-of-day phase','dimensionless']
],columns=['feature_family','definition','unit'])
display(feature_schema)
feature_schema.to_csv(OUT/'feature_definitions.csv',index=False)
(OUT/'feature_schema.json').write_text(json.dumps({'ordered_features':FEATURES,'dtypes':{k:str(features[k].dtype) for k in FEATURES}},indent=2))
''')
pair('6.2 Visualize current versus reference features','Feature excursions can indicate legitimate changes; the interpretation remains conditional on provenance.', '''
g=train[train.sensor.eq('traffic:1')].head(240)
fig,ax=plt.subplots(3,1,figsize=(12,9),sharex=True)
ax[0].plot(g.time,g.value,label='Current');ax[0].plot(g.time,g.rolling_mean,label='Prior mean');ax[0].legend()
ax[1].plot(g.time,g.robust_z,label='Robust z');ax[1].axhline(6,color='red',ls='--');ax[1].axhline(-6,color='red',ls='--');ax[1].legend()
ax[2].plot(g.time,g.seasonal_residual,label='Causal seasonal residual');ax[2].legend()
plt.tight_layout();plt.show()
''')
pair('6.3 Inspect causal availability','No target, known-fault label, municipality identifier or synthetic depth enters these models.', '''
display(train[['sensor','time']+FEATURES].head(8))
assert not {'target','depth_m','failure','fault_label','event_id'}.intersection(FEATURES)
print('All',len(FEATURES),'features are numeric; no cross-entity encoding is fitted.')
''')
m('''## 07. Historical development and baseline detectors

**Rules:** current missing/invalid reading, sufficiently long identical run, value above the training 99.5th percentile, or absolute cadence change above its training 99.5th percentile. Flatline thresholds are 12 hourly readings / 5 daily readings; zero-rainfall runs are exempt. These are inspectable research rules, not physical upper safety limits.

**Robust detector:** abs(robust z)>6 against a strictly prior median/MAD. Missing z is not treated as measured normality; quality alerts are separate.

**Isolation Forest:** randomized partition trees isolate sparse feature combinations in shorter paths. We report `−score_samples`, so larger means more unusual; alert iff score is **strictly greater** than `−offset_`. Contamination=0.02 sets a training-score cutoff; it is **not a measured failure prevalence**. Training may already contain unusual events.

The component uses Isolation Forest plus independent quality rules for a review signal. Raw rules, robust and isolation results stay separately available. No precision-based model winner can be selected without labels. We prespecify 100 trees, 256 subsamples and 2% contamination; sensitivity experiments investigate this choice without test-based retuning. See [scikit-learn outlier detection](https://scikit-learn.org/stable/modules/outlier_detection.html) and [Isolation Forest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html); the installed version is recorded in artifacts.
''')
pair('7.1 Fit only supported development histories','Junction 4 has no development-period rows under the shared traffic cutoff. It is withheld as a naturally unseen identity.', '''
suites={};fit_rows=[]
for sensor,g in train.groupby('sensor'):
    if len(g)<100:continue
    model=DetectorSuite(specs[sensor],n_estimators=100,max_samples=256,contamination=.02,seed=SEED).fit(g)
    suites[sensor]=model
    fit_rows.append({'sensor':sensor,'fit_rows':model.fit_rows_,'train_last':str(model.train_end_),
                     'rule_upper':model.upper_,'jump_threshold':model.jump_,'isolation_threshold':model.isolation_threshold_})
fit_table=pd.DataFrame(fit_rows)
display(fit_table)
print('Untrained identities:',sorted(set(specs)-set(suites)))
fit_table.to_csv(OUT/'fitted_thresholds.csv',index=False)
''')
pair('7.2 Score validation without learning from it','Only the train-fitted imputer and detector are used. Validation scores describe behavior; they are not fault labels.', '''
def score_period(frame):
    parts=[]
    for sensor,model in suites.items():
        subset=frame[frame.sensor.eq(sensor)]
        if len(subset):parts.append(model.score(subset))
    return pd.concat(parts,ignore_index=True)
val_scores=score_period(validation)
display(val_scores.head())
alert_columns=['rule_alert','robust_alert','isolation_alert','quality_alert','review_alert']
validation_rates=val_scores.groupby('sensor')[alert_columns].mean()
display(validation_rates)
validation_rates.to_csv(OUT/'validation_alert_rates.csv')
''')
pair('7.3 Validation alert comparison','Higher alert rate is neither better recall nor more confirmed failures.', '''
validation_rates[['rule_alert','robust_alert','isolation_alert']].plot.bar(title='Later validation alert rates (unlabeled)',ylabel='Fraction of observations',rot=20)
plt.tight_layout();plt.show()
''')
pair('7.4 Score distributions and threshold semantics','Each detector uses a different scale. Scores must not be averaged into a single risk probability.', '''
fig,ax=plt.subplots(1,3,figsize=(15,4))
z=val_scores[val_scores.sensor.eq('traffic:1')]
for column,a in zip(['rule_score','robust_score','isolation_score'],ax):
    sns.histplot(z[column].dropna(),bins=50,ax=a);a.set_title(column)
ax[0].axvline(1,color='red');ax[1].axvline(6,color='red');ax[2].axvline(suites['traffic:1'].isolation_threshold_,color='red')
plt.tight_layout();plt.show()
''')
m('''## 08. Temporal validation and hyperparameter sensitivity

No labels are manufactured for historical observations. Expanding-origin validation reports alert rate, score quantiles and seed agreement instead of supervised accuracy. Hyperparameters are investigated transparently, and the predeclared final configuration remains unchanged. The final period and final injected fixtures are still reserved.
''')
pair('8.1 Expanding-origin validation','This uses only the original development segment. Each fold refits imputation and detector on its own earlier subset.', '''
from sklearn.model_selection import TimeSeriesSplit
cv=[]
z=train[train.sensor.eq('traffic:1')].reset_index(drop=True)
for fold,(tr,va) in enumerate(TimeSeriesSplit(n_splits=3).split(z)):
    model=DetectorSuite(specs['traffic:1'],n_estimators=100,max_samples=256,contamination=.02,seed=SEED).fit(z.iloc[tr])
    scored=model.score(z.iloc[va])
    cv.append({'fold':fold,'training_rows':len(tr),'validation_rows':len(va),'last_train':str(z.iloc[tr].time.max()),
               'first_validation':str(z.iloc[va].time.min()),'alert_rate':scored.isolation_alert.mean(),
               'score_p50':scored.isolation_score.median(),'score_p95':scored.isolation_score.quantile(.95)})
cv=pd.DataFrame(cv);display(cv);cv.to_csv(OUT/'temporal_cv_diagnostics.csv',index=False)
cv.plot.bar(x='fold',y='alert_rate',legend=False,title='Expanding-fold alert rates; not error rates');plt.axhline(.02,color='red',ls='--');plt.show()
''')
pair('8.2 Contamination assumptions','Changing contamination changes the score threshold, not evidence that anomalies are real faults. Hold tree settings and seed constant for a controlled comparison.', '''
contamination_rows=[]
for sensor in suites:
    tr=train[train.sensor.eq(sensor)];va=validation[validation.sensor.eq(sensor)]
    for contamination in [.005,.01,.02,.05,.10]:
        model=DetectorSuite(specs[sensor],100,256,contamination,SEED).fit(tr)
        out=model.score(va)
        contamination_rows.append({'sensor':sensor,'assumed_contamination':contamination,'threshold':model.isolation_threshold_,
                                   'validation_alert_rate':out.isolation_alert.mean()})
contamination_results=pd.DataFrame(contamination_rows)
display(contamination_results)
sns.lineplot(data=contamination_results,x='assumed_contamination',y='validation_alert_rate',hue='sensor',marker='o')
plt.title('Threshold sensitivity on validation');plt.show()
contamination_results.to_csv(OUT/'contamination_sensitivity.csv',index=False)
''')
pair('8.3 Tree count, subsampling and seed stability','Rank agreement and alert-set Jaccard quantify reproducibility, not diagnostic correctness. We do not optimize these using final-period data.', '''
from scipy.stats import spearmanr
sensitivity=[];tr=train[train.sensor.eq('traffic:1')];va=validation[validation.sensor.eq('traffic:1')]
reference=suites['traffic:1'].score(va)
for trees,samples in [(64,128),(100,256),(160,512)]:
    for seed in [42,73]:
        candidate=DetectorSuite(specs['traffic:1'],trees,samples,.02,seed).fit(tr)
        scored=candidate.score(va)
        a=scored.isolation_alert.to_numpy();b=reference.isolation_alert.to_numpy()
        sensitivity.append({'trees':trees,'subsamples':samples,'seed':seed,'alert_rate':a.mean(),
                            'rank_correlation':spearmanr(scored.isolation_score,reference.isolation_score).statistic,
                            'alert_jaccard':np.sum(a&b)/max(1,np.sum(a|b))})
sensitivity=pd.DataFrame(sensitivity);display(sensitivity)
sensitivity.to_csv(OUT/'hyperparameter_stability.csv',index=False)
sns.scatterplot(data=sensitivity,x='rank_correlation',y='alert_jaccard',hue='trees',style='seed',s=100)
plt.title('Sensitivity relative to declared reference configuration');plt.show()
''')
pair('8.4 Sensitivity to seasonal features','An ablation drops seasonal residual and calendar phase while keeping raw data and training period fixed. Alert disagreement does not establish which detector is correct.', '''
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import IsolationForest
nonseasonal=[f for f in FEATURES if f not in ['seasonal_residual','hour_sin','hour_cos']]
ablation=Pipeline([('impute',SimpleImputer(strategy='median',keep_empty_features=True)),('model',IsolationForest(n_estimators=100,max_samples=256,contamination=.02,random_state=SEED,n_jobs=2))])
ablation.fit(tr[nonseasonal])
no_season_alert=ablation.predict(va[nonseasonal])==-1
ablation_summary=pd.DataFrame({'hour':va.time.dt.hour,'with_seasonality':reference.isolation_alert.to_numpy(),'without_seasonal_features':no_season_alert}).groupby('hour').mean()
ablation_summary.plot(title='Validation hourly alert rate: feature ablation',ylabel='Alert fraction');plt.show()
print('Disagreement fraction:',np.mean(no_season_alert!=reference.isolation_alert.to_numpy()))
ablation_summary.to_csv(OUT/'seasonality_ablation.csv')
''')
pair('8.5 Locked configuration record','Final-period findings cannot change these parameters. Quality rules and contamination are assumptions that future validated deployments must revisit.', '''
locked={'component_version':VERSION,'n_estimators':100,'max_samples':256,'contamination':.02,'seed':SEED,
        'robust_threshold':6,'strict_threshold_comparison':'>','rule_quantile':.995,
        'selection':'predeclared research reference, no supervised winner','supported_sensors':sorted(suites),
        'unknown_sensor_policy':'abstain','training_excludes_injected_fixtures':True}
(OUT/'detector_config.json').write_text(json.dumps(locked,indent=2))
print(json.dumps(locked,indent=2))
''')
m('''## 09. Final historical monitoring evaluation

This is a held-out **behavioral evaluation**, not labeled failure detection. Report alert volume, score distribution shift, seasonality and agreement. Unflagged observations are not certified healthy. Higher alert rates can reflect real traffic growth or environmental seasonality rather than false alarms.
''')
pair('9.1 Final alert rates and unsupported coverage','Unknown identities are counted explicitly rather than disappearing from the denominator or receiving fabricated predictions.', '''
test_scores=score_period(test)
final_rates=test_scores.groupby('sensor')[alert_columns].mean()
display(final_rates)
unsupported=test.loc[~test.sensor.isin(suites)].groupby('sensor').size()
print('Unscored final-period rows by identity:',unsupported.to_dict())
print('Scored final-period rows:',len(test_scores))
final_rates.to_csv(OUT/'test_alert_rates.csv')
test_scores.to_csv(OUT/'test_scores.csv',index=False)
''')
pair('9.2 Compare validation and final periods','The 2% training cutoff does not guarantee 2% future alerts under distribution shift.', '''
comparison=validation_rates[['isolation_alert']].rename(columns={'isolation_alert':'validation'}).join(final_rates[['isolation_alert']].rename(columns={'isolation_alert':'test'}))
display(comparison)
comparison.plot.bar(title='Isolation alert-rate drift',ylabel='Fraction alerted',rot=20);plt.axhline(.02,color='red',ls='--');plt.tight_layout();plt.show()
''')
pair('9.3 Alert stability across months','Independent source timelines are displayed in separate panels.', '''
fig,axes=plt.subplots(3,1,figsize=(12,10))
monthly=[]
for family,ax in zip(['traffic','aqi','rainfall'],axes):
    for sensor,g in test_scores[test_scores.sensor.str.startswith(family+':')].groupby('sensor'):
        q=g.set_index('time').isolation_alert.resample('MS').mean()
        q.plot(ax=ax,label=sensor);monthly.extend({'sensor':sensor,'month':str(t),'alert_rate':v} for t,v in q.items())
    ax.set_title(family+' final-period monthly alert fraction');ax.legend()
plt.tight_layout();plt.show()
pd.DataFrame(monthly).to_csv(OUT/'monthly_alert_rates.csv',index=False)
''')
pair('9.4 Score distribution drift','These are descriptive empirical quantiles, not calibrated probabilities or exchangeable confidence intervals.', '''
score_rows=[]
for sensor,model in suites.items():
    for split,values in [('train',model.train_scores_),('validation',val_scores[val_scores.sensor.eq(sensor)].isolation_score),('test',test_scores[test_scores.sensor.eq(sensor)].isolation_score)]:
        for q in [.01,.1,.5,.9,.95,.99]:score_rows.append({'sensor':sensor,'period':split,'quantile':q,'score':float(np.quantile(values,q))})
score_distribution=pd.DataFrame(score_rows)
display(score_distribution.head(18))
score_distribution.to_csv(OUT/'score_distributions.csv',index=False)
sns.lineplot(data=score_distribution[score_distribution.sensor.eq('traffic:1')],x='quantile',y='score',hue='period',marker='o')
plt.title('Traffic 1 isolation score distribution shift');plt.show()
''')
pair('9.5 Agreement among detectors','Agreement is not corroboration from an independent physical source: all three methods use the same underlying measurements.', '''
agreement=[]
for sensor,g in test_scores.groupby('sensor'):
    for a,b in [('rule_alert','robust_alert'),('rule_alert','isolation_alert'),('robust_alert','isolation_alert')]:
        aa=g[a].to_numpy();bb=g[b].to_numpy()
        agreement.append({'sensor':sensor,'pair':a+' / '+b,'jaccard':np.sum(aa&bb)/max(1,np.sum(aa|bb)),'disagreement':np.mean(aa!=bb)})
agreement=pd.DataFrame(agreement);display(agreement)
sns.heatmap(agreement.pivot(index='sensor',columns='pair',values='jaccard'),annot=True,vmin=0,vmax=1,cmap='Blues');plt.title('Alert-set Jaccard');plt.tight_layout();plt.show()
agreement.to_csv(OUT/'detector_agreement.csv',index=False)
''')
pair('9.6 Seasonal alert sensitivity on later data','Rainfall spikes may be legitimate monsoon observations. Detection does not distinguish environmental events from reporting faults.', '''
fig,ax=plt.subplots(1,2,figsize=(13,4))
hourly=test_scores[test_scores.sensor.eq('traffic:1')].copy();hourly['hour']=hourly.time.dt.hour
hourly.groupby('hour')[['rule_alert','robust_alert','isolation_alert']].mean().plot(ax=ax[0],title='Traffic 1 by hour')
rain=test_scores[test_scores.sensor.eq('rainfall:Delhi')].copy();rain['month']=rain.time.dt.month
rain.groupby('month')[['rule_alert','robust_alert','isolation_alert']].mean().plot(ax=ax[1],title='Delhi rainfall by month')
plt.tight_layout();plt.show()
''')
m('''## 10. Isolated injected-anomaly robustness experiments

Eight documented perturbations are applied to **copies**: missing readings, one-point spike (+10 prior-context SD), persistent shift (+5 SD), gradual drift (0→6 SD), positive flatline, altered seasonal amplitude (3 SD sinusoid), negative invalid values and deleted intervals. The original source is never changed. Mechanisms and onset positions are selected without detector scores.

Each test fixture uses a bounded trailing context (1,200 hourly or 500 daily observations) wholly in the final period, with two onset seeds. Models stay frozen. Baselines are recomputed causally on the paired clean and perturbed context; this intentionally tests bounded-context behavior, not equality to the full-history service. Daily sinusoidal perturbations have a 24-day period, hourly ones 24 hours. Persistent-shift adaptation may suppress later detection.

Recovery = fraction of injected points alerted. Event detection = any alert within the injection interval. Delay is cadence steps to first alert. Unmodified-background alert fraction is **not a false-positive rate**, because untouched historical records have no known health labels. The seasonal-shift fixture is a distribution-change stress test, not a simulated equipment fault. No performance on these designed fixtures is promoted to real-world accuracy.
''')
pair('10.1 Injection manifest and paired evaluation','Evaluate three independent streams, eight mechanisms and two onset seeds. Report all mechanisms including poor recovery.', '''
mechanisms=['missing','spike','persistent_shift','drift','flatline','seasonal_shift','invalid','data_gap']
fixture_results=[];manifests=[];case_fixtures={}
for sensor in ['traffic:1','aqi:Delhi','rainfall:Delhi']:
    spec=specs[sensor];model=suites[sensor]
    final_history=histories[sensor][histories[sensor].time>=pd.Timestamp(boundaries[spec.family]['test_start'])]
    context=final_history.tail(500 if spec.cadence=='D' else 1200).reset_index(drop=True)
    clean_f=causal_features(context,spec)
    clean_s=model.score(clean_f)
    for mechanism in mechanisms:
        for seed in [42,73]:
            injected,manifest=inject_fixture(context,spec,mechanism,seed)
            f=causal_features(injected,spec);scores=model.score(f)
            mask=injected.injected.to_numpy();eligible=f.ready.to_numpy()
            assert eligible[mask].all()
            manifest.update(sensor=sensor,context_rows=len(context),context_start=str(context.time.min()))
            manifests.append(manifest)
            for method in ['rule','robust','isolation','review']:
                alert=scores[method+'_alert'].to_numpy()
                baseline=clean_s[method+'_alert'].to_numpy()
                positions=np.flatnonzero(mask&alert)
                first=np.flatnonzero(mask)[0]
                fixture_results.append({'sensor':sensor,'mechanism':mechanism,'seed':seed,'detector':method,
                    'injected_points':int(mask.sum()),'recovery':float(alert[mask].mean()),
                    'matched_clean_alert_rate':float(baseline[mask].mean()),
                    'new_alert_fraction':float((alert[mask]&~baseline[mask]).mean()),
                    'background_alert_fraction':float(alert[eligible&~mask].mean()),
                    'event_detected':bool(len(positions)),
                    'delay_steps':float(positions[0]-first) if len(positions) else np.nan})
            if sensor=='traffic:1' and seed==42:case_fixtures[mechanism]=(injected,scores,manifest)
fixture_results=pd.DataFrame(fixture_results)
fixture_results.to_csv(OUT/'injected_recovery.csv',index=False)
(OUT/'injection_manifests.json').write_text(json.dumps(manifests,indent=2))
display(fixture_results.head(12))
print('Independent fixture copies',len(manifests),'method evaluations',len(fixture_results))
''')
pair('10.2 Which detector responds to which mechanism?','Quality checks can recover missing/invalid points that Isolation Forest, trained on mostly complete data, may miss. Inspect the combined review signal separately.', '''
recovery=fixture_results.groupby(['mechanism','detector']).recovery.mean().unstack()
display(recovery)
sns.heatmap(recovery,annot=True,fmt='.2f',vmin=0,vmax=1,cmap='Blues');plt.title('Injected-point recovery; averaged across 3 streams × 2 onsets');plt.tight_layout();plt.show()
''')
pair('10.3 Stream-specific recovery','An identical mechanism can behave differently under daily zero-inflated rain and hourly traffic or pollutant distributions.', '''
by_stream=fixture_results[fixture_results.detector.eq('review')].groupby(['sensor','mechanism']).recovery.mean().unstack()
sns.heatmap(by_stream,annot=True,fmt='.2f',vmin=0,vmax=1,cmap='viridis');plt.title('Combined review recovery by benchmark stream');plt.tight_layout();plt.show()
''')
pair('10.4 Event detection, delays and background burden','A detector that alerts continuously would recover every injection but provide poor review value. Paired clean alerts and background burden reveal this weakness without pretending they are fault precision.', '''
fixture_summary=fixture_results.groupby(['mechanism','detector']).agg(recovery=('recovery','mean'),event_detection=('event_detected','mean'),median_delay=('delay_steps','median'),matched_clean_alert=('matched_clean_alert_rate','mean'),new_alert_fraction=('new_alert_fraction','mean'),background_alert=('background_alert_fraction','mean'))
display(fixture_summary)
fixture_summary.to_csv(OUT/'injected_summary.csv')
''')
pair('10.5 Visual stress cases','Shading marks injected points only. Red markers are the quality-or-isolation review signal.', '''
fig,axes=plt.subplots(4,2,figsize=(15,14))
for mechanism,ax in zip(mechanisms,axes.flat):
    h,s,manifest=case_fixtures[mechanism];loc=np.flatnonzero(h.injected)
    a=max(0,loc[0]-48);b=min(len(h),loc[-1]+49)
    z=h.iloc[a:b];q=s.iloc[a:b]
    ax.plot(z.time,z.value,label='Perturbed measurement')
    ax.axvspan(h.iloc[loc[0]].time,h.iloc[loc[-1]].time,alpha=.2,color='orange')
    mask=q.review_alert.to_numpy();ax.scatter(z.time[mask],z.value[mask],c='red',s=12)
    ax.set_title(mechanism);ax.tick_params(axis='x',rotation=20)
plt.tight_layout();plt.show()
''')
pair('10.6 Unknown identity and cold-start handling','Anomaly evidence cannot be transferred from a known junction into an unseen identity. Natural late-appearing Junction 4 supplies this test.', '''
service=AnomalyService(suites,specs)
unknown='traffic:4'
unknown_payload=service.predict(unknown,histories[unknown],histories[unknown].time.max())
print(json.dumps(unknown_payload,indent=2))
assert unknown_payload['alert'] is None and unknown_payload['supported_sensor'] is False
''')
m('''## 11. Explainability and case studies

Rule outputs identify the violated checks. For Isolation Forest we show train-relative features and controlled score sensitivity: replace one feature by its training median, holding others fixed, and observe the score change. This is a diagnostic of model behavior, not causal attribution, a probability contribution, or a proof of sensor failure. Correlated rolling features can make these counterfactual combinations unrealistic.
''')
pair('11.1 Inspect high-scoring real records','These are unusual historical measurements with unknown fault status. Keep the original units and source identity.', '''
cases=test_scores.sort_values('isolation_score',ascending=False).groupby('sensor',sort=False).head(2)
display(cases[['sensor','time','value','isolation_score','isolation_alert','quality_alert','violated_rules']])
cases.to_csv(OUT/'historical_case_studies.csv',index=False)
''')
pair('11.2 Expose violated rules','Missingness, invalidity, sudden change and training-quantile exceedance are transparent observations, not municipal fault codes.', '''
rule_cases=test_scores[test_scores.rule_alert].groupby('sensor').head(3)
display(rule_cases[['sensor','time','value','violated_rules']])
rule_counts=test_scores.violated_rules.str.split(',').explode().value_counts()
rule_counts=rule_counts[rule_counts.index!='']
rule_counts.plot.barh(title='Final-period rule-trigger counts');plt.tight_layout();plt.show()
''')
pair('11.3 Model-score sensitivity for one traffic case','A positive score drop means replacing that feature by its train median reduced anomaly score; it does not identify the physical cause.', '''
case=test_scores[test_scores.sensor.eq('traffic:1')].nlargest(1,'isolation_score').iloc[0]
row=test[test.sensor.eq(case.sensor)&test.time.eq(case.time)]
diagnostic=pd.DataFrame(suites[case.sensor].diagnose(row,top=10))
display(row[['sensor','time']+FEATURES]);display(diagnostic)
diagnostic.plot.barh(x='feature',y='score_drop_on_median_replacement',legend=False,title='Controlled feature replacement diagnostic');plt.tight_layout();plt.show()
diagnostic.to_csv(OUT/'case_feature_diagnostics.csv',index=False)
''')
pair('11.4 Train-relative case context','Display the historical case against the preceding week. Nearby values can be useful corroborating context, but they are not independent device-health measurements.', '''
h=histories[case.sensor];context=h[(h.time>=case.time-pd.Timedelta(days=7))&(h.time<=case.time)]
plt.plot(context.time,context.value);plt.scatter([case.time],[case.value],c='red',s=70)
plt.title('Real benchmark case: traffic excursion, fault status unknown');plt.ylabel(specs[case.sensor].unit);plt.show()
''')
pair('11.5 Inspect a missed injected event','Poor recovery is retained and explained as a limitation. Imputation, adaptive baselines and a sparse training distribution can all limit detection.', '''
weak=fixture_results.sort_values(['recovery','new_alert_fraction']).head(12)
display(weak[['sensor','mechanism','seed','detector','recovery','event_detected','delay_steps','matched_clean_alert_rate']])
print('These are designed test interventions. Their missed recovery does not estimate missed real municipal failures.')
''')
m('''## 12. Reusable inference, versioned export and tests

Inference accepts one source-qualified sensor, its causal history, an expected observation timestamp and an aware detection timestamp. Input time remains on the documented source wall clock. For Asia/Kolkata assumptions, UTC age is computed explicitly; traffic’s unknown timezone produces freshness=unknown. Missing tail slots are materialized, and last-valid-reading age is reported. Unknown/untrained identities and insufficient history abstain. Scoring at/before training cutoff is rejected.

The service requires full preceding history to reproduce expanding-baseline values; bounded context is a separately documented approximation used only in the fixture experiments. No online model refitting occurs. Fitted preprocessing and detectors are saved only after successful training and diagnostics. Copy `src/` and `civicflux_core.py` with the joblib; load only trusted artifacts.
''')
pair('12.1 Versioned configuration and model card','The model card records source hashes, fit cutoffs, numerical feature floors, unverified provenance and blocked real-fault evaluation.', '''
model_card={'component':'infrastructure_measurement_anomaly','version':VERSION,'research_only':True,
 'objective':'flag unusual measurements; never confirm asset failure','source_inventory':inventory.to_dict('records'),
 'supported_sensors':sorted(suites),'untrained_sensors':sorted(set(specs)-set(suites)),
 'sensor_specs':{k:asdict(v) for k,v in specs.items()},'fit_summary':fit_rows,'config':locked,
 'labels':'No verified equipment-fault labels; injection support labels only',
 'real_data_metrics':'alert rates, score distributions, temporal stability; no fault precision or accuracy',
 'fixture_metrics':'point recovery, event detection, delay and matched clean alert burden',
 'limitations':['No real water-level, pressure, flow or fault observations','No verified municipal asset mapping',
                'AQI unit/measurement provenance unverified','Traffic timezone unknown','Adaptive baselines can absorb persistent shifts',
                '2% contamination is an assumption, not fault prevalence','State rainfall is not a local drainage sensor'],
 'integration_status':'pure evidence adapter; CivicFlux backend schema unavailable','dispatch_allowed':False,
 'versions':{name:importlib.metadata.version(name) for name in ['numpy','pandas','scikit-learn','joblib']}}
(OUT/'model_card.json').write_text(json.dumps(model_card,indent=2,default=str))
joblib.dump(service,OUT/'detectors.joblib')
print('Saved actually fitted suites:',len(suites),'to',OUT)
''')
pair('12.2 Serialize/reload and inspect full output contract','Use a fixed detection instant for reproducibility. Because the file ends in the past, the input is correctly marked stale.', '''
loaded=joblib.load(OUT/'detectors.joblib')
sensor='aqi:Delhi';h=histories[sensor];detected_at=pd.Timestamp('2026-10-25T00:00:00Z')
output=loaded.predict(sensor,h,h.time.max(),detected_at)
assert output==service.predict(sensor,h,h.time.max(),detected_at)
json.dumps(output,allow_nan=False)
print(json.dumps(output,indent=2))
(OUT/'inference_example.json').write_text(json.dumps(output,indent=2))
assert output['input_freshness']['status']=='stale' and output['confirmed_failure'] is False
''')
pair('12.3 Quality and invalid-input contract example','The adapter must carry the quality warning even if the Isolation Forest score itself is below threshold.', '''
copy=histories['traffic:1'].copy();copy.loc[copy.index[-1],'value']=np.nan
copy.attrs['synthetic_fixture']=True
quality_output=loaded.predict('traffic:1',copy,copy.time.max(),detected_at)
print(json.dumps({k:quality_output[k] for k in ['sensor','anomaly_score','isolation_alert','quality_alert','alert','input_freshness','synthetic','warnings']},indent=2))
assert quality_output['quality_alert'] and quality_output['alert']
''')
pair('12.4 Automated integrity and serving tests','Run both the legacy test suite and the new tests: missing/invalid/stale/constant/unknown inputs, reproducibility, reload, causality, rule thresholds and dispatch suppression.', '''
result=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-v'],cwd=ROOT,text=True,capture_output=True)
print(result.stdout+result.stderr)
(OUT/'tests.txt').write_text(result.stdout+result.stderr)
assert result.returncode==0,'Automated integrity test failure'
''')
pair('12.5 Preserve notebooks 01–04 and their artifacts','The initial checksums were captured before any changes. This confirms the extension did not regenerate or overwrite legacy outputs.', '''
preserved=json.loads((ROOT/'reports/notebook05/preserved_before.json').read_text())
changed=[name for name,digest in preserved.items() if not (ROOT/name).exists() or sha256(ROOT/name)!=digest]
assert not changed,changed
print('PASS:',len(preserved),'existing notebook/artifact files unchanged byte-for-byte')
(OUT/'preservation_check.json').write_text(json.dumps({'checked_files':len(preserved),'changed':changed},indent=2))
''')
m('''## 13. CivicFlux evidence integration and findings

The inspected CivicFlux workspace contains research bundles/payloads but no actual infrastructure-risk API, graph/optimizer or municipal asset registry. Therefore the integration is a **thin pure-function evidence adapter**, not a fabricated live backend connection. No unrelated FastAPI schema is modified. A future backend must establish verified asset mapping and preserve its own corroboration/approval rules.

The evidence envelope contains the version, source-qualified entity, input sources, observation/detection times, units, anomaly score/threshold, contributing indicators, freshness, provenance and research status. `asset_id=null`, `requires_corroboration=true`, `confirmed_failure=false`, `eligible_for_operational_risk_fusion=false`, and `automatic_dispatch_allowed=false`. The adapter has no dispatch capability or side effect.
''')
pair('13.1 Thin evidence adapter','A downstream graph may store this as research evidence awaiting corroboration; it must not equate it with a guaranteed equipment-failure node.', '''
evidence=evidence_adapter(output)
print(json.dumps(evidence,indent=2))
assert not evidence['automatic_dispatch_allowed'] and not evidence['confirmed_failure']
assert evidence['asset_id'] is None and evidence['requires_corroboration']
(OUT/'civicflux_evidence_example.json').write_text(json.dumps(evidence,indent=2))
''')
pair('13.2 Actual measured findings','Generate conclusions from executed measurements; no predetermined success score is inserted.', '''
print('Fitted sensor/entity suites:',len(suites))
print('Held-out scored rows:',len(test_scores),'Unsupported rows:',int(unsupported.sum()))
print('Isolation Forest later alert rates (%):')
print((100*final_rates.isolation_alert).round(2).to_string())
print('Injected point recovery, combined review (%):')
print((100*fixture_results[fixture_results.detector.eq('review')].groupby('mechanism').recovery.mean()).round(2).to_string())
findings={'fitted_suites':len(suites),'scored_test_rows':len(test_scores),'unsupported_test_rows':int(unsupported.sum()),
          'test_alert_rates':final_rates.to_dict('index'),
          'fixture_recovery':recovery.to_dict('index'),'fixture_copies':len(manifests),
          'real_fault_precision':None,'real_fault_accuracy':None,'dispatch_allowed':False}
(OUT/'findings.json').write_text(json.dumps(findings,indent=2))
''')
m('''### 13.3 Limitations, interpretation and next dependencies

Anomaly evidence is useful for review prioritization, but the present experiment cannot diagnose municipal equipment failure. The reported alert rates are not false-positive rates. Injected recovery depends on the designed amplitude, duration, context and onset seeds; two onsets and three streams are not a validated municipal incident population. Adaptive rolling/seasonal baselines can absorb drift and sustained shifts. A missing-value indicator may be unseen in development, so independent data-quality checks remain necessary. Rainfall zero spells are expected; city-level pollution does not localize a specific sensor fault.

Before live integration: supply the actual CivicFlux backend schemas and asset registry; provide verified sensor-to-asset mapping, measurement units, timestamp/receive-time semantics and telemetry freshness requirements; collect observed water/pressure/flow readings and adjudicated incidents; validate thresholds and costs using future/site holdouts; distinguish sensor faults from legitimate environmental events with independent corroboration. None of those absent datasets or interfaces is silently substituted here. Existing approval and resource-allocation workflows remain untouched.
''')
nb=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python (CivicFlux)','language':'python','name':'civicflux'},'language_info':{'name':'python','version':'3.13'}})
nbf.write(nb,DEST)
print(DEST.name,len(cells),'cells;',sum(x.cell_type=='code' for x in cells),'code cells')
