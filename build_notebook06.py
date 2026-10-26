from notebook_builder import *
n=ResearchNotebook('06_Water_Network_Fault_Research.ipynb','CivicFlux — Water-Network Fault Detection')
n.section(1,'Problem definition','''Use the public BattLeDIM/L-TOWN benchmark to detect whether **a new leakage episode began within the preceding 24 hours**, at hourly observation instants. This is early-stage network-level detection, not localization or a classifier of every ongoing leak. A negative label may include an older persistent leak. The endpoint is chosen to avoid interpreting the near-continuous existence of background leakage as a meaningful easy classification task.

L-TOWN is a hypothetical benchmark generated from a Cyprus network. Its readings and leakage labels are simulated benchmark evidence, never real Delhi incidents. This retrospective study uses released ground-truth leak-flow tables; it is not a competition submission or a claim of reproducing official BattLeDIM scoring.''')
n.step('Environment and versioned outputs','Reuse the existing project, source checksum utility and shared graph representation. No legacy notebook is regenerated.',SETUP+"\nfrom src.civicflux.water import *\nfrom src.civicflux.graph import read_epanet\nOUT=ROOT/'artifacts/water_network/v1.0.0'\nOUT.mkdir(parents=True,exist_ok=True)\nDATA=ROOT/'data/raw/battledim'\n")
n.section(2,'Source verification and measurement contract','''Official [Zenodo record 4017659](https://zenodo.org/records/4017659) and [BattLeDIM organizers](https://battledim.ucy.ac.cy/) provide the public benchmark. License: CC BY 4.0; credit Vrachimis and coauthors, DOI 10.5281/zenodo.4017659. Download with `python download_battledim.py`; no account/API key was required. The script checks every selected file against official MD5 metadata.

CSV format uses semicolon separators and decimal commas, timestamps `YYYY-MM-DD HH:MM:SS`, at five-minute cadence. Timezone/receipt latency are unspecified and remain source-local. Pressures and tank level are meters; flows/leak outflows are m³/hour; optional AMR demands are L/hour. The nominal EPANET graph contains sensor node/link identities, relative coordinates and nominal demands. Those coordinates are not Delhi GIS locations. Demand EDA uses nominal network demand and patterns, not invented measured AMR data.''')
n.step('Verify files, checksums and licensing','The source metadata snapshot and file contents establish the version used. Missing required files stop the study.', '''
import hashlib
record=json.loads((DATA/'record.json').read_text())
print('License',record['metadata']['license'])
required=['L-TOWN.inp','README.txt','dataset_configuration.yaml']+[f'{y}_{kind}.csv' for y in [2018,2019] for kind in ['SCADA_Pressures','SCADA_Flows','SCADA_Levels','Leakages']]
verified=[]
for name in required:
    path=DATA/name;entry=next(e for e in record['files'] if e['key']==name)
    assert path.exists(),f'Run download_battledim.py: missing {name}'
    assert hashlib.md5(path.read_bytes()).hexdigest()==entry['checksum'].split(':')[1]
    verified.append({'file':name,'bytes':path.stat().st_size,'sha256':sha256(path)})
display(pd.DataFrame(verified));write_json(OUT/'source_manifest.json',verified)
''')
n.step('Load SCADA and independent label tables','Pressure/flow/level observations are joined only on exact timestamps inside this one documented network.', '''
measurements,leakages=load_benchmark(DATA)
graph=read_epanet(DATA/'L-TOWN.inp')
for name,d in measurements.items():
    print(name,d.shape,d.index.min(),d.index.max());display(d.head(3))
print('Leakage label matrix',leakages.shape,'Topology',graph.number_of_nodes(),'nodes',graph.number_of_edges(),'links')
''')
n.section(3,'Data inspection and sensor mapping','''Inspect every measurement family for missingness, duplicates, cadence, units and supported IDs. Flow sensors identify links; pressure sensors identify nodes. Link orientation is not inferred from count values. Topology is nominal and may differ from the hydraulic simulator used to generate readings.''')
n.step('Coverage and missingness','Missing readings are not imputed labels. Current predictor gaps are handled in the train-fitted preprocessing and explicitly guarded at serving.', '''
audit=[]
for name,d in measurements.items():
    audit.append({'family':name,'rows':len(d),'sensors':len(d.columns),'missing':int(d.isna().sum().sum()),'duplicate_times':int(d.index.duplicated().sum()),'cadence_minutes':d.index.to_series().diff().dt.total_seconds().median()/60})
    display(d.describe().T.head(8))
audit=pd.DataFrame(audit);display(audit);audit.to_csv(OUT/'data_audit.csv',index=False)
audit.plot.bar(x='family',y='missing',title='Missing values in source SCADA',legend=False);plt.show()
''')
n.step('Verify sensor placement','Every pressure/level sensor must exist as a node; every flow sensor must exist as a link.', '''
link_ids={k for u,v,k in graph.edges(keys=True)}
assert set(measurements['Pressures']).issubset(graph.nodes)
assert set(measurements['Levels']).issubset(graph.nodes)
assert set(measurements['Flows']).issubset(link_ids)
print('All source sensor identities mapped to nominal EPANET topology.')
print('Connected components',nx.number_connected_components(graph))
''')
n.section(4,'EDA: hydraulic patterns and topology','''Analytical time-series EDA uses 2018 before September. Source-level coverage inspection is retained for both years; model selection never consults final 2019 targets.''')
n.step('Pressure sensor distributions','Different elevations and positions generate different baseline pressures, so location IDs must be retained.', '''
pressure=measurements['Pressures'].loc[:'2018-08-31'].iloc[::12]
pressure.plot.box(figsize=(15,5),rot=90,title='Development pressure by sensor (m)');plt.tight_layout();plt.show()
''')
n.step('Pressure and flow temporal traces','Five-minute readings are downsampled at exact hourly instants. No future interval average is assigned to an earlier observation.', '''
fig,ax=plt.subplots(3,1,figsize=(12,10),sharex=True)
for (family,d),a in zip(measurements.items(),ax):
    d.loc['2018-02-01':'2018-02-07'].iloc[::12,:min(4,len(d.columns))].plot(ax=a,title=family+' example week')
plt.tight_layout();plt.show()
''')
n.step('Diurnal demand-related patterns','Daily hydraulic cycles are consistent with demand variation. Nominal demand is a network input, not a measured customer-use label.', '''
fig,ax=plt.subplots(1,2,figsize=(13,4))
for col in measurements['Flows']:
    d=measurements['Flows'].loc[:'2018-08-31'];d.groupby(d.index.hour)[col].mean().plot(ax=ax[0],label=col)
ax[0].legend();ax[0].set(title='Development mean flow by hour',ylabel='m³/hour')
nominal=pd.Series(nx.get_node_attributes(graph,'base_demand'))
sns.histplot(nominal[nominal>0],bins=40,ax=ax[1]);ax[1].set_title('Positive nominal node demands (EPANET input units)')
plt.tight_layout();plt.show()
print('Nominal EPANET demand units are determined by its OPTIONS/UNITS; inspect below.')
lines=(DATA/'L-TOWN.inp').read_text().splitlines()
print('\\n'.join(line for line in lines if 'Units' in line or 'UNITS' in line)[:500])
''')
n.step('Network map and sensor locations','Coordinates are benchmark plotting coordinates; edges are physical pipe adjacency, not civic dependency probabilities.', '''
pos=nx.get_node_attributes(graph,'pos')
plt.figure(figsize=(12,9))
nx.draw_networkx_edges(graph,pos,alpha=.25,width=.5)
nx.draw_networkx_nodes(graph,pos,node_size=3,node_color='grey')
nx.draw_networkx_nodes(graph,pos,nodelist=list(measurements['Pressures'].columns),node_size=35,node_color='tab:red',label='Pressure sensors')
plt.legend();plt.title('L-TOWN nominal topology and pressure sensor placement');plt.axis('equal');plt.show()
''')
n.step('Sensor correlation and redundancy','Highly correlated pressures may reflect shared hydraulics. They are not independent fault confirmations.', '''
sns.heatmap(pressure.corr(),cmap='coolwarm',vmin=-1,vmax=1);plt.title('Development pressure correlations');plt.tight_layout();plt.show()
''')
n.section(5,'Leakage episodes and honest labels','''Ground-truth leakage-flow columns are used only to identify the start of each positive contiguous episode. They are never features. The target is a preceding-24-hour onset window, not a generic active-leak flag. The public labels enable supervised benchmark experiments but do not validate real-world fault incidence.''')
n.step('Create documented onset labels','The first positive leak-flow sample marks onset; the original five-minute resolution imposes detection-time granularity.', '''
f=water_features(measurements)
y,events=onset_labels(leakages,f.index)
display(events);print('Recent-onset prevalence',y.mean())
events.to_csv(OUT/'label_events.csv',index=False)
fig,ax=plt.subplots(2,1,figsize=(12,6),sharex=True)
leakages.sum(axis=1).iloc[::12].plot(ax=ax[0],title='Total benchmark leakage flow (label-only)',ylabel='m³/hour')
y.plot(ax=ax[1],title='Target: onset within preceding 24 hours',ylabel='Binary label')
plt.tight_layout();plt.show()
''')
n.step('Inspect overlapping episodes','Simultaneous events reduce the interpretability of network-wide onset alerts. No individual pipe localization is claimed.', '''
active=(leakages>1e-6).sum(axis=1)
print('Maximum simultaneous active pipes',int(active.max()))
print('Hourly labels',y.value_counts().to_dict())
events.groupby(events.onset.dt.year).size().plot.bar(title='Released episode onsets by year',ylabel='Events');plt.show()
''')
n.section(6,'Causal features and preprocessing','''Features include each pressure/flow/level value at t, its one-hour difference, a trailing 24-hour mean, missingness and known clock phase. Label files and future observations are excluded. Numeric medians are fitted only on training folds. Logistic Regression is scaled; tree models are not. Hourly scoring reduces compute and bounds minimum resolution to roughly an hour; it is not five-minute competition performance.''')
n.step('Feature schema and target exclusion','Serving uses exactly the same feature builder and ordered sensor contract.', '''
feature_names=list(f.columns);numeric=feature_names;categorical=[]
assert not any('leak' in col.lower() for col in feature_names)
display(f.head(28).tail(6))
write_json(OUT/'feature_schema.json',{'features':feature_names,'units':UNITS,'sensor_ids':{k:list(v.columns) for k,v in measurements.items()}})
''')
n.step('Future perturbation test','Changing future pressure observations must leave earlier feature rows identical.', '''
copy={k:v.copy() for k,v in measurements.items()}
cut=pd.Timestamp('2018-06-01');copy['Pressures'].loc[copy['Pressures'].index>cut]=9999
pd.testing.assert_frame_equal(f.loc[:cut],water_features(copy).loc[:cut])
print('PASS: causal water features')
''')
n.section(7,'Time- and event-aware validation','''Development: January–August 2018. Validation: September–December 2018. Final: 2019. Any 24-hour onset target episode crossing a boundary is excluded with a 24-hour context buffer. Expanding CV uses a 24-hour gap, preventing one onset window from appearing on both sides of a fold. Older persistent leakage remains possible in negative examples by target definition. These choices are frozen before final evaluation.''')
n.step('Construct and audit splits','Both classes must exist in each fold; otherwise the study stops rather than reporting meaningless PR-AUC.', '''
data=split_water(f,y,events)
train=data[data.period.eq('train')];val=data[data.period.eq('validation')];test=data[data.period.eq('test')]
Xtrain,ytrain=train[feature_names],train.target
Xval,yval=val[feature_names],val.target
Xtest,ytest=test[feature_names],test.target
folds=list(TimeSeriesSplit(n_splits=3,gap=24).split(Xtrain))
for tr,va in folds:
    assert Xtrain.index[tr].max()<Xtrain.index[va].min()-pd.Timedelta(hours=23)
    assert ytrain.iloc[tr].nunique()==2 and ytrain.iloc[va].nunique()==2
split_report=pd.DataFrame([{'split':s,'n':len(d),'positive':d.target.sum(),'start':str(d.index.min()),'end':str(d.index.max())} for s,d in [('train',train),('validation',val),('test',test)]])
display(split_report);split_report.to_csv(OUT/'splits.csv',index=False)
''')
n.step('Rule-based baseline','Pressure-change/flow-change robust deviations are learned from training data only. This rule is an interpretable comparison, not an official operating threshold.', '''
rule=WaterRule().fit(Xtrain)
rule_val=rule.predict_proba(Xval)[:,1]
rule_threshold,rule_thresholds=choose_threshold(yval,rule_val)
print('Validation rule threshold',rule_threshold)
''')
n.section(8,'Model comparisons and tuning','''Compare Logistic Regression, Random Forest and XGBoost against the prior and hydraulic-change rule. Train/validation/test roles are distinct. Tuning CV scores may be optimistic; final evaluation is independent.''')
classification_experiment(n,True)
n.section(9,'Final evaluation and detection delay','''Metrics apply only to released benchmark onset-window labels. False-positive rate means outside the recent-onset target window; it does not mean absence of all active leakage. Delays are measured from each held-out episode onset to the first hourly alert in its 24-hour target window. Misses are retained separately rather than assigned zero delay.''')
classification_evaluation(n)
n.step('Rule comparison and hourly trace','The learned winner remains the CV choice regardless of final comparison results.', '''
rule_test=rule.predict_proba(Xtest)[:,1]
comparison=pd.DataFrame([{'model':selected,**metrics},{'model':'Hydraulic change rule',**binary_metrics(ytest,rule_test,rule_threshold)}])
display(comparison);comparison.to_csv(OUT/'final_comparison.csv',index=False)
results=pd.DataFrame({'time':Xtest.index,'target':ytest.to_numpy(),'probability':ptest,'alert':ptest>=threshold})
results.to_csv(OUT/'test_predictions.csv',index=False)
results.set_index('time')[['target','probability']].iloc[:1500].plot(title='Beginning of final year: target and frozen prediction');plt.show()
''')
n.step('Event recovery and onset-to-alert delay','Report detected fraction plus delay among detected episodes; a small conditional delay can coexist with many misses.', '''
delays=[]
for r in events.itertuples():
    if r.onset.year!=2019:continue
    window=results[(results.time>=r.onset)&(results.time<r.window_end)]
    if len(window)<20:continue
    alerts=window[window.alert]
    delays.append({'event_id':r.event_id,'pipe':r.pipe,'onset':str(r.onset),'detected':len(alerts)>0,
                   'delay_hours':(alerts.time.iloc[0]-r.onset).total_seconds()/3600 if len(alerts) else np.nan})
delays=pd.DataFrame(delays);display(delays);delays.to_csv(OUT/'event_detection_delay.csv',index=False)
print('Event detection fraction',delays.detected.mean(),'Median detected delay hours',delays.delay_hours.median())
false=results[results.target.eq(0)].copy()
print('False alert hours outside onset target windows:',int(false.alert.sum()))
''')
n.section(10,'Error analysis and robustness','''Inspect time/season dependence and failures. Do not tune on these final outcomes. The absence of field labels, receipt times and verified municipal mapping prevents operational use.''')
n.step('Monthly error slices','Seasonality and changing leak scenarios may differ between 2018 and 2019.', '''
slices=[]
for month,indices in results.groupby(results.time.dt.month).groups.items():
    g=results.loc[indices];slices.append({'month':month,**binary_metrics(g.target,g.probability,threshold)})
slices=pd.DataFrame(slices);display(slices)
slices.plot(x='month',y=['precision','recall','F1'],marker='o',title='Final monthly target-window metrics');plt.show()
''')
n.step('Missing-sensor sensitivity','A controlled 20% current-sensor outage is explicitly artificial and must cause serving abstention later.', '''
probe={k:v.tail(24*12+1).copy() for k,v in measurements.items()}
last_hour=probe['Pressures'].index[probe['Pressures'].index.minute==0][-1]
probe['Pressures'].loc[last_hour,probe['Pressures'].columns[:10]]=np.nan
print('Injected missing pressure sensor count',probe['Pressures'].loc[last_hour].isna().sum())
''')
n.section(11,'Interpretability','''Feature importance and SHAP describe statistical associations in the benchmark. Pressure patterns are correlated; explanations do not identify the true leaking pipe or establish causation.''')
explanations(n)
n.section(12,'Export and validated inference','''Export the fitted model, preprocessing, threshold, units, ordered sensor IDs, feature recipe and source manifest. Unsupported network/unit contracts abstain; wrong sensor identity or timestamp alignment is rejected. Missing-current coverage above 10% abstains. No prediction can dispatch resources.''')
n.step('Save model, metadata and examples','All serialized objects are actually fitted and importable outside Jupyter.', '''
metadata={'component':'water_recent_leak_onset','version':'1.0.0','selected_model':selected,'threshold':threshold,'train_end':str(Xtrain.index.max()),
          'target':'new benchmark leak began in preceding 24h','synthetic_benchmark':True,'source_doi':'10.5281/zenodo.4017659','license':'CC BY 4.0',
          'units':UNITS,'metrics':metrics,'dispatch_allowed':False,'validation':'retrospective hourly benchmark; not official challenge evaluation',
          'versions':{p:importlib.metadata.version(p) for p in ['numpy','pandas','scikit-learn','xgboost','networkx']}}
bundle=WaterBundle(model,feature_names,{k:list(d.columns) for k,d in measurements.items()},threshold,metadata)
joblib.dump(bundle,OUT/'pipeline.joblib');write_json(OUT/'metadata.json',metadata)
loaded=joblib.load(OUT/'pipeline.joblib')
example={k:d.tail(24*12+1) for k,d in measurements.items()}
output=loaded.predict(example,UNITS,detected_at='2026-10-25T00:00:00Z')
assert output==bundle.predict(example,UNITS,detected_at='2026-10-25T00:00:00Z')
assert loaded.predict(probe,UNITS)['probability'] is None
assert loaded.predict(example,{'pressure':'psi'})['probability'] is None
print(json.dumps(output,indent=2));write_json(OUT/'example_prediction.json',output)
''')
n.section(13,'CivicFlux integration, findings and limitations','''The shared `src/civicflux/` architecture is reused. No CivicFlux FastAPI risk/approval schema was found in the workspace; the output is a versioned pure inference contract, not a claim of live API integration. The nominal water topology remains separate from synthetic cross-sector dependencies. Anomaly/fault evidence requires corroboration and verified sensor-to-asset mapping.

Important limitations: retrospective simulated benchmark, hourly rather than five-minute scoring, recent-onset target rather than universal active-fault detection, no localization, limited independent events, unknown operational latency and timezone, and no calibrated field effectiveness. Source receipt-time and actual municipal sensor/fault data are the next dependencies.''')
n.step('Actual final findings','All findings below are computed by this run; failures remain visible.', '''
print('CV-selected model',selected)
print('Final benchmark metrics',json.dumps(metrics,indent=2))
print('Detected onset episodes',int(delays.detected.sum()),'of',len(delays))
print('Network/sensor map',graph.number_of_nodes(),graph.number_of_edges(),{k:len(v.columns) for k,v in measurements.items()})
''')
n.save()
