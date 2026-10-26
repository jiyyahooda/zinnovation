"""Generate the legacy 01–04 notebooks; training runs separately.

Notebook generation sources are intentionally scoped: build_notebook05.py for
05, build_notebook06.py for 06, build_notebook07.py for 07, and
build_notebooks_08_09.py for 08–09, and build_notebooks_10_11.py for 10–11.
Run apply_targeted_review.py after intentional source regeneration of 06–09. These builders share src/civicflux modules
and preserve executed notebooks unless an explicit overwrite flag is provided.
"""
from pathlib import Path
import sys
# Explicit scoped entry points avoid rebuilding the legacy notebooks.
if '--review-06-09' in sys.argv or '--reports-10-11' in sys.argv:
    import runpy
    script='apply_targeted_review.py' if '--review-06-09' in sys.argv else 'build_notebooks_10_11.py'
    runpy.run_path(str(Path(__file__).resolve().parent/script),run_name='__main__')
    raise SystemExit(0)
# Legacy source generator is authoritative for 01–04, but regenerating them
# must be explicit because it erases their executed outputs.
if any((Path(__file__).resolve().parent / 'notebooks').glob('0[1-4]_*.ipynb')) and '--overwrite-legacy' not in sys.argv:
    raise SystemExit('Preserving executed notebooks 01–04. Use --overwrite-legacy only for intentional regeneration; use the per-notebook builders for 05–11.')
import nbformat as nbf
import textwrap
ROOT=Path(__file__).resolve().parent

def md(s): return nbf.v4.new_markdown_cell(textwrap.dedent(s).strip())
def code(s): return nbf.v4.new_code_cell(textwrap.dedent(s).strip())
class Notebook:
 def __init__(self,title): self.cells=[md(title)]
 def m(self,s): self.cells.append(md(s))
 def c(self,s): self.cells.append(code(s))
 def pair(self,title,explanation,source):
  self.m('### '+title+'\n\n'+explanation);self.c(source)
 def save(self,name):
  n=nbf.v4.new_notebook(cells=self.cells,metadata={'kernelspec':{'display_name':'Python (CivicFlux)','language':'python','name':'civicflux'},'language_info':{'name':'python','version':'3.13'}})
  nbf.write(n,ROOT/'notebooks'/name)

SETUP='''
from pathlib import Path
import sys, json, platform, importlib.metadata, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from IPython.display import display
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.model_selection import cross_validate, RandomizedSearchCV
from sklearn.inspection import permutation_importance
import joblib
ROOT = Path.cwd() if (Path.cwd() / 'civicflux_core.py').exists() else Path.cwd().parent
assert (ROOT / 'civicflux_core.py').exists(), 'Run from civicflux_ml or its notebooks directory'
sys.path.insert(0, str(ROOT))
from civicflux_core import *
sns.set_theme(style='whitegrid', palette='colorblind')
plt.rcParams.update({'figure.figsize': (11, 4), 'figure.dpi': 110})
SEED = 42
N_SPLITS = 3  # Expanding time folds; increase to five for a longer study.
N_SEARCH = 6  # Real searches are run; increase to 20+ for a larger compute budget.
'''
DOMAINS={
'rainfall':dict(title='Daily Rainfall Forecasting',file='01_Rainfall_Research.ipynb',target='next-day state-average rainfall',units='mm/day',scope='Delhi state/territory aggregate',context='Rainfall is zero-inflated and heavy-tailed. MAE summarizes typical error, RMSE exposes missed extremes, and wet-day/upper-tail slices prevent dry days from hiding failure.',exclude='`id` is an identifier; `rfs`, `normal` and `deviation` have incomplete definitions or reference-period availability. They are excluded rather than treated as known future weather.',source='daily-rainfall-at-state-level.csv',provenance='Reported real historical state-level rainfall, republished on Kaggle. The upstream observation and aggregation process is not independently audited. This is not a rain gauge at a particular drain.',special='rainfall'),
'aqi':dict(title='Hourly PM2.5 Forecasting',file='02_AQI_Research.ipynb',target='next-hour PM2.5 concentration',units='µg/m³, provisional unit assumption',scope='Delhi city series; other cities remain visible in source inspection',context='This model predicts PM2.5, not an AQI category and not CO₂ emissions. The CSV contains city labels and representative coordinates, not monitoring-station identifiers. Publication describes measurements but does not establish station-level lineage.',exclude='Exclude contemporaneously derived `aqi`, `aqi_category` and supplied calendar fields; regenerate calendar features from parsed timestamps. Other pollutants could be added only after their units and reporting delays are established.',source='processed_aqi_data.csv',provenance='Publisher-described air-quality measurements; real versus generated/processed status is not independently verifiable. Keep this uncertainty in every exported prediction. Working assumption: PM2.5 is µg/m³; no unsupported unit conversion is applied.',special='aqi'),
'traffic':dict(title='Hourly Junction Traffic Forecasting',file='03_Traffic_Research.ipynb',target='next-hour vehicle count at each junction',units='vehicles/hour',scope='All four anonymous benchmark junctions',context='Vehicle counts measure flow, not road speed or travel time. The benchmark does not supply a verified city, coordinates, lane capacity, incident reports, or a time zone. Network routing therefore requires additional measured edge data.',exclude='`ID` encodes date/junction and is excluded. Junction is a categorical identity, not an ordinal numeric quantity. No speed, capacity or geographic join is inferred from count.',source='traffic.csv',provenance='Observational traffic benchmark as described by its publisher; anonymous junction geography and original sensor lineage remain unverified.',special='traffic')}

for kind,d in DOMAINS.items():
 n=Notebook(f"# CivicFlux — {d['title']}\n\n**Research notebook · 13 sections · seed 42**\n\nInspired by the supplied 110-cell RTA notebook: inspect → visualize → clean → engineer → compare → tune → evaluate → explain → export. All outputs below are generated from the downloaded data. Read the limitations with the metrics; these are historical research models.")
 n.m(f"## 01. Problem definition\n\nPredict **{d['target']}**, in **{d['units']}**, for **{d['scope']}**. The origin is immediately after the current observation becomes available; horizon is one regular interval. Publication delays are unknown, so deployment must shift the origin if reports arrive late.\n\n{d['context']}\n\nThe holdout experiment is rolling one-step forecasting: earlier holdout observations may supply later lags after they become available. This is not a fixed-origin multi-step forecast.")
 n.pair('1.1 Reproducibility and research budget','Imports and fixed seeds are explicit. No warning suppression, hidden package installation, or silent synthetic fallback is used.',SETUP+f"\nKIND = {kind!r}\ncfg = CONFIGS[KIND].copy()\nOUT = ROOT / 'artifacts' / KIND\nOUT.mkdir(parents=True, exist_ok=True)\nprint('Python', platform.python_version())")
 n.m(f"## 02. Dataset introduction\n\nSource: [Kaggle dataset](https://www.kaggle.com/datasets/{__import__('sys').path and {'rainfall':'wydoinn/daily-rainfall-data-india-2009-2024','aqi':'aniket0712/delhi-ncr-hourly-air-quality-dataset-20192024','traffic':'fedesoriano/traffic-prediction-dataset'}[kind]}). Read `DATASET_GUIDE.md` for API URLs, exact commands, licenses, schemas and quality limitations.\n\n**Provenance:** {d['provenance']}\n\n**File:** `{d['source']}`. The notebook inspects the complete downloaded file before selecting its modeling geography. Default scope is editable in `cfg['selected']`; changing it requires rerunning every cell. No unrelated sources are merged.")
 n.pair('2.1 Load immutable source and fingerprint','The checksum identifies the exact bytes used. Downloaded CSVs are never overwritten.', '''
source_path = ROOT / 'data' / 'raw' / cfg['file']
if not source_path.exists():
    raise FileNotFoundError('Run download_data.py or follow DATASET_GUIDE.md first')
raw = pd.read_csv(source_path)
fingerprint = sha256(source_path)
print('Source:', source_path.name, '\\nSHA256:', fingerprint)
print('Actual rows and columns:', raw.shape)
''')
 n.pair('2.2 Source coverage and unit contract','Coverage is measured from the file, rather than inferred from the dataset title.', '''
display(pd.DataFrame({'rows': raw.groupby(cfg['entity']).size()}))
print('Timestamp range:', raw[cfg['time']].min(), 'to', raw[cfg['time']].max())
print('Target units:', cfg['unit'])
print('Timezone:', cfg['tz'] or 'unknown local civil time; do not convert to UTC')
print('Provenance:', cfg['provenance'])
''')
 n.m('## 03. Data inspection\n\nInspect structure, missingness, duplicate keys, numeric ranges and coverage before deciding how to model. Inspection is descriptive; model choices and thresholds must not use the final test outcomes.')
 n.pair('3.1 First and last observations','Look for ordering, identifiers and unexpected formatting.', 'display(raw.head(8))\ndisplay(raw.tail(5))')
 n.pair('3.2 Data types and cardinality','String dates are parsed later with a declared format.', "display(pd.DataFrame({'dtype': raw.dtypes.astype(str), 'unique':raw.nunique(), 'missing':raw.isna().sum()}))")
 n.pair('3.3 Missingness table and plot','A blank measurement is not a zero concentration, zero traffic, or a dry day.', '''
missing = pd.DataFrame({'count':raw.isna().sum(), 'percent':100*raw.isna().mean()})
display(missing.sort_values('percent', ascending=False))
missing['percent'].sort_values().plot.barh(title='Source missingness by column', xlabel='Missing (%)')
plt.tight_layout(); plt.show()
''')
 n.pair('3.4 Duplicate audit','Exact rows can be removed once. Conflicting entity/timestamp keys cause a stop; averaging them would silently change the measurement definition.', '''
print('Exact duplicate rows:', raw.duplicated().sum())
keys=[cfg['entity'],cfg['time']]
print('Repeated keys:', raw.duplicated(keys).sum())
display(raw.loc[raw.duplicated(keys,keep=False)].head(12))
''')
 n.pair('3.5 Descriptive statistics and suspicious extremes','We inspect, not winsorize, genuine environmental peaks.', "display(raw.describe(include='all').T)\ndisplay(raw.nlargest(10,cfg['value'])[[cfg['time'],cfg['entity'],cfg['value']]])")
 n.pair('3.6 Timeline continuity','Per-entity interval differences reveal gaps and non-hourly/non-daily observations.', '''
raw_times=pd.to_datetime(raw[cfg['time']], format=cfg['date_format'], errors='coerce')
spacing=pd.DataFrame({'entity':raw[cfg['entity']], 't':raw_times}).sort_values(['entity','t'])
display(spacing.groupby('entity').t.diff().value_counts().head(10).rename('interval_count'))
''')
 n.m('## 04. Exploratory analysis\n\nTo avoid designing features around the test set, analytical EDA below uses the earliest 60% of source timestamps. Full-source structural inspection above is retained for auditing. Extreme values stay visible on both ordinary and log scales.')
 n.c('''
cut = np.sort(raw_times.dropna().unique())[int(.6*raw_times.nunique())]
eda = raw.loc[raw_times < cut].copy()
eda['parsed_time'] = raw_times.loc[eda.index]
eda['month_eda'] = eda.parsed_time.dt.month
eda['weekday_eda'] = eda.parsed_time.dt.dayofweek
eda['hour_eda'] = eda.parsed_time.dt.hour
print('EDA only before',cut, '; rows',len(eda))
''')
 n.pair('4.1 Target distribution','Compare raw concentration/count/rainfall with log1p to make long tails visible without transforming the label.', '''
fig,ax=plt.subplots(1,2,figsize=(12,4))
sns.histplot(eda[cfg['value']],bins=60,ax=ax[0]); ax[0].set_title('Observed distribution')
sns.histplot(np.log1p(eda[cfg['value']].clip(lower=0)),bins=60,ax=ax[1]); ax[1].set_title('log(1 + value), diagnostic only')
plt.tight_layout(); plt.show()
''')
 n.pair('4.2 Long-term changes','Monthly means are for descriptive visualization only; they never enter model features.', '''
trend=eda.set_index('parsed_time').groupby(cfg['entity'])[cfg['value']].resample('MS').mean().unstack(0)
trend.plot(title='Monthly mean by source geography',ylabel=cfg['unit'],legend=False)
plt.tight_layout(); plt.show()
''')
 n.pair('4.3 Seasonal distributions','Seasonality can motivate calendar features without using future outcomes.', '''
sns.boxplot(data=eda, x='month_eda', y=cfg['value'], showfliers=False)
plt.title('Month-of-year distribution (points hidden here, not removed)')
plt.ylabel(cfg['unit']); plt.show()
''')
 n.pair('4.4 Weekly and diurnal patterns','Calendar comparisons are descriptive, not evidence of causation.', '''
fig,ax=plt.subplots(1,2,figsize=(12,4))
eda.groupby('weekday_eda')[cfg['value']].mean().plot.bar(ax=ax[0],title='Day-of-week mean')
eda.groupby('hour_eda')[cfg['value']].mean().plot.bar(ax=ax[1],title='Hour-of-day mean; daily data has one hour')
plt.tight_layout(); plt.show()
''')
 n.pair('4.5 Geography and coverage','State means, city series and anonymous junctions represent different spatial resolutions.', '''
coverage=eda.groupby(cfg['entity'])[cfg['value']].agg(['count','mean','median','max'])
display(coverage)
coverage['mean'].sort_values().plot.barh(title='Development-period mean by source geography',figsize=(10,7))
plt.tight_layout(); plt.show()
''')
 n.pair('4.6 Numeric associations','Identifiers and precomputed calendar fields can produce spurious correlations; this heatmap is not automatic feature selection.', '''
cols=eda.select_dtypes('number').columns
sns.heatmap(eda[cols].corr(),cmap='coolwarm',center=0,vmin=-1,vmax=1)
plt.title('Raw numeric correlation — interpretation required'); plt.tight_layout(); plt.show()
''')
 n.m(f"## 05. Preprocessing\n\n{d['exclude']}\n\nPolicy: keep the first identical full row; reject conflicting entity-time records; parse timestamps exactly; retain nonnegative extremes; convert physically impossible negative target values to missing; insert absent grid intervals as missing. Labels are never imputed. Predictor medians and category encoding are learned only inside each training fold. There is no backward filling or interpolation.\n\nFor Indian rainfall/AQI we explicitly assume naive timestamps refer to Asia/Kolkata; this needs upstream confirmation. Traffic remains timezone-naive because its zone is undocumented. Daily rainfall is assumed available after the labeled day's total is reported; aggregation window and reporting latency require verification before live deployment.")
 n.pair('5.1 Canonicalize and regularize','The shared implementation is also used by the exported raw-history prediction bundle.', '''
history,audit=canonicalize(raw,cfg)
display(pd.Series(audit,name='audit'))
display(history.head())
(OUT/'cleaning_audit.json').write_text(json.dumps(audit,indent=2))
''')
 n.pair('5.2 Missingness after regularization','Missing labels remain missing. Median imputation later handles predictors without accessing future values.', '''
print('Unavailable observed values:',history.value.isna().sum())
history.set_index('time').source_missing.resample('MS').mean().plot(title='Fraction missing per month after grid insertion',ylabel='Missing fraction')
plt.show()
''')
 n.pair('5.3 Outlier report without deletion','A train-period 99th percentile is diagnostic only. Heavy rainfall and pollution spikes may be the most important observations.', '''
train_observed=history.loc[history.time < history.time.quantile(.6),'value']
extreme_cut=train_observed.quantile(.99)
print('Development 99th percentile:',extreme_cut)
print('Extremes retained:',history.value.gt(extreme_cut).sum())
assert history.value.dropna().ge(0).all()
''')
 n.m('### 5.4 Geographic and temporal alignment\n\nNo cross-dataset join is performed. Exact entity ID and exact regular interval are required (spatial tolerance **zero across identities**, temporal tolerance **zero for target joins**). Delhi state rainfall is not localized catchment rain; city AQI coordinates are not station footprints; anonymous traffic junctions cannot be matched to Delhi. A future station-to-asset join must have verified coordinates, matching administrative codes and declared measurement footprints; provisional point matching could use ≤1 km and backward-only ≤1 hour, but these are unvalidated project assumptions, not applied here. State polygons cannot pass that point-radius rule.')
 n.m('## 06. Feature engineering\n\nAll lags are group-specific and measured on the complete regular grid. At origin t, the current observed value and windows ending at t are available. The label is the observation exactly one interval later. Calendar values describe that future interval and are known in advance.')
 n.pair('6.1 Build auditable temporal features','Lag 1 means one complete earlier interval, not merely the previous available record.', '''
frame=make_features(history,cfg)
# Start after the longest history window; never fill unavailable future labels.
first=history.groupby('entity').time.min()
warmup=pd.to_timedelta(max(cfg['lags']),unit='D' if cfg['freq']=='D' else 'h')
ready=frame.time >= frame.entity.map(first)+warmup
frame=frame.loc[ready & frame.target.notna()].reset_index(drop=True)
features=[c for c in frame if c not in ['time','target_time','target']]
assert not {'target','target_time','depth_m','aqi_category','ID','deviation'} & set(features)
display(frame.head()); print('Features:',features)
''')
 n.pair('6.2 Feature dictionary','Each family has an explicit availability contract.', '''
feature_dictionary=pd.DataFrame([
 ('current','Observation at t; available after reporting'),
 ('lag_k','Observed target k intervals before t'),
 ('mean_w / std_w','Trailing statistics through t; no future values'),
 ('coverage_w / source_missing','Availability quality at origin, not future quality'),
 ('calendar and cyclic','Known calendar of t+1'),
 ('positive_fraction','Trailing fraction positive, not an incident count'),
 ('entity','Exact state/city/junction identity')],columns=['family','definition'])
display(feature_dictionary)
feature_dictionary.to_csv(OUT/'feature_dictionary.csv',index=False)
''')
 n.pair('6.3 Visualize the lag relationship','Use development rows only and sample deterministically for plotting.', '''
preview=frame[frame.time<frame.time.quantile(.6)].head(5000)
fig,ax=plt.subplots(1,2,figsize=(12,4))
sns.scatterplot(data=preview,x='current',y='target',alpha=.2,s=8,ax=ax[0])
sns.scatterplot(data=preview,x=f'mean_{cfg["windows"][0]}',y='target',alpha=.2,s=8,ax=ax[1])
plt.tight_layout(); plt.show()
''')
 n.pair('6.4 Visualize trailing features','Smoothing changes the noise level; it must not change the information cutoff.', '''
one=preview[preview.entity.eq(preview.entity.iloc[0])].head(200).set_index('time')
one[['current',f'mean_{cfg["windows"][0]}',f'mean_{cfg["windows"][-1]}']].plot(title='Current observation and causal rolling means')
plt.show()
''')
 n.pair('6.5 Incident-history availability','These datasets do not contain verified incidents or report timestamps. Missing incident history is explicitly unavailable and excluded; zeros would invent evidence.', '''
incident_counts=historical_incidents(frame[['entity','time']],None)
assert incident_counts.isna().all()
print('Historical incident count: unavailable; not included in model features')
''')
 n.pair('6.6 Executable future-perturbation check','Changing a future observation must not change earlier predictor rows.', '''
probe_time=history.time.sort_values().iloc[len(history)//2]
changed=history.copy()
changed.loc[changed.time>probe_time,'value']=999999
original_features=make_features(history,cfg,with_target=False)
changed_features=make_features(changed,cfg,with_target=False)
pd.testing.assert_frame_equal(original_features.loc[original_features.time<=probe_time],changed_features.loc[changed_features.time<=probe_time])
print('PASS: future measurements cannot change earlier features')
''')
 n.m('## 07. Training strategy\n\nUse 60% of unique timestamps for development, 20% for calibration and 20% for untouched final evaluation. Purge any training label that reaches a validation origin. Three expanding folds keep every location at a timestamp together. Select models by development CV MAE; never by final test scores. No SMOTE is appropriate for continuous forecasts. Rainfall imbalance is addressed through dry/wet and extreme slices, not fabricated targets.')
 n.pair('7.1 Split once and document boundaries','The calibration period estimates uncertainty only; it is not used for candidate selection.', '''
dev,cal,test=partition(frame)
Xdev,ydev=dev[features],dev.target
Xcal,ycal=cal[features],cal.target
Xtest,ytest=test[features],test.target
folds=temporal_folds(dev,N_SPLITS)
split_table=pd.DataFrame([{'split':name,'rows':len(z),'origin_start':z.time.min(),'origin_end':z.time.max(),'last_label':z.target_time.max()} for name,z in [('development',dev),('calibration',cal),('test',test)]])
display(split_table)
split_table.to_csv(OUT/'split_boundaries.csv',index=False)
assert dev.target_time.max()<cal.time.min()
assert cal.target_time.max()<test.time.min()
''')
 n.pair('7.2 Plot temporal cross-validation','The gaps are horizon purges, not randomly held-out rows.', '''
fig,ax=plt.subplots(figsize=(11,3))
for i,(tr,va) in enumerate(folds):
    ax.plot([dev.iloc[tr].time.min(),dev.iloc[tr].time.max()],[i,i],lw=8,color='steelblue')
    ax.plot([dev.iloc[va].time.min(),dev.iloc[va].time.max()],[i,i],lw=8,color='orange')
ax.set(title='Expanding CV: blue train, orange validation',ylabel='Fold'); plt.show()
''')
 n.pair('7.3 Train-fold preprocessing','Numeric medians and missing indicators are fitted per fold. Categorical encoding ignores unseen entities. Only Ridge is scaled; trees are not.', '''
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
numeric=[c for c in features if c!='entity']
def make_pipeline(model,scale=False):
    steps=[('impute',SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True))]
    if scale: steps.append(('scale',StandardScaler()))
    prep=ColumnTransformer([('num',Pipeline(steps),numeric),('cat',OneHotEncoder(handle_unknown='ignore',sparse_output=False),['entity'])])
    return Pipeline([('preprocess',prep),('model',model)])
models={
 'Persistence':BaselineRegressor('persistence'),
 'Seasonal mean':BaselineRegressor('seasonal'),
 'Ridge':make_pipeline(Ridge(alpha=10),scale=True),
 'Random Forest':make_pipeline(RandomForestRegressor(n_estimators=80,min_samples_leaf=5,max_depth=14,n_jobs=2,random_state=SEED)),
 'XGBoost':make_pipeline(XGBRegressor(n_estimators=120,max_depth=3,learning_rate=.05,subsample=.85,colsample_bytree=.9,objective='reg:squarederror',tree_method='hist',n_jobs=2,random_state=SEED))}
print('Candidates:',list(models))
''')
 n.m('## 08. Model experiments\n\nThe same folds and observations are used for every baseline and learned model. Persistence can be difficult to beat over one hour. Seasonal means are learned from training data only. The budget is deliberately finite and reported; this is a reproducible comparison, not a claim of globally optimal tuning.')
 n.pair('8.1 Cross-validated model comparison','MAE is primary; RMSE and variability across time folds provide complementary evidence.', '''
cv_rows=[]
for name,model in models.items():
    scores=cross_validate(model,Xdev,ydev,cv=folds,scoring={'mae':'neg_mean_absolute_error','rmse':'neg_root_mean_squared_error'},n_jobs=1,error_score='raise')
    for fold,(mae,rmse,seconds) in enumerate(zip(-scores['test_mae'],-scores['test_rmse'],scores['fit_time'])):
        cv_rows.append(dict(model=name,fold=fold,MAE=mae,RMSE=rmse,fit_seconds=seconds))
cv_details=pd.DataFrame(cv_rows)
cv_summary=cv_details.groupby('model').agg(MAE=('MAE','mean'),MAE_std=('MAE','std'),RMSE=('RMSE','mean'),fit_seconds=('fit_seconds','sum')).sort_values('MAE')
display(cv_summary)
cv_details.to_csv(OUT/'candidate_cv.csv',index=False)
''')
 n.pair('8.2 Compare error and stability','Large spread can indicate time-period sensitivity even when the average score is good.', '''
cv_summary.MAE.plot.barh(xerr=cv_summary.MAE_std,title='Development CV MAE ± fold standard deviation',xlabel=cfg['unit'])
plt.tight_layout(); plt.show()
sns.lineplot(data=cv_details,x='fold',y='MAE',hue='model',marker='o'); plt.title('Performance across later periods'); plt.show()
''')
 n.m('## 09. Hyperparameter tuning\n\nTune the two best learned candidates from development CV. Baselines remain eligible to win overall. RandomizedSearchCV refits preprocessing within every fold. Tuning CV scores are optimistic selection estimates; only section 10 provides a final generalization estimate.')
 n.pair('9.1 Declare search spaces','Search sizes are visible and seeds fixed. No test-period early stopping is used.', '''
spaces={
 'Ridge':{'model__alpha':[.1,1,10,100,1000,10000]},
 'Random Forest':{'model__n_estimators':[80,140],'model__max_depth':[8,14,None],'model__min_samples_leaf':[3,8,15],'model__max_features':[.7,1.]},
 'XGBoost':{'model__n_estimators':[80,140,220],'model__max_depth':[2,3,5],'model__learning_rate':[.03,.08,.15],'model__min_child_weight':[1,5,10],'model__subsample':[.7,1.],'model__reg_lambda':[1,5,15]}}
top=[name for name in cv_summary.index if name in spaces][:2]
print('Tune:',top,';',N_SEARCH,'settings each;',N_SPLITS,'folds')
''')
 n.pair('9.2 Run searches and save every trial','Model selection does not consult calibration or final test labels.', '''
searches={}
selection={name:float(-cv_summary.loc[name,'MAE']) for name in models}
for name in top:
    search=RandomizedSearchCV(models[name],spaces[name],n_iter=N_SEARCH,cv=folds,scoring='neg_mean_absolute_error',refit=True,random_state=SEED,n_jobs=1,error_score='raise',return_train_score=True)
    search.fit(Xdev,ydev)
    searches[name]=search
    selection[name+' tuned']=search.best_score_
    pd.DataFrame(search.cv_results_).to_csv(OUT/(name.replace(' ','_')+'_search.csv'),index=False)
    print(name,search.best_params_,'CV MAE',-search.best_score_)
selected_name=max(selection,key=selection.get)
final_model=searches[selected_name.removesuffix(' tuned')].best_estimator_ if selected_name.endswith(' tuned') else clone(models[selected_name]).fit(Xdev,ydev)
print('Locked winner:',selected_name)
''')
 n.pair('9.3 Tuning results and overfitting gap','Show the winning search trials, including train/validation divergence.', '''
for name,s in searches.items():
    trials=pd.DataFrame(s.cv_results_).sort_values('rank_test_score')
    display(trials[['rank_test_score','mean_test_score','std_test_score','mean_train_score','params']].head(6))
    plt.plot(-trials.mean_train_score.to_numpy(),label='train MAE')
    plt.plot(-trials.mean_test_score.to_numpy(),label='validation MAE')
    plt.title(name+' search trials ordered by rank');plt.legend();plt.show()
''')
 n.pair('9.4 Calibrate prediction intervals','Use the untouched calibration segment for a 90% absolute-residual interval. Time dependence means exchangeability is not guaranteed; report achieved coverage instead of promising nominal coverage.', '''
cal_pred=np.maximum(0,final_model.predict(Xcal))
residual_abs=np.abs(ycal.to_numpy()-cal_pred)
q_level=min(1,np.ceil((len(residual_abs)+1)*.9)/len(residual_abs))
radius=float(np.quantile(residual_abs,q_level,method='higher'))
print('90% residual interval radius:',radius,cfg['unit'])
''')
 n.m('## 10. Final evaluation\n\nThe winner and uncertainty radius are now fixed. Evaluate the final test block once. Compare frozen persistence and seasonal baselines to contextualize performance, but do not change the selected model after seeing this section.')
 n.pair('10.1 Test metrics and baseline skill','Predictions are clipped to the physical lower bound zero at serving and evaluation. CV uses raw predictions, so tiny differences may occur for linear candidates.', '''
pred=np.maximum(0,final_model.predict(Xtest))
metrics=regression_metrics(ytest,pred)
comparison=[]
for name in ['Persistence','Seasonal mean']:
    baseline=clone(models[name]).fit(Xdev,ydev)
    comparison.append({'model':name,**regression_metrics(ytest,baseline.predict(Xtest))})
comparison.append({'model':selected_name,**metrics})
results=pd.DataFrame(comparison)
display(results)
metrics['MAE_skill_vs_persistence']=1-metrics['MAE']/max(results.iloc[0].MAE,1e-12)
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2))
''')
 n.pair('10.2 Forecast trace and intervals','Each point is a forecast from its preceding origin, not a forecast made once at the start of the entire test period.', '''
errors=test[['time','target_time','entity','target']].copy()
errors['prediction']=pred
errors['error']=pred-ytest.to_numpy()
errors['abs_error']=np.abs(errors.error)
errors['lower']=np.maximum(0,pred-radius);errors['upper']=pred+radius
errors.to_csv(OUT/'test_predictions.csv',index=False)
trace=errors[errors.entity.eq(errors.entity.iloc[0])].head(200)
plt.plot(trace.target_time,trace.target,label='Observed')
plt.plot(trace.target_time,trace.prediction,label='One-step forecast')
plt.fill_between(trace.target_time,trace.lower,trace.upper,alpha=.2,label='Calibrated 90% interval')
plt.legend();plt.ylabel(cfg['unit']);plt.title('Untouched test forecast trace');plt.show()
''')
 n.pair('10.3 Residual diagnostics','Look for systematic bias, scale-dependent errors and serial dependence.', '''
fig,ax=plt.subplots(1,3,figsize=(15,4))
sns.histplot(errors.error,bins=50,ax=ax[0]);ax[0].set_title('Residual distribution')
sns.scatterplot(data=errors.iloc[::max(1,len(errors)//1500)],x='prediction',y='error',s=8,ax=ax[1]);ax[1].axhline(0,color='black')
entity_errors=errors[errors.entity.eq(errors.entity.iloc[0])].set_index('time').error.asfreq(cfg['freq'])
pd.Series({lag:entity_errors.autocorr(lag) for lag in range(1,25)}).plot.bar(ax=ax[2],title='Residual autocorrelation')
plt.tight_layout();plt.show()
''')
 n.pair('10.4 Calibration and interval width','A wide interval can obtain coverage without being useful. Inspect both coverage and width.', '''
covered=(errors.target>=errors.lower)&(errors.target<=errors.upper)
print('Observed coverage:',covered.mean(),'Mean width:',(errors.upper-errors.lower).mean())
errors['covered']=covered
calibration=errors.assign(month=errors.target_time.dt.month).groupby('month').agg(coverage=('covered','mean'),MAE=('abs_error','mean'),n=('target','size'))
display(calibration)
calibration.coverage.plot.bar(title='Interval coverage by test month');plt.axhline(.9,color='red',ls='--');plt.show()
''')
 n.pair('10.5 Error slices and worst cases','Upper-tail cutoff comes from development targets. These are audits, not post-test optimization.', '''
cutoff=float(ydev.quantile(.9))
errors['slice']=np.where(errors.target>cutoff,'above development p90',np.where(errors.target==0,'zero','other'))
display(errors.groupby('slice').agg(n=('target','size'),MAE=('abs_error','mean'),bias=('error','mean')))
display(errors.groupby('entity').agg(n=('target','size'),MAE=('abs_error','mean')))
display(errors.nlargest(12,'abs_error'))
''')
 if kind=='rainfall':
  n.pair('10.6 Wet-day diagnostic','A 1 mm/day wet-day cutoff is a project diagnostic, not an official warning category. A separate occurrence/amount model is a future extension if dry-day dominance is problematic.', '''
from sklearn.metrics import ConfusionMatrixDisplay, classification_report
print(classification_report(ytest>=1,pred>=1,zero_division=0))
ConfusionMatrixDisplay.from_predictions(ytest>=1,pred>=1,display_labels=['<1 mm','≥1 mm']);plt.title('Wet-day diagnostic from regression');plt.show()
''')
 n.m('## 11. Explainability\n\nPermutation importance evaluates the locked model. Correlated lags can share importance; these associations are not causal. SHAP is shown for the selected tree or linear model on a small, documented sample. If the winning model is a baseline, the SHAP plot is explicitly an auxiliary tree explanation, never attributed to the winner.')
 n.pair('11.1 Permutation importance','Use a deterministic calibration sample, not final test outcomes for feature selection.', '''
explain_X=Xcal.sample(min(200,len(Xcal)),random_state=SEED)
explain_y=ycal.loc[explain_X.index]
pi=permutation_importance(final_model,explain_X,explain_y,scoring='neg_mean_absolute_error',n_repeats=3,random_state=SEED,n_jobs=1)
importance=pd.Series(pi.importances_mean,index=features).sort_values()
importance.tail(15).plot.barh(title='Locked winner: permutation increase in MAE');plt.tight_layout();plt.show()
importance.to_csv(OUT/'permutation_importance.csv')
''')
 n.pair('11.2 SHAP global explanation','Transform inputs with the exact fitted preprocessing. SHAP values explain model predictions, not real-world causes.', '''
import shap
if hasattr(final_model,'named_steps') and isinstance(final_model.named_steps['model'],(XGBRegressor,RandomForestRegressor,Ridge)):
    shap_model=final_model;shap_label=selected_name
else:
    shap_model=clone(models['XGBoost']).fit(Xdev,ydev);shap_label='Auxiliary XGBoost (not the selected model)'
transformed=shap_model.named_steps['preprocess'].transform(explain_X.iloc[:80])
feature_names=shap_model.named_steps['preprocess'].get_feature_names_out()
if isinstance(shap_model.named_steps['model'],Ridge):
    background=shap_model.named_steps['preprocess'].transform(Xdev.sample(min(100,len(Xdev)),random_state=SEED))
    explanation=shap.LinearExplainer(shap_model.named_steps['model'],background)(transformed)
else:
    explanation=shap.TreeExplainer(shap_model.named_steps['model'])(transformed)
explanation.feature_names=list(feature_names)
print('Explaining:',shap_label)
shap.plots.beeswarm(explanation,max_display=15,show=False);plt.tight_layout();plt.show()
''')
 n.pair('11.3 SHAP individual example','Inspect one representative row and its contributions in the prediction unit.', '''
display(explain_X.iloc[[0]])
shap.plots.waterfall(explanation[0],max_display=12,show=False);plt.tight_layout();plt.show()
''')
 n.m('## 12. Model export\n\nExport a full raw-history bundle plus a model card and ordered feature schema. The bundle includes the canonicalization/feature configuration and the fitted preprocessing/model; copy `civicflux_core.py` with the artifact. The input contract is a historical table in the downloaded schema, not an undocumented precomputed feature vector. Only load trusted joblib files.')
 n.pair('12.1 Record metadata and package versions','Unverified source provenance and timezone assumptions travel with the model.', '''
metadata={'task':KIND,'winner':selected_name,'source_url':'https://www.kaggle.com/datasets/'+SOURCES[KIND],'sha256':fingerprint,'units':cfg['unit'],'horizon':cfg['freq'],'timezone':cfg['tz'],'provenance':cfg['provenance'],'seed':SEED,'cv_folds':N_SPLITS,'search_iterations':N_SEARCH,'test_metrics':metrics,'interval_radius_90':radius,'operating_mode':'rolling one-step; current observation assumed available','deployment_status':'research; measurement lineage and reporting delays need validation','versions':{p:importlib.metadata.version(p) for p in ['pandas','numpy','scikit-learn','xgboost','shap','joblib']}}
schema={c:{'dtype':str(Xdev[c].dtype),'role':'feature'} for c in features}
(OUT/'metadata.json').write_text(json.dumps(metadata,indent=2,default=str))
(OUT/'feature_schema.json').write_text(json.dumps(schema,indent=2))
bundle=ForecastBundle(final_model,cfg,features,radius,metadata)
joblib.dump(bundle,OUT/'pipeline.joblib')
print('Exported to',OUT)
''')
 n.pair('12.2 Reload and forecast beyond the last observation','This is a genuine next-interval forecast. It is separate from the evaluated historical holdout and has no known label yet.', '''
loaded=joblib.load(OUT/'pipeline.joblib')
forecast=loaded.predict(raw)
pd.testing.assert_frame_equal(forecast,bundle.predict(raw))
display(forecast)
forecast.to_csv(OUT/'next_interval_forecast.csv',index=False)
print('PASS: serialized raw-history serving agrees with in-memory prediction')
''')
 n.m('## 13. CivicFlux integration\n\nEmit a typed prediction with geography, horizon, units, uncertainty and provenance. The example policy is illustrative and has no automatic public-alert or dispatch action. Different variables are never silently added into one risk score. Routing requires verified road connectivity, travel times and capacities; OR-Tools/NetworkX are not required for these forecasting tasks.')
 n.pair('13.1 Decision-engine payload','The engine can request review when uncertainty is wide. Thresholds below are examples, not validated operational limits.', '''
payloads=[]
for r in forecast.itertuples():
    payload={'variable':{'rainfall':'rainfall_mm_day','aqi':'pm25_concentration','traffic':'vehicle_count_hour'}[KIND], 'geography':r.entity,'origin':str(r.time),'valid_at':str(r.target_time),'timezone':cfg['tz'] or 'unknown','prediction':float(r.prediction),'interval_90':[float(r.lower_90),float(r.upper_90)],'unit':cfg['unit'],'source_quality':cfg['provenance'],'current_observation_missing':bool(r.source_missing),'action':'human_review_required','research_only':True}
    payloads.append(payload)
print(json.dumps(payloads,indent=2))
(OUT/'civicflux_payload.json').write_text(json.dumps(payloads,indent=2))
''')
 if kind=='traffic':
  n.pair('13.2 Separate traffic-disruption scenario simulator','Capacity loss and demand pressure are hypothetical inputs. Predicted flow is not translated into measured road speed. These scenario rows never enter real-data model evaluation.', '''
scenarios=[]
for r in forecast.itertuples():
    for loss in [0,.25,.50]:
        assumed_capacity=max(1,1.5*r.prediction)  # Explicit illustrative assumption, not measured.
        capacity=assumed_capacity*(1-loss)
        scenarios.append({'junction':r.entity,'assumed_capacity_loss':loss,'forecast_demand_count':r.prediction,'assumed_service_capacity':capacity,'unserved_count_proxy':max(0,r.prediction-capacity),'simulated':True})
disruption=pd.DataFrame(scenarios)
display(disruption)
sns.barplot(data=disruption,x='junction',y='unserved_count_proxy',hue='assumed_capacity_loss');plt.title('Synthetic disruption scenario, not observed congestion');plt.show()
disruption.to_csv(OUT/'synthetic_disruption_scenarios.csv',index=False)
''')
 n.m('### 13.3 Research conclusion and next validation\n\nRead the CV winner, baseline skill, extreme-error slice and interval coverage together. Negative baseline skill means the learned procedure has not justified replacing persistence. These files do not establish causal effects or field readiness. Before deployment, verify source units/timezone/reporting delay, measure geographic representativeness, backtest with latency, validate on later data, and establish domain-specific decision thresholds. For multiple future horizons, fit separate horizon-specific targets and repeat the temporal purge; do not relabel one-step outputs as a multi-day forecast.')
 n.save(d['file'])

# Flood notebook is intentionally a different scientific task: surrogate scenario classification.
n=Notebook('# CivicFlux — Reproducible Flood Scenario Classification\n\n**Real rainfall reference + explicitly synthetic drainage scenarios**\n\nA research surrogate for a documented mass-balance simulator. This notebook does not claim observed flood-event prediction or infrastructure-failure detection.')
n.m('## 01. Problem definition\n\nGiven a specified 24-hour storm scenario and hypothetical catchment/drainage parameters, estimate the probability that the simulator produces peak ponding depth ≥0.15 m. The threshold is a project assumption. Rainfall is a supplied scenario input, not an observed future predictor available to a live forecaster. For a real forecast, supply an external rainfall forecast and propagate its uncertainty; errors from that upstream model are not validated here.\n\nThe target is **simulated flood occurrence**, not generic FloodProbability, a verified incident, or infrastructure failure. No supplied dataset has verified pipe-failure labels. The simulator provides the authoritative deterministic answer; ML is an approximation whose accuracy does not validate the physics.')
n.pair('1.1 Reproducibility','All parameter ranges, seeds and equations are visible.',SETUP+"\nOUT=ROOT/'artifacts'/'flood'\nOUT.mkdir(parents=True,exist_ok=True)")
n.m('## 02. Dataset introduction\n\nUse the same downloaded [India daily rainfall](https://www.kaggle.com/datasets/wydoinn/daily-rainfall-data-india-2009-2024) reference as notebook 01. Four hypothetical drainage configurations are generated for each observed Delhi state-day. No resampling of a test-derived rainfall distribution occurs. Date groups stay together during splitting. State-average daily rainfall cannot establish local storm intensity: duration and spatial concentration are explicitly synthetic assumptions.\n\nThe [Playground flood score](https://www.kaggle.com/competitions/playground-series-s4e5/data) and [UrbanFloodBench](https://www.kaggle.com/competitions/urban-flood-modelling/data) are documented alternatives, not silently substituted training sources. See DATASET_GUIDE.md. This choice avoids presenting synthetic generic scores as observed flood incidents.')
n.pair('2.1 Load and inspect real rainfall reference','The complete original file is inspected before selecting Delhi.', '''
cfg=CONFIGS['rainfall'].copy()
source_path=ROOT/'data'/'raw'/cfg['file']
raw=pd.read_csv(source_path)
fingerprint=sha256(source_path)
print('Shape',raw.shape,'SHA256',fingerprint)
display(raw.head());display(raw.dtypes)
''')
n.pair('2.2 Select geography and report availability','Missing rainfall is excluded from scenario forcing, not treated as dry weather.', '''
history,rain_audit=canonicalize(raw,cfg)
display(pd.Series(rain_audit))
print('Reference interval',history.time.min(),history.time.max())
print('Valid real rainfall observations',history.value.notna().sum())
''')
n.m('### 2.3 Simulator equations and limits\n\nLet P be daily rainfall in mm, C a dimensionless effective runoff coefficient, D storm duration in hours, q drainage capacity in mm/hour over the catchment, b blockage fraction, S₀ initial equivalent storage in mm, and f the fraction of catchment area over which excess water ponds.\n\n$$R=CP,\\quad Q=q(1-b)D,\\quad S_{peak}=\\max(S_0, S_0+R-Q,0),\\quad h_{peak}=S_{peak}/(1000f).$$\n\nFor uniform storm intensity, storage rises or falls monotonically during the event, so the maximum is one of the endpoints. Catchment area A converts equivalent depths to volumes (m³ = mm × A / 1000), but cancels from the depth expression under a proportional drainage assumption. C lumps infiltration/interception losses; do not subtract infiltration again. No topographic routing, river overflow, tidal backwater, dynamic infiltration or pipe hydraulics is represented.\n\nThis is a deliberately simplified conservation-of-water model, **not EPA SWMM**. For the richer reservoir/routing framework see [EPA SWMM documentation](https://www.epa.gov/water-research/storm-water-management-model-swmm). All synthetic parameter ranges below are illustrative design choices, not fitted regional engineering constants.')
n.pair('2.4 Parameter distributions','These ranges define the synthetic population; the metrics only apply to it.', '''
parameter_table=pd.DataFrame([
 ['rain_mm','observed Delhi state daily rainfall','mm'],['duration_h','Uniform(1,12)','hours'],['area_m2','Uniform(10000,100000)','m²'],['runoff_coefficient','Uniform(.3,.95)','fraction'],['drain_mm_h','Uniform(.2,8)','mm/hour over catchment'],['blockage','Uniform(0,.9)','fraction'],['ponding_fraction','Uniform(.03,.2)','fraction'],['initial_storage_mm','Uniform(0,2)','mm over catchment']
],columns=['input','distribution','unit'])
display(parameter_table)
parameter_table.to_csv(OUT/'scenario_parameters.csv',index=False)
''')
n.pair('2.5 Generate a reproducible moderate-sized scenario set','Four configurations per real day preserve rainfall frequency, including dry days; one million near-duplicates would not add independent weather events.', '''
scenarios=generate_scenarios(history,repeats=4,seed=SEED)
pd.testing.assert_frame_equal(scenarios,generate_scenarios(history,repeats=4,seed=SEED))
print('Scenarios:',len(scenarios),'Independent dated forcing groups:',scenarios.event_id.nunique())
scenarios.to_csv(ROOT/'data'/'flood_scenarios.csv',index=False)
''')
n.m('## 03. Data inspection\n\nInspect both the real forcing and the generated outcomes. Synthetic cleanliness is not evidence of measurement quality.')
n.pair('3.1 Head, shape and types','Date/event identifiers are audit fields, not model inputs.', 'display(scenarios.head(10));print(scenarios.shape);display(scenarios.dtypes)')
n.pair('3.2 Nulls, duplicates and ranges','Scenario IDs must be unique; repeated event IDs are intentional groups.', '''
display(scenarios.isna().sum());print('Duplicate scenario IDs:',scenarios.scenario_id.duplicated().sum())
display(scenarios.describe().T)
assert scenarios.scenario_id.is_unique
assert not scenarios[FLOOD_FEATURES+['target']].isna().any().any()
''')
n.pair('3.3 Target prevalence','An imbalanced simulator calls for precision-recall metrics and per-fold class checks.', '''
display(scenarios.target.value_counts().rename({0:'no simulated flood',1:'simulated flood'}))
print('Positive prevalence:',scenarios.target.mean())
sns.countplot(data=scenarios,x='target');plt.title('Synthetic labels, not incident reports');plt.show()
''')
n.pair('3.4 Reference rainfall missingness','The scenario set omits missing forcing; report that selection effect.', '''
history.set_index('time').value.isna().resample('YS').mean().plot.bar(title='Fraction unavailable rainfall by year')
plt.tight_layout();plt.show()
''')
n.m('## 04. Exploratory analysis\n\nEDA uses the development period only. Labels describe the simulator; relations can reflect its equations by construction.')
n.c('dev,cal,test=partition(scenarios)\neda=dev.copy()\nprint("Development scenario count",len(eda))')
n.pair('4.1 Real rainfall distribution and synthetic depth','Dry days dominate many rainfall series, while concentrating water into a small ponded area creates a long depth tail.', '''
fig,ax=plt.subplots(1,2,figsize=(12,4))
sns.histplot(eda.drop_duplicates('event_id').rain_mm,bins=50,ax=ax[0]);ax[0].set_title('Independent reference-day rainfall')
sns.histplot(eda.depth_m,bins=60,ax=ax[1]);ax[1].axvline(.15,color='red');ax[1].set_title('Synthetic peak depth; threshold 0.15 m')
plt.tight_layout();plt.show()
''')
n.pair('4.2 Seasonal event rate','The rate is conditional on synthetic asset ranges and must not be called observed flood frequency.', '''
eda.assign(month=eda.time.dt.month).groupby('month').target.mean().plot.bar(title='Simulated event fraction by month',ylabel='Synthetic event fraction');plt.show()
''')
n.pair('4.3 Drainage and blockage relationships','Plot sampled design parameters against label to inspect simulator behavior.', '''
fig,ax=plt.subplots(1,2,figsize=(12,4))
sns.boxplot(data=eda,x='target',y='drain_mm_h',ax=ax[0])
sns.boxplot(data=eda,x='target',y='blockage',ax=ax[1])
plt.tight_layout();plt.show()
''')
n.pair('4.4 Rainfall-depth response','Multiple depths for the same rain amount reflect differing hypothetical catchments.', '''
sns.scatterplot(data=eda.sample(min(2500,len(eda)),random_state=SEED),x='rain_mm',y='depth_m',hue='blockage',palette='viridis',s=10)
plt.axhline(.15,color='red',ls='--');plt.title('Simulated depth response');plt.show()
''')
n.pair('4.5 Correlation matrix','Depth and target appear only for diagnosis and are forbidden model features.', '''
sns.heatmap(eda[FLOOD_FEATURES+['depth_m','target']].corr(),center=0,cmap='coolwarm');plt.title('Simulator correlations');plt.tight_layout();plt.show()
''')
n.pair('4.6 Temporal forcing coverage','Independent storms/days, not scenario row count, determine weather diversity.', '''
eda.drop_duplicates('event_id').set_index('time').rain_mm.resample('MS').sum().plot(title='Development monthly rainfall sum (available days only)',ylabel='mm');plt.show()
''')
n.m('## 05. Preprocessing\n\nReal rainfall uses the same exact-duplicate, negative-value and regular-grid policies as notebook 01. No future interpolation and no deletion of positive extremes. Synthetic inputs are finite by construction; a pipeline imputer is retained for consistent model infrastructure, while serving rejects missing physical inputs. Scaling is only used for Logistic Regression. No city-name join, geospatial interpolation or synthetic incident count is performed.')
n.pair('5.1 Physical range checks','Fail on impossible fractions rather than silently clipping them.', '''
assert scenarios.rain_mm.ge(0).all()
assert scenarios.duration_h.between(1,12).all()
assert scenarios.blockage.between(0,.9).all()
assert scenarios.ponding_fraction.between(.03,.2).all()
assert scenarios.depth_m.ge(0).all()
print('PASS: simulator physical ranges')
''')
n.pair('5.2 Unit and conservation check','Area cancels from depth but not volume. The end-of-event balance tracks rainfall runoff, drainage and remaining storage.', '''
x=eda.head(1000)
initial=x.initial_storage_mm*x.area_m2/1000
runoff=x.rain_mm*x.runoff_coefficient*x.area_m2/1000
capacity=x.drain_mm_h*(1-x.blockage)*x.duration_h*x.area_m2/1000
outflow=np.minimum(initial+runoff,capacity)
final=np.maximum(0,initial+runoff-capacity)
np.testing.assert_allclose(initial+runoff,outflow+final,rtol=1e-12,atol=1e-8)
print('Maximum water-balance error (m³):',np.max(np.abs(initial+runoff-outflow-final)))
''')
n.pair('5.3 Labels and identifiers are excluded','Derived depth, storage and the exact threshold function would directly reveal the answer.', '''
features=FLOOD_FEATURES.copy()
assert not {'depth_m','target','event_id','scenario_id','target_time'} & set(features)
display(pd.DataFrame({'feature':features}))
''')
n.m('## 06. Feature engineering\n\nPrimary inputs are scenario forcing and physical design assumptions. Avoid adding the exact net-storage/depth formula as a predictor: that would trivialize label reconstruction. Area is retained as a negative-control variable; the specified physics predicts no direct area effect under proportional capacity. Model importance on area can reveal approximation artifacts. No incident-history, observed speed or measured water-level field is invented.')
n.pair('6.1 Illustrate sensitivity features without training on target algebra','Effective drainage and runoff are diagnostic quantities, excluded from the feature matrix.', '''
diagnostic=eda[['rain_mm','drain_mm_h','blockage']].copy()
diagnostic['effective_capacity']=diagnostic.drain_mm_h*(1-diagnostic.blockage)
sns.scatterplot(data=diagnostic.sample(min(1500,len(diagnostic)),random_state=SEED),x='blockage',y='effective_capacity',s=10)
plt.title('Effective drainage capacity is reduced by blockage');plt.ylabel('mm/hour');plt.show()
''')
n.pair('6.2 Demonstrate area invariance','Changing catchment area alone should not change depth in this deliberately simplified model.', '''
a=eda[features].head(100).copy();b=a.copy();b['area_m2']*=2
np.testing.assert_allclose(simulate_depth(a),simulate_depth(b))
print('PASS: depth is invariant to area under proportional drainage capacity')
''')
n.pair('6.3 Monotonic physical checks','Increasing rainfall or blockage cannot reduce depth under these equations.', '''
a=eda[features].head(1000).copy()
b=a.copy();b.rain_mm+=20
c=a.copy();c.blockage=np.minimum(.99,c.blockage+.1)
assert (simulate_depth(b)>=simulate_depth(a)-1e-12).all()
assert (simulate_depth(c)>=simulate_depth(a)-1e-12).all()
print('PASS: rainfall and blockage monotonicity')
''')
n.m('## 07. Training strategy\n\nSplit by unique real forcing date, then use expanding, purged temporal folds. All four scenarios from a date remain together. This tests transfer to later rainfall dates, not transfer to real assets or unseen physical laws. The middle 20% is further divided chronologically into probability-calibration and decision-threshold segments. Only development data is used for model selection. Class weights are learned/controlled inside each model fit; no global SMOTE is used.')
n.pair('7.1 Audit split and class balance','Every training and validation fold must contain both classes.', '''
Xdev,ydev=dev[features],dev.target
Xtest,ytest=test[features],test.target
folds=temporal_folds(dev,N_SPLITS)
for tr,va in folds:
    assert dev.iloc[tr].target.nunique()==2 and dev.iloc[va].target.nunique()==2
for left,right in [(dev,cal),(cal,test)]:
    assert not set(left.event_id)&set(right.event_id)
    assert left.target_time.max()<right.time.min()
split_summary=pd.DataFrame([{'split':name,'rows':len(z),'forcing_dates':z.event_id.nunique(),'prevalence':z.target.mean(),'start':str(z.time.min()),'end':str(z.time.max())} for name,z in [('dev',dev),('cal',cal),('test',test)]])
display(split_summary);split_summary.to_csv(OUT/'splits.csv',index=False)
''')
n.pair('7.2 Models and fold-local preprocessing','Compare prior probability, standard Logistic Regression, balanced Logistic Regression and XGBoost. PR-AUC is the selection metric because simulated floods are rare.', '''
from sklearn.linear_model import LogisticRegression
from sklearn.dummy import DummyClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (average_precision_score,roc_auc_score,brier_score_loss,classification_report,ConfusionMatrixDisplay,PrecisionRecallDisplay,RocCurveDisplay,f1_score,precision_score,recall_score)
from sklearn.calibration import calibration_curve
from xgboost import XGBClassifier

def clf_pipeline(model,scale=False):
    steps=[('impute',SimpleImputer(strategy='median',keep_empty_features=True))]
    if scale: steps.append(('scale',StandardScaler()))
    return Pipeline(steps+[('model',model)])
models={
 'Prior':clf_pipeline(DummyClassifier(strategy='prior')),
 'Logistic':clf_pipeline(LogisticRegression(max_iter=3000,random_state=SEED),True),
 'Logistic balanced':clf_pipeline(LogisticRegression(class_weight='balanced',max_iter=3000,random_state=SEED),True),
 'XGBoost':clf_pipeline(XGBClassifier(n_estimators=120,max_depth=3,learning_rate=.05,eval_metric='logloss',tree_method='hist',n_jobs=2,random_state=SEED))}
''')
n.m('## 08. Model experiments\n\nThe deterministic simulator itself has perfect agreement with its labels by definition. The learned models only approximate this mapping. Their CV scores cannot demonstrate real-world flood validity.')
n.pair('8.1 Compare models on temporal folds','Report average precision and ROC-AUC, plus calibration-sensitive Brier loss.', '''
cv_rows=[]
for name,model in models.items():
    scores=cross_validate(model,Xdev,ydev,cv=folds,scoring={'ap':'average_precision','auc':'roc_auc','brier':'neg_brier_score'},error_score='raise',n_jobs=1)
    for i in range(N_SPLITS):
        cv_rows.append({'model':name,'fold':i,'AP':scores['test_ap'][i],'ROC_AUC':scores['test_auc'][i],'Brier':-scores['test_brier'][i]})
cv_details=pd.DataFrame(cv_rows)
summary=cv_details.groupby('model').agg(AP=('AP','mean'),AP_std=('AP','std'),ROC_AUC=('ROC_AUC','mean'),Brier=('Brier','mean')).sort_values('AP',ascending=False)
display(summary);cv_details.to_csv(OUT/'candidate_cv.csv',index=False)
''')
n.pair('8.2 Visualize discrimination and calibration','Balanced weighting can improve recall while distorting raw probability calibration.', '''
fig,ax=plt.subplots(1,2,figsize=(12,4))
summary.AP.plot.barh(xerr=summary.AP_std,ax=ax[0],title='CV average precision ± fold standard deviation')
summary.Brier.plot.barh(ax=ax[1],title='CV Brier loss (lower better)');plt.tight_layout();plt.show()
''')
n.m('## 09. Hyperparameter tuning\n\nTune both primary families: Logistic Regression (including weighting) and XGBoost. Keep the same grouped temporal folds. Use two distinct later calibration blocks so probability calibration and action-threshold choice do not share labels.')
n.pair('9.1 Search spaces','No test-label class ratio or test-period early stopping is used.', '''
spaces={'Logistic':{'model__C':[.01,.1,1,10,100],'model__class_weight':[None,'balanced']},'XGBoost':{'model__n_estimators':[80,140,220],'model__max_depth':[2,3,5],'model__learning_rate':[.03,.08,.15],'model__min_child_weight':[1,5,10],'model__scale_pos_weight':[1,3,10],'model__reg_lambda':[1,5,10]}}
searches={}
selection={name:float(summary.loc[name,'AP']) for name in models}
for name,space in spaces.items():
    s=RandomizedSearchCV(models[name],space,n_iter=N_SEARCH,scoring='average_precision',cv=folds,random_state=SEED,n_jobs=1,error_score='raise',return_train_score=True)
    s.fit(Xdev,ydev);searches[name]=s;selection[name+' tuned']=s.best_score_
    trials=pd.DataFrame(s.cv_results_);trials.to_csv(OUT/(name+'_search.csv'),index=False)
    display(trials.sort_values('rank_test_score')[['mean_test_score','std_test_score','params']].head())
selected_name=max(selection,key=selection.get)
final_model=searches[selected_name.removesuffix(' tuned')].best_estimator_ if selected_name.endswith(' tuned') else clone(models[selected_name]).fit(Xdev,ydev)
print('Locked winner:',selected_name)
''')
n.pair('9.2 Tuning comparison plot','Selection scores are development estimates, not final performance.', '''
pd.Series(selection).sort_values().plot.barh(title='Development CV selection scores',xlabel='Average precision');plt.tight_layout();plt.show()
''')
n.pair('9.3 Probability calibration','Isotonic calibration maps raw probabilities on the earlier half of the calibration dates. If there are too few positives, stop and enlarge the study rather than silently reporting invalid calibration.', '''
cal_times=np.sort(cal.time.unique());boundary=cal_times[len(cal_times)//2]
prob_cal=cal[(cal.time<boundary)&(cal.target_time<boundary)].copy()
threshold_cal=cal[cal.time>=boundary].copy()
assert prob_cal.target.sum()>=10 and threshold_cal.target.sum()>=10
assert prob_cal.target.nunique()==2 and threshold_cal.target.nunique()==2
calibrator=IsotonicRegression(out_of_bounds='clip')
calibrator.fit(final_model.predict_proba(prob_cal[features])[:,1],prob_cal.target)
p_threshold=calibrator.predict(final_model.predict_proba(threshold_cal[features])[:,1])
''')
n.pair('9.4 Choose an explicit decision threshold','Illustrative false-negative cost is five times false-positive cost. This project utility assumption requires stakeholder validation; it is not an emergency policy.', '''
threshold_rows=[]
for threshold in np.linspace(.01,.99,99):
    yhat=p_threshold>=threshold
    fn=int(((threshold_cal.target==1)&~yhat).sum())
    fp=int(((threshold_cal.target==0)&yhat).sum())
    threshold_rows.append({'threshold':threshold,'cost':5*fn+fp,'FN':fn,'FP':fp})
threshold_table=pd.DataFrame(threshold_rows)
threshold=float(threshold_table.sort_values(['cost','threshold']).iloc[0].threshold)
threshold_table.plot(x='threshold',y='cost',title='Threshold selection on separate calibration dates');plt.axvline(threshold,color='red');plt.show()
print('Locked threshold:',threshold)
threshold_table.to_csv(OUT/'threshold_search.csv',index=False)
''')
n.m('## 10. Final evaluation\n\nEvaluate discrimination, calibration, decision errors, rainfall regimes and physical sensitivities. All labels remain synthetic. Accuracy alone would conceal rare-event failures.')
n.pair('10.1 Final metrics and confusion matrix','The model, calibrator and threshold are frozen before this cell.', '''
p_raw=final_model.predict_proba(Xtest)[:,1]
p=calibrator.predict(p_raw)
yhat=p>=threshold
metrics={'average_precision':float(average_precision_score(ytest,p)),'ROC_AUC':float(roc_auc_score(ytest,p)),'Brier_raw':float(brier_score_loss(ytest,p_raw)),'Brier_calibrated':float(brier_score_loss(ytest,p)),'F1':float(f1_score(ytest,yhat)),'precision':float(precision_score(ytest,yhat,zero_division=0)),'recall':float(recall_score(ytest,yhat)),'threshold':threshold,'positive_prevalence':float(ytest.mean())}
display(pd.Series(metrics));print(classification_report(ytest,yhat,zero_division=0))
ConfusionMatrixDisplay.from_predictions(ytest,yhat,display_labels=['No simulated flood','Simulated flood']);plt.show()
''')
n.pair('10.2 Precision-recall and ROC curves','PR baseline equals test prevalence; a strong ROC score can coexist with poor rare-event precision.', '''
fig,ax=plt.subplots(1,2,figsize=(12,4))
PrecisionRecallDisplay.from_predictions(ytest,p,ax=ax[0]);ax[0].axhline(ytest.mean(),ls='--',color='grey')
RocCurveDisplay.from_predictions(ytest,p,ax=ax[1]);plt.tight_layout();plt.show()
''')
n.pair('10.3 Probability reliability','Compare raw and calibrated probabilities; calibration can worsen under temporal or simulator shift.', '''
for label,probs in [('raw',p_raw),('calibrated',p)]:
    observed,mean=calibration_curve(ytest,probs,n_bins=10,strategy='quantile')
    plt.plot(mean,observed,marker='o',label=label)
plt.plot([0,1],[0,1],'k--');plt.legend();plt.xlabel('Mean probability');plt.ylabel('Observed synthetic fraction');plt.title('Final test reliability');plt.show()
''')
n.pair('10.4 Error analysis and exportable examples','False negatives can cluster near the assumed 0.15 m threshold.', '''
errors=test.copy();errors['probability']=p;errors['predicted']=yhat;errors['wrong']=yhat!=ytest
errors['rain_bin']=pd.cut(errors.rain_mm,[-.01,1,10,30,100,np.inf])
display(errors.groupby('rain_bin',observed=True).agg(n=('target','size'),positives=('target','sum'),error_rate=('wrong','mean')))
display(errors[errors.wrong].sort_values('depth_m',ascending=False).head(12))
errors.to_csv(OUT/'test_predictions.csv',index=False)
''')
n.pair('10.5 Check sensitivity outside sampled conditions','These are labeled stress scenarios, not new real test observations. A classifier can violate physics even if its average score is high.', '''
stress=Xtest.head(1000).copy();stress['rain_mm']*=1.5;stress['blockage']=np.minimum(.99,stress.blockage+.1)
stress_truth=(simulate_depth(stress)>=.15).astype(int)
stress_p=calibrator.predict(final_model.predict_proba(stress)[:,1])
print('Shifted synthetic scenario recall:',recall_score(stress_truth,stress_p>=threshold,zero_division=0))
print('Fraction with decreasing probability despite increased forcing:',np.mean(stress_p<p[:len(stress)]-1e-9))
''')
n.m('## 11. Explainability\n\nImportance reflects simulator emulation. It does not discover real hydrological causes. Features such as area should have negligible true effect under the stated equations; nonzero model attribution indicates approximation or correlation artifacts.')
n.pair('11.1 Permutation importance','Calibration dates are used for explanation; no feature reselection follows.', '''
explain_X=threshold_cal[features].sample(min(300,len(threshold_cal)),random_state=SEED)
explain_y=threshold_cal.target.loc[explain_X.index]
pi=permutation_importance(final_model,explain_X,explain_y,scoring='average_precision',n_repeats=4,random_state=SEED)
importance=pd.Series(pi.importances_mean,index=features).sort_values()
importance.plot.barh(title='Locked model: permutation decrease in average precision');plt.tight_layout();plt.show()
importance.to_csv(OUT/'permutation_importance.csv')
''')
n.pair('11.2 SHAP global explanation','SHAP explains the underlying fitted XGBoost margin, before isotonic calibration. If Logistic wins, this plot is explicitly an auxiliary XGBoost explanation.', '''
import shap
if isinstance(final_model.named_steps['model'],XGBClassifier):
    shap_model=final_model;shap_label=selected_name
else:
    shap_model=searches['XGBoost'].best_estimator_;shap_label='Auxiliary XGBoost, not selected model'
transformed=shap_model[:-1].transform(explain_X.iloc[:100])
if isinstance(shap_model.named_steps['model'],Ridge):
    background=shap_model.named_steps['preprocess'].transform(Xdev.sample(min(100,len(Xdev)),random_state=SEED))
    explanation=shap.LinearExplainer(shap_model.named_steps['model'],background)(transformed)
else:
    explanation=shap.TreeExplainer(shap_model.named_steps['model'])(transformed)
explanation.feature_names=features
print('Explaining',shap_label,'raw margin, not calibrated probability')
shap.plots.beeswarm(explanation,show=False);plt.tight_layout();plt.show()
''')
n.pair('11.3 Individual explanation','Show the physical inputs next to the raw-model explanation.', '''
display(explain_X.iloc[[0]])
shap.plots.waterfall(explanation[0],show=False);plt.tight_layout();plt.show()
''')
n.m('## 12. Model export\n\nExport the input pipeline, probability calibrator, threshold, schema, simulator assumptions and source checksum. Serving accepts only supplied scenario inputs; it never pretends to know tomorrow’s actual rain.')
n.pair('12.1 Save reproducible artifacts','A versioned module holds the bundle class so joblib does not rely on notebook-local definitions.', '''
metadata={'task':'synthetic flood scenario classification','winner':selected_name,'seed':SEED,'rain_sha256':fingerprint,'scenario_count':len(scenarios),'forcing_dates':scenarios.event_id.nunique(),'synthetic':True,'label':'simulated peak depth >= 0.15 m','scenario_horizon':'24 hours; uniform storm duration 1–12 h','spatial_support':'Delhi state rainfall reference, hypothetical catchments','physics':'lumped mass balance, uncalibrated','metrics':metrics,'deployment_status':'research scenario surrogate; not validated real flood or infrastructure failure forecast','versions':{name:importlib.metadata.version(name) for name in ['numpy','pandas','scikit-learn','xgboost','shap']}}
bundle=FloodBundle(final_model,calibrator,threshold,metadata)
joblib.dump(bundle,OUT/'pipeline.joblib')
(OUT/'metadata.json').write_text(json.dumps(metadata,indent=2,default=str))
(OUT/'feature_schema.json').write_text(parameter_table.to_json(orient='records',indent=2))
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2))
''')
n.pair('12.2 Serialization round-trip','Verify that the saved artifact accepts scenario inputs and reproduces probabilities.', '''
loaded=joblib.load(OUT/'pipeline.joblib')
example=Xtest.iloc[[0]].copy()
pd.testing.assert_frame_equal(loaded.predict(example),bundle.predict(example))
display(loaded.predict(example));print('PASS: flood bundle round-trip')
''')
n.m('## 13. CivicFlux integration\n\nUse a scenario envelope to request an engineering review. A rainfall forecast interval is uncertainty about state-scale rainfall, not automatically the local storm forcing. The illustrative range below is user-supplied hypothetical rainfall. No unrelated AQI/traffic location is joined. No automatic evacuation, dispatch, road closure or risk claim is made.')
n.pair('13.1 Scenario envelope from uncertain rainfall input','Evaluate low, central and high supplied rain values independently. The probability range is not a calibrated joint flood forecast interval.', '''
scenario_inputs=pd.concat([example]*3,ignore_index=True)
scenario_inputs['rain_mm']=[10,30,70]  # Hypothetical low/central/high storm totals.
scenario_results=loaded.predict(scenario_inputs)
scenario_results['supplied_rain_mm']=scenario_inputs.rain_mm
display(scenario_results)
scenario_results.plot(x='supplied_rain_mm',y='simulated_flood_probability',marker='o',title='Conditional synthetic scenario envelope');plt.show()
''')
n.pair('13.2 Decision-engine payload','Carry the synthetic flag and physical assumptions into every consumer.', '''
payload={'variable':'simulated_flood_scenario_probability','synthetic':True,'geography':'hypothetical catchment; Delhi state rainfall reference only','horizon_hours':24,'rain_scenarios_mm':[10,30,70],'probabilities':scenario_results.simulated_flood_probability.tolist(),'decision_threshold':threshold,'action':'engineering_review' if scenario_results.scenario_alert.any() else 'retain_for_scenario_planning','automatic_dispatch':False,'limitations':['uncalibrated drainage','no real incident labels','daily state rainfall is not local storm intensity','no infrastructure-failure labels']}
print(json.dumps(payload,indent=2))
(OUT/'civicflux_payload.json').write_text(json.dumps(payload,indent=2))
''')
n.m('### 13.3 Research conclusion\n\nA high score means successful emulation of this simulator over later forcing dates. It does not validate local rainfall, hydrodynamics, observed floods or engineering design. Before real incident prediction, acquire measured local rainfall and water levels, dated flood incidents, drainage geometry and maintenance records, calibrate/validate the physical model against observed events, and hold out catchments as well as time. Changing parameter ranges or the depth threshold defines a new synthetic population and requires repeating the full study.')
n.save('04_Flood_Research.ipynb')
print('Generated:',[(p.name,len(nbf.read(p,as_version=4).cells)) for p in (ROOT/'notebooks').glob('*.ipynb')])
