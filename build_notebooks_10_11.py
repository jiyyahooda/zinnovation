"""Author evaluation/serving notebooks from saved artifacts; no model training."""
from notebook_builder import ResearchNotebook

SETUP='''
from pathlib import Path
import sys,json,platform,subprocess,copy
import numpy as np,pandas as pd,matplotlib.pyplot as plt,seaborn as sns
from IPython.display import display
ROOT=Path.cwd() if (Path.cwd()/'civicflux_core.py').exists() else Path.cwd().parent
sys.path.insert(0,str(ROOT))
from civicflux_core import sha256
from src.civicflux.serving import discover,directory_for,json_safe,SCOPES,UNITS,HORIZONS
from src.civicflux.validation import recompute_metrics,artifact_inventory,component_comparisons,registry_with_checks
sns.set_theme(style='whitegrid',palette='colorblind')
plt.rcParams.update({'figure.figsize':(11,4),'figure.dpi':110})
print('Python',platform.python_version(),'project',ROOT)
'''

n=ResearchNotebook('10_Model_Comparison_and_Validation.ipynb','CivicFlux — Model Comparison and Validation')
n.section(1,'Research objective and comparison rules','''Audit what the existing CivicFlux components actually achieve using their saved artifacts and predictions. No estimator is retrained here. A rainfall MAE in mm/day cannot be ranked against a traffic MAE in vehicles/hour or a flood classification F1. Instead, verify each task's arithmetic and compare with its own documented baseline.

Distinguish forecast research, synthetic surrogates, unsupervised measurement alerts, graph rules and constrained optimization. Technical inference readiness means that a fresh-process loading/prediction check passed; it does not establish municipal validity. The water model remains explicitly unsupported for operational fault prediction, and outcome success scores cannot drive allocation.''')
n.step('Reproducible read-only evaluation environment','The new report directory contains evaluation outputs only. Source notebooks 01–05 and legacy model files are not rewritten.',SETUP+'''
OUT=ROOT/'artifacts/model_validation/v1.0.0';OUT.mkdir(parents=True,exist_ok=True)
REPORTS=ROOT/'reports/integration'
''')
n.section(2,'Artifact discovery and component taxonomy','''Discover the latest versioned experiment for every expected component. Legacy forecasts have no semantic artifact version, so their registry version is honestly recorded as `legacy-unversioned`. Infrastructure anomaly detection stores a model card instead of metadata.json; the registry recognizes that existing architecture. Missing files remain missing rather than being generated as replacements.''')
n.step('Discover components and actual notebook coverage','The registry locates existing fitted artifacts, metadata, schema and model type. Optimization is not a trained ML model.', '''
registry=registry_with_checks(ROOT,REPORTS)
summary=pd.DataFrame(registry)
display(summary[['component','component_kind','version','selected_model','artifact','missing']])
import nbformat
notebook_rows=[]
for prefix in range(1,10):
    matches=list((ROOT/'notebooks').glob(f'{prefix:02d}_*.ipynb'))
    if not matches:notebook_rows.append({'notebook':prefix,'status':'missing'});continue
    book=nbformat.read(matches[0],as_version=4)
    errors=[o.get('ename') for c in book.cells if c.cell_type=='code' for o in c.get('outputs',[]) if o.output_type=='error']
    notebook_rows.append({'notebook':matches[0].name,'cells':len(book.cells),'executed_cells':sum(c.cell_type=='code' and c.execution_count is not None for c in book.cells),'error_outputs':len(errors)})
notebook_inventory=pd.DataFrame(notebook_rows);display(notebook_inventory)
notebook_inventory.to_csv(OUT/'notebook_inventory.csv',index=False)
''')
n.step('Inventory every component artifact and its fingerprint','Hashes make later changes visible and keep old v1.0.0 experiments distinct from the targeted v1.1.0 review. Generated evaluation reports are excluded to avoid self-referential hashes.', '''
inventory=artifact_inventory(ROOT);display(inventory.head(20))
display(inventory.groupby('suffix').agg(files=('path','size'),total_bytes=('bytes','sum')))
inventory.to_csv(OUT/'artifact_inventory.csv',index=False)
inventory.groupby('suffix')['bytes'].sum().sort_values().plot.barh(title='Artifact storage by file type');plt.xlabel('Bytes');plt.show()
''')
n.section(3,'Dataset provenance and geographic support','''Rainfall uses a Delhi state aggregate. AQI is a publisher-described Delhi aggregate with incomplete source units and station lineage. Traffic junctions lack a city, coordinates and timezone. These are distinct entities and cannot be joined on a city name. BattLeDIM/L-TOWN is simulated; cascade, drainage and outcome experiments are synthetic. The optimizer receives hypothetical costs, inventory and policy proxies.

A high score on synthetic data measures behavior under the stated generator. It is not measured accuracy on Delhi equipment failures, flood incidents, civic cascades or intervention success.''')
n.step('Make scope, provenance and horizon visible','The matrix preserves uncertainty in provenance rather than labeling all downloaded data verified real.', '''
provenance=summary[['component','geographic_scope','units','horizon','provenance','validation_status','simulation_only']].copy()
display(provenance);provenance.to_csv(OUT/'provenance_and_scope.csv',index=False)
status_counts=summary.assign(source_group=np.where(summary.simulation_only,'simulation/benchmark only','observational lineage requires review')).source_group.value_counts()
status_counts.plot.bar(title='Evidence classes of the nine research components',rot=20);plt.ylabel('Components');plt.show()
''')
n.section(4,'Validation design and information availability','''Forecasts use chronological development, calibration and final periods with horizon purging; no random future/past shuffle. Water uses 2018 training/validation and 2019 testing, with onset-window boundary exclusions. Cascade splits independent event groups and holds out complete graph seeds, though all labels still follow the same simulator family. Outcomes split assignment time; post-completion and verification fields are forbidden as predictors.

The targeted review repairs water threshold coverage, retains cascade Logistic Regression, and moves duration selection from test to validation. Test-based diagnostics do not authorize another selection round.''')
n.step('Inspect existing split and event records','Print the stored designs, not an invented uniform cross-validation claim.', '''
for component,filename in [('rainfall','split_boundaries.csv'),('aqi','split_boundaries.csv'),('traffic','split_boundaries.csv'),('flood','splits.csv'),('water_network','splits.csv')]:
    path=directory_for(ROOT,component)/filename
    print(component);display(pd.read_csv(path) if path.exists() else pd.DataFrame({'warning':['split file unavailable']}))
validation_notes=pd.DataFrame([
 ('rainfall/aqi/traffic','chronological, purged horizon','source latency and lineage unverified'),
 ('flood','forcing-date grouped chronological','uncalibrated synthetic hydrology'),
 ('anomaly','historical fit, later observations and injection fixtures','no verified equipment-fault labels'),
 ('water','2018 train/validation; 2019 test','only two validation onsets; temporal shift'),
 ('cascade','event grouped; unseen graph seeds','same synthetic mechanism family'),
 ('optimizer','identical hard constraints across methods','synthetic costs and equity/environment assumptions'),
 ('outcomes','chronological assignment; validation-only duration choice','synthetic noisy, confounded and completion-selected')],columns=['component','design','limitation'])
display(validation_notes);validation_notes.to_csv(OUT/'validation_design.csv',index=False)
''')
n.section(5,'Recompute metrics from saved predictions','''Recompute applicable regression and classification metrics from labels and scores already saved by earlier notebooks. Reported values are compared with a small numerical tolerance for CSV serialization. Persistence reproduces the original training-mean fallback when a current observation is missing; it does not use test-label information.

Flood exports calibrated probabilities but not raw probabilities. Its raw Brier score cannot be recomputed from that file, and is explicitly marked unavailable. No missing metric is fabricated.''')
n.step('Arithmetic consistency audit','A mismatch is a reportable finding. This notebook will not silently replace a reported metric.', '''
metric_checks,forecast_baselines=recompute_metrics(ROOT)
display(metric_checks);display(metric_checks[metric_checks.status.ne('consistent')])
metric_checks.to_csv(OUT/'metric_consistency.csv',index=False)
forecast_baselines.to_csv(OUT/'forecast_baselines.csv',index=False)
print('Consistent:',int(metric_checks.status.eq('consistent').sum()),'mismatches:',int(metric_checks.status.eq('MISMATCH').sum()))
assert not metric_checks.status.eq('MISMATCH').any(),'Investigate actual saved-metric inconsistencies'
''')
n.section(6,'Forecasts versus their own baselines','''Compare a forecast with persistence on exactly the same task, units and test rows. Positive MAE skill means improvement over that task's persistence baseline. It does not imply an operational benefit and is not a cross-domain ranking. Current measurements are assumed available at the origin; real reporting delay may reduce achievable skill.''')
n.step('Separate unit-specific forecast panels','Each panel uses its own physical units and axis. The dimensionless skill chart compares relative baseline improvement only.', '''
display(forecast_baselines)
fig,axes=plt.subplots(1,3,figsize=(15,4))
for ax,row in zip(axes,forecast_baselines.itertuples()):
    ax.bar(['Persistence','Selected'],[row.baseline_MAE,row.model_MAE]);ax.set_title(row.component);ax.set_ylabel('MAE: '+row.units)
plt.tight_layout();plt.show()
forecast_baselines.set_index('component').MAE_skill.plot.bar(title='Task-specific relative MAE improvement over persistence',rot=0);plt.axhline(0,color='black');plt.ylabel('1 − model MAE / own baseline MAE');plt.show()
''')
n.step('Inspect uncertainty coverage and extreme errors','Intervals are pooled calibration residual bands. Observed marginal coverage does not guarantee conditional coverage for rare extreme events.', '''
interval_rows=[]
for component in ['rainfall','aqi','traffic']:
    p=pd.read_csv(directory_for(ROOT,component)/'test_predictions.csv')
    if {'lower','upper'}.issubset(p.columns):
        covered=p.target.between(p.lower,p.upper)
        extreme=p.target>=p.target.quantile(.95)
        interval_rows.append({'component':component,'n':len(p),'coverage_90':float(covered.mean()),'extreme_95_coverage':float(covered[extreme].mean()),'mean_width':float((p.upper-p.lower).mean()),'extreme_n':int(extreme.sum())})
intervals=pd.DataFrame(interval_rows);display(intervals);intervals.to_csv(OUT/'interval_coverage.csv',index=False)
intervals.plot.bar(x='component',y=['coverage_90','extreme_95_coverage'],rot=0,title='Marginal and extreme-tail interval coverage');plt.axhline(.9,color='black',ls='--');plt.show()
''')
n.section(7,'Classification, graph rules and weak alert policies','''Each classification comparison has its own target and population. Flood scores mimic a drainage simulator. Water scores detect recent simulated onsets with high false-alert burden. Cascade scores emulate a stochastic dependency mechanism. Outcome success scores have weak discrimination and must not supply allocation weights. Do not combine their F1 or ROC-AUC values into a single winner.''')
n.step('Task-specific baseline tables','Every metric shown is read or recomputed from the existing experiment. Graph rules and historical-rate baselines keep their own semantics.', '''
comparisons=component_comparisons(ROOT)
for component,table in comparisons.items():
    print(component);display(table)
    table.to_csv(OUT/(component+'_baseline_comparison.csv'),index=False)
fig,axes=plt.subplots(2,2,figsize=(15,10))
for ax,component in zip(axes.flat,['flood','water_network','cascade_risk','intervention_outcomes']):
    table=comparisons[component];label='method' if 'method' in table else 'model'
    fields=[c for c in ['precision','recall','PR_AUC_average_precision'] if c in table]
    table.plot.bar(x=label,y=fields,ax=ax,rot=25,title=component+' — own benchmark only')
plt.tight_layout();plt.show()
''')
n.step('Water events and false-alarm duration','Always-alert baselines can recover every event while wasting almost every negative hour. Event recall therefore appears beside false-alert duration and episode counts.', '''
water_events=pd.read_csv(directory_for(ROOT,'water_network')/'event_comparison.csv');display(water_events)
water_events.to_csv(OUT/'water_event_review.csv',index=False)
fig,ax=plt.subplots(1,2,figsize=(13,4))
water_events.plot.bar(x='model',y='event_recall',ax=ax[0],rot=25)
water_events.plot.bar(x='model',y='false_alert_hours_per_negative_day',ax=ax[1],rot=25)
ax[0].set_title('Recent-onset window recovery');ax[1].set_title('False alert hours / negative day');plt.tight_layout();plt.show()
''')
n.section(8,'Anomaly detection and resource optimization','''Unlabeled unusual measurements cannot support real-fault precision or accuracy. Anomaly fixture recovery measures response to deliberately injected perturbations only. Resource allocation is an optimization problem: compare utility, capacity use and constraint satisfaction under shared synthetic constraints, without calling the solver a classifier.''')
n.step('Inspect anomaly evidence without inventing fault labels','The outputs preserve the separation between historical alert rates and injected anomaly recovery.', '''
for filename in ['test_alert_rates.csv','injected_summary.csv']:
    path=directory_for(ROOT,'infrastructure_anomaly')/filename
    print(filename);display(pd.read_csv(path))
print('Verified municipal fault precision/recall: unavailable; no real fault labels.')
optimizer=comparisons['resource_optimization'];display(optimizer[['scenario','method','status','utility','selected_count','budget_utilization']])
optimizer.pivot(index='scenario',columns='method',values='utility').plot.bar(title='Same-constraint synthetic allocation utility',rot=20);plt.show()
''')
n.section(9,'Calibration and resolution-time evidence','''Calibration curves assess how saved probabilities behave in their test populations. They cannot convert simulated labels into real municipal probabilities. Duration is evaluated among completed synthetic interventions only; incomplete work is censored, so selection and censoring limit interpretation.''')
n.step('Classifiers on their own reliability diagrams','The diagonal is a within-population reference, not operational certification.', '''
from sklearn.calibration import calibration_curve
fig,axes=plt.subplots(2,2,figsize=(12,9))
for ax,component in zip(axes.flat,['flood','water_network','cascade_risk','intervention_outcomes']):
    table=pd.read_csv(directory_for(ROOT,component)/'test_predictions.csv')
    actual,predicted=calibration_curve(table.target,table.probability,n_bins=8,strategy='quantile')
    ax.plot(predicted,actual,'o-');ax.plot([0,1],[0,1],'k--');ax.set(title=component,xlabel='Saved score',ylabel='Observed target rate')
plt.tight_layout();plt.show()
duration=pd.read_csv(directory_for(ROOT,'intervention_outcomes')/'duration_comparison.csv');display(duration)
duration.plot.bar(x='model',y='MAE_hours',rot=20,title='Completed synthetic jobs: resolution-time MAE');plt.ylabel('Hours');plt.show()
''')
n.section(10,'Artifact and serving readiness matrix','''A file existing on disk is insufficient for backend readiness. Fresh-process inference and negative input checks are required. A passing result for synthetic components is classified as simulation/demo only. A technical research-inference result for rainfall, AQI, traffic or anomaly detection still requires source lineage, latency and field validation.

The fresh-process reports are created by Notebook 11. If they do not exist yet or artifact/interface hashes changed, readiness stays Not ready until those checks run.''')
n.step('Readiness based on evidence, not a manual claim','This matrix makes the remaining scope restrictions visible.', '''
registry=registry_with_checks(ROOT,REPORTS);summary=pd.DataFrame(registry)
readiness=pd.DataFrame({'component':summary.component,'artifact_present':summary.artifact.notna() | summary.component.eq('resource_optimization'),
 'schema_present':summary.feature_schema.notna(),'fresh_process_passed':summary.readiness.ne('Not ready'),'observed_validation_claim':False,
 'operational_authority':False,'simulation_only':summary.simulation_only})
display(summary[['component','readiness','readiness_reason','validation_status']]);display(readiness)
sns.heatmap(readiness.set_index('component').astype(int),annot=True,vmin=0,vmax=1,cmap='Blues',cbar=False);plt.title('Technical checks and limits (1=yes, 0=no)');plt.xticks(rotation=30,ha='right');plt.tight_layout();plt.show()
readiness.to_csv(OUT/'readiness_matrix.csv',index=False)
''')
n.section(11,'Schema compatibility and missing evidence','''The shared adapter validates raw input contracts before invoking the existing bundles. Scope, horizon, units, known entities and explicit historical/simulation clocks must agree. Unknown geographic mapping is not fixed by silently joining datasets. Essential standardized metadata for reviewed components is stored beside versioned artifacts; legacy artifacts remain unchanged.''')
n.step('Validate the reviewed metadata and schemas','Only essential fields are required. Raw flood scores are an acknowledged export limitation, and live city topology/outcome records remain unavailable.', '''
required={'contract_version','component','artifact_version','component_kind','geographic_scope','units','horizon','provenance','supported_inputs','validation_status','operational_supported'}
for component in ['water_network','cascade_risk','resource_optimization','intervention_outcomes']:
    meta=json.loads((directory_for(ROOT,component)/'standard_metadata.json').read_text())
    assert required.issubset(meta),(component,required-set(meta))
    assert meta['operational_supported'] is False
missing=pd.DataFrame([{'component':r['component'],'missing_files':str(r['missing']),'geographic_mapping':'unverified for municipal graph','operational_validation':False} for r in registry])
display(missing);missing.to_csv(OUT/'missing_and_incompatible.csv',index=False)
''')
n.section(12,'Export the consolidated research registry','''The registry records artifact locations, schema paths, identity, version, support scope, horizon, units, validation status and evidence for technical readiness. It does not create missing estimators or rank incompatible tasks. Metadata and metrics are exported as reports for a future thin FastAPI route.''')
n.step('Save registry and evaluation report','JSON exports reject nonfinite numbers through the shared serializer.', '''
(OUT/'model_registry.json').write_text(json.dumps(json_safe(registry),indent=2,allow_nan=False))
(OUT/'metadata.json').write_text(json.dumps({'component':'model_validation_report','version':'1.0.0','retrained_models':0,'components':len(registry),
 'metric_mismatches':int(metric_checks.status.eq('MISMATCH').sum()),'unavailable_recomputations':int(metric_checks.status.ne('consistent').sum()),
 'limitations':['raw flood probabilities were not exported','no verified municipal topology or outcomes','research readiness is not operational validation']},indent=2))
print('Registry:',OUT/'model_registry.json')
''')
n.section(13,'Conclusions and next validation','''Read task baselines and uncertainty together. Repaired thresholds change alert tradeoffs, not discrimination. Water still has excessive false alarms. Cascade performance is simulator-specific and degrades across dependency conditions. Outcome success discrimination remains weak; its latent oracle is a diagnostic, never a deployable feature. Resolution estimates remain conditional on synthetic completion.

The supported next step is controlled research inference through the shared adapter, not deployment as a source of operational municipal facts. Representative measured incidents, verified asset mappings, known sensor units/clocks, independent outcome verification and prospective validation remain necessary.''')
n.step('Actual audit findings','Results below are read from the files evaluated in this run.', '''
print('Components',len(registry),'metric mismatches',int(metric_checks.status.eq('MISMATCH').sum()))
print('Unavailable recomputations:');display(metric_checks[metric_checks.status.ne('consistent')])
display(summary[['component','readiness']])
''')
n.save()

n=ResearchNotebook('11_End_to_End_CivicFlux.ipynb','CivicFlux — End-to-End Prediction and Decision Pipeline')
n.section(1,'Research workflow and decision boundaries','''Demonstrate saved-artifact loading, supported predictions and bounded decision support without training models. The conceptual sequence is historical data → validation → causal features → supported research prediction → compatible infrastructure evidence → synthetic dependency analysis → transparent scoring → feasible allocation → human review → independent outcome verification.

Actual datasets have incompatible spatial identities. Delhi aggregate forecasts, unlocated traffic junctions and simulated L-TOWN sensors cannot be fused into one asset graph. The notebook shows those supported forecast lanes separately, then runs the complete decision sequence on a clearly identified synthetic graph with matching candidate assets. Weak success or onset scores never become operational facts.''')
n.step('Setup and existing interfaces','Reuse the saved models, graph module, OR-Tools solver and verification helper. No alternate serving framework is introduced.',SETUP+'''
from src.civicflux.runtime import research_environment
from src.civicflux.serving import serve
from src.civicflux.integration import fixture,negative_requests,scenario_pipeline,review_proposal,compatible_graph_evidence
OUT=ROOT/'artifacts/end_to_end/v1.0.0';OUT.mkdir(parents=True,exist_ok=True)
CHECKS=ROOT/'reports/integration';CHECKS.mkdir(parents=True,exist_ok=True)
''')
n.section(2,'Discover exported models and research components','''Only saved fitted artifacts can be checked for serving. Notebook-only candidate estimators without exports are not invented or recreated. The anomaly artifact includes multiple registered sensor suites; the fresh-process worker also checks every supported suite. Optimization has configuration/results instead of a fitted estimator and is validated as an algorithm.''')
n.step('Inspect paths, input schemas and versions','Files are located using the same registry function as Notebook 10.', '''
entries=discover(ROOT);display(pd.DataFrame(entries)[['component','component_kind','version','artifact','feature_schema','missing']])
for row in entries:
    if row['missing']:print('Missing requirements:',row['component'],row['missing'])
''')
n.section(3,'Fresh Python process model-serving validation','''Launch a separate ordinary Python process for each component. The worker imports reusable modules and existing bundles, not notebook variables or Jupyter. It predicts on genuinely supported held-out historical or synthetic inputs, tests incompatible requests, and fingerprints the artifact and serving interface.

On this macOS workspace XGBoost needs the OpenMP library path already used by the notebook executor. `research_environment()` supplies that launch environment from the installed scikit-learn distribution. This is a documented runtime requirement for a FastAPI process too; a failed load produces Not ready, never a fabricated prediction.''')
n.step('Load, predict and challenge inputs outside Jupyter','The worker executes six or more negative cases per component. Runtime output and failures are retained in reports.', '''
process_rows=[]
for entry in entries:
    component=entry['component'];destination=CHECKS/(component+'.json')
    command=[sys.executable,str(ROOT/'scripts/check_research_inference.py'),component,'--output',str(destination)]
    completed=subprocess.run(command,cwd=ROOT,env=research_environment(),capture_output=True,text=True,timeout=180)
    row={'component':component,'return_code':completed.returncode,'stdout':completed.stdout.strip(),'stderr':completed.stderr[-5000:]}
    if destination.exists():
        report=json.loads(destination.read_text());row.update(passed=report['passed'],jupyter_imported=report['jupyter_imported'],
          positive_status=report['positive']['status'],negative_cases=len(report['negative_cases']),registered_sensor_suites=len(report.get('sensor_results',{})))
    else:row.update(passed=False,jupyter_imported=None,positive_status='not_ready',negative_cases=0,registered_sensor_suites=0)
    process_rows.append(row)
process_checks=pd.DataFrame(process_rows);display(process_checks)
process_checks.to_csv(OUT/'fresh_process_checks.csv',index=False)
assert process_checks.passed.all(),'Inspect retained worker failures before declaring readiness'
assert not process_checks.jupyter_imported.any()
''')
n.step('Inspect one actual response and registered detector coverage','The common envelope contains version, scope, provenance, validation limits, uncertainty if supported, and an explicit research status.', '''
responses={r['component']:json.loads((CHECKS/(r['component']+'.json')).read_text()) for r in entries}
display(responses['rainfall']['positive'])
print('Registered sensor suites checked:',list(responses['infrastructure_anomaly'].get('sensor_results',{})))
print('No Jupyter modules imported in workers:',not process_checks.jupyter_imported.any())
''')
n.section(4,'Input validation and abstention behavior','''The adapter validates scope, horizon and units before model loading; malformed payloads, missing observations, stale inputs and unsupported purposes abstain. Historical mode uses an explicit as-of clock and does not claim that an old observation is live. Unknown traffic timezones remain unknown source clocks. Synthetic experiments require synthetic provenance.

Water's operational fault output and intervention success probability are withheld. A technical simulation score remains available only within its documented research task.''')
n.step('Audit negative request results','An explicit abstention contains a reason and no prediction. No exception is converted into a plausible number.', '''
negative_rows=[]
for component,report in responses.items():
    for case,response in report['negative_cases'].items():
        negative_rows.append({'component':component,'case':case,'status':response['status'],'prediction_is_null':response['prediction'] is None,
          'reason':'; '.join(response['warnings'])[:500]})
negative_table=pd.DataFrame(negative_rows);display(negative_table)
negative_table.to_csv(OUT/'abstention_checks.csv',index=False)
assert negative_table.status.eq('abstained').all() and negative_table.prediction_is_null.all()
print('Water operational request:',responses['water_network']['negative_cases']['operational'])
print('Outcome research response:',responses['intervention_outcomes']['positive']['prediction'])
''')
n.section(5,'Supported historical forecasts and uncertainty','''Rainfall predicts the next Delhi state day; AQI predicts next-hour PM2.5 for the declared aggregate; traffic predicts next-hour vehicle counts for benchmark junction identities. The raw histories pass through the existing canonicalization, feature construction and fitted preprocessing. Intervals are pooled residual bands with no guarantee of conditional or live coverage.''')
n.step('Show actual forecast outputs in separate domains','These are historical research inferences, not live readings. Axes retain their task units.', '''
forecast_rows=[]
for component in ['rainfall','aqi','traffic']:
    response=responses[component]['positive'];record=response['prediction'][0]
    interval=response['uncertainty']['intervals'][0]
    forecast_rows.append({'component':component,'entity':record['entity'],'observation':record['time'],'target_time':record['target_time'],
     'prediction':record['prediction'],'lower_90':interval['lower_90'],'upper_90':interval['upper_90'],'units':response['units'],'scope':response['geographic_scope']})
forecasts=pd.DataFrame(forecast_rows);display(forecasts)
fig,axes=plt.subplots(1,3,figsize=(14,4))
for ax,row in zip(axes,forecasts.itertuples()):
    ax.errorbar([0],[row.prediction],yerr=[[row.prediction-row.lower_90],[row.upper_90-row.prediction]],fmt='o',capsize=7)
    ax.set(title=row.component,ylabel=row.units,xticks=[0],xticklabels=[row.target_time[:16]])
plt.tight_layout();plt.show();forecasts.to_csv(OUT/'historical_forecasts.csv',index=False)
''')
n.section(6,'Geographic, time and provenance compatibility','''A common city string cannot map an aggregate to a specific pump. The shared graph evidence checker requires an existing node, synthetic status, matching graph identity and exact graph fingerprint. Forecast units and horizons are not silently converted to asset disruption probabilities. Cross-domain bridges without verified spatial/temporal mapping abstain.''')
n.step('Demonstrate blocked and compatible evidence','The asset mapping check is exact for this seeded synthetic graph; it does not pretend to solve municipal geospatial matching.', '''
from src.civicflux.graph import from_config,graph_fingerprint
cascade_request=fixture('cascade_risk',ROOT);graph=from_config(cascade_request['graph'])
evidence={'synthetic':True,'graph_id':graph.graph['graph_id'],'graph_fingerprint':graph_fingerprint(graph),'node_id':'pump_0'}
compatibility=pd.DataFrame([
 {'connection':'same declared synthetic graph/node','compatible':compatible_graph_evidence(evidence,graph)},
 {'connection':'same node name, wrong graph fingerprint','compatible':compatible_graph_evidence({**evidence,'graph_fingerprint':'unverified'},graph)},
 {'connection':'Delhi forecast to synthetic pump','compatible':compatible_graph_evidence({'synthetic':False,'node_id':'pump_0'},graph)}])
display(compatibility);compatibility.to_csv(OUT/'mapping_checks.csv',index=False)
assert compatibility.compatible.tolist()==[True,False,False]
''')
n.section(7,'Synthetic infrastructure risk and cascade analysis','''Declare a hypothetical initial pump disruption independently of weak forecasts. The selected Logistic Regression and NetworkX directed propagation operate on the existing synthetic dependency graph. The graph's IDs and fingerprint match Notebook 08's scenario assets. Node risk is scenario evidence, not a confirmed failure.''')
n.step('Run the saved cascade bundle and visualize node scores','No retraining or graph replacement occurs. Colors show model scores on operational nodes; the initial disrupted node is excluded from the secondary-disruption target.', '''
scenario=scenario_pipeline(ROOT)
assert scenario['status']=='supported_simulation'
node_risk=pd.DataFrame(scenario['cascade']['prediction']);display(node_risk.sort_values('risk',ascending=False).head(15))
import networkx as nx
pos=nx.spring_layout(graph,seed=42);risk_map=node_risk.set_index('node_id').risk.to_dict()
plt.figure(figsize=(12,8));nx.draw_networkx_edges(graph,pos,alpha=.25,arrows=True)
points=nx.draw_networkx_nodes(graph,pos,node_color=[risk_map.get(node,1.) for node in graph],cmap='OrRd',vmin=0,vmax=1,node_size=180)
nx.draw_networkx_labels(graph,pos,font_size=6);plt.colorbar(points,label='Synthetic secondary-disruption score');plt.title('Declared synthetic outage and saved cascade inference');plt.axis('off');plt.show()
''')
n.step('Explain a candidate dependency route','Trace uses directions, travel times and conditional edge transmission factors. It is a candidate exposure mechanism, not a realized path or causal claim.', '''
from src.civicflux.cascade import dependency_trace,propagation_rule
node=node_risk.sort_values('risk',ascending=False).iloc[0].node_id
route=dependency_trace(graph,cascade_request['initial'],node,cascade_request['load'])
display(route)
reach=propagation_rule(graph,cascade_request['initial'])
print('NetworkX reachable operational nodes:',len(reach),'model review nodes:',int(node_risk.review.sum()))
(OUT/'cascade_route.json').write_text(json.dumps(json_safe(route),indent=2))
''')
n.section(8,'Sustainability scoring and resource scarcity','''Only compatible synthetic cascade scores enter hypothetical proposal factors. Urgency, service, costs, carbon and equity values retain their documented assumed provenance. Use the existing normalized scoring function and OR-Tools solver under shared budget/pump/crew limits. Success scores from Notebook 09 are explicitly rejected if supplied to allocation.''')
n.step('Review normal and scarce allocations and constraints','Compare the same synthetic cases with a smaller budget. The solver result is a proposal with no dispatch authority.', '''
from src.civicflux.optimization import assert_feasible
allocation_rows=[]
for item in scenario['allocations']:
    response=item['allocation'];assert response['status']=='supported_simulation'
    allocation=response['prediction'];assert_feasible(allocation['selected'],allocation['available'])
    allocation_rows.append({'scenario':item['scenario'],'status':allocation['status'],'utility':allocation['objective'],'selected':len(allocation['selected']),
        'budget_used':allocation['used']['budget'],'budget_available':allocation['available']['budget'],'pumps_used':allocation['used']['pumps'],
        'crew_hours_used':sum(allocation['used']['crew_hours'].values()),'solver_seconds':allocation['solver_seconds'],'dispatch_allowed':allocation['dispatch_allowed']})
allocations=pd.DataFrame(allocation_rows);display(allocations)
fig,axes=plt.subplots(1,3,figsize=(13,4))
for ax,column in zip(axes,['utility','selected','budget_used']):allocations.plot.bar(x='scenario',y=column,ax=ax,rot=15,legend=False)
plt.tight_layout();plt.show();allocations.to_csv(OUT/'allocation_summary.csv',index=False)
normal=scenario['allocations'][0]['allocation']['prediction']
display(pd.DataFrame(normal['selected'])[['case_id','node_id','urgency','cascade','environmental_benefit','equity_proxy','utility','cost','crew_type','duration_hours','pumps_required']])
''')
n.section(9,'Human review and audit records','''The existing optimizer requires human approval. No civic approval API or live dispatch system exists in this repository. A thin audit helper therefore records pending/deferred/rejected research proposals and cannot approve them. A fictional reviewer action below is visibly a synthetic walkthrough, not an actual human authorization.

Proposal, review, completion and outcome verification are distinct states. A high model score cannot approve work or confirm success.''')
n.step('Inspect pending proposals and an explicitly fictional deferral','The research helper rejects approval and dispatch instructions.', '''
review_records=[]
for item in scenario['allocations']:
    review_records += [item['review'],item['demonstration_review_record']]
display(pd.DataFrame(review_records))
try:review_proposal({'proposal_id':'SYNTHETIC-example'},decision='approve',reviewer='automated process')
except ValueError as error:print('Expected approval abstention:',error)
else:raise AssertionError('Research helper granted approval')
(OUT/'review_audit.json').write_text(json.dumps(review_records,indent=2))
''')
n.section(10,'Outcome recording and independent verification','''The outcome bundle can estimate research resolution time in its synthetic population, but exposes no operational success probability. Completed work is not verified success. Real outcome recording requires consistent timestamps, completion status, independent verifier and evidence. Synthetic rows cannot be promoted into real verified labels.''')
n.step('Show completion and verification remain distinct','The existing verification helper refuses synthetic promotion. This is the expected end of the demonstration.', '''
from src.civicflux.outcomes import validate_outcome_record,verify_outcome
records=pd.read_csv(directory_for(ROOT,'intervention_outcomes')/'synthetic_intervention_records.csv')
example=records[records.status.eq('completed')].iloc[0].to_dict()
validate_outcome_record(example)
display({'work_status':example['status'],'outcome_status':example['outcome_status'],'source_type':example['source_type']})
display(scenario['verification'])
assert scenario['verification']['status']=='abstained'
outcome_response=responses['intervention_outcomes']['positive'];assert outcome_response['prediction']['success_probability'] is None
print('Resolution estimate:',outcome_response['prediction']['research_resolution_hours'],'hours; synthetic completed-cohort research only')
''')
n.section(11,'Integration tests and honest readiness classifications','''Technical readiness is assigned only after fresh-process loading, compatible prediction and incompatible-input tests pass. Synthetic models remain Simulation/demo only even if technically functional. Weak water and outcome success predictions remain operationally unsupported. Research forecasts retain their geographic and source-quality restrictions.''')
n.step('Build the final evidence-based registry','Readiness checks also require matching artifact and serving-interface hashes, preventing stale reports from certifying changed files.', '''
registry=registry_with_checks(ROOT,CHECKS);readiness=pd.DataFrame(registry)
display(readiness[['component','readiness','readiness_reason','operational_supported']])
assert readiness.readiness.ne('Not ready').all(),'Some components require further loading/inference repair'
assert not readiness.operational_supported.any()
checks=pd.DataFrame({'component':process_checks.component,'fresh_process':process_checks.passed,'no_jupyter_dependency':~process_checks.jupyter_imported,
                    'negative_cases_abstain':process_checks.passed,'operational_authority':False})
sns.heatmap(checks.set_index('component').astype(int),annot=True,cbar=False,cmap='Blues',vmin=0,vmax=1);plt.title('Serving execution versus operational authority');plt.xticks(rotation=25,ha='right');plt.tight_layout();plt.show()
''')
n.step('Run the changed-behavior and integration tests','The suite checks causal features, threshold coverage, outcome suppression, provenance, constraints, serialization and metric consistency.', '''
result=subprocess.run([sys.executable,'-m','pytest','-q','tests'],cwd=ROOT,env=research_environment(),capture_output=True,text=True,timeout=180)
print(result.stdout);print(result.stderr)
(OUT/'tests.txt').write_text(result.stdout+'\\n'+result.stderr)
assert result.returncode==0,'Inspect the test report before claiming completion'
''')
n.section(12,'Export API-compatible research evidence','''Export the common registry, example responses, scenario allocations, audit trace and fresh-process summaries. A FastAPI route can call `src.civicflux.serving.serve(component, request, project_root)` directly. It returns JSON-compatible values and explicit abstentions; no web server is created here.

On macOS launch the serving process with `research_environment()` or an equivalent configured OpenMP path. Authenticating a real operator and implementing a real approval API remain application work; this research notebook has no authority to provide those decisions.''')
n.step('Save registry, responses and reproducible scenario reports','The new artifacts contain predictions and decisions already executed in this notebook, not assumed backend responses.', '''
exports={'model_registry.json':registry,'example_api_responses.json':{k:v['positive'] for k,v in responses.items()},'scenario_results.json':scenario,
         'audit_trace.json':scenario['audit_trace'],'metadata.json':{'component':'end_to_end_research_validation','version':'1.0.0','retrained_models':0,
             'fresh_process_components':len(registry),'operational_dispatch':False,'limitations':['no verified common municipal mapping','synthetic decisions and outcomes','weak fault/success policies abstain operationally','runtime OpenMP launch requirement']}}
for filename,payload in exports.items():(OUT/filename).write_text(json.dumps(json_safe(payload),indent=2,allow_nan=False))
print('Exports:',OUT)
''')
n.section(13,'Actual completion report and remaining limitations','''All supported paths must be read in their research context. Passing tests proves that the interfaces load and execute for supported fixtures, not that their measurements, probabilities or decisions are valid in a live city. The complete decision trace therefore uses declared synthetic incidents, aligned synthetic graph nodes and hypothetical resources. It ends at pending human review and refuses promotion of simulated outcomes to real verified success.

Remaining evidence includes measured local incidents, verified sensor clocks/units, geospatial asset mappings, actual inventories and independently audited outcomes. No additional estimator is trained merely to label these final evaluation notebooks as models.''')
n.step('Final per-component status','The table below is populated by actual fresh-process reports from this execution.', '''
display(readiness[['component','readiness','geographic_scope','validation_status']])
print('Fresh processes:',int(process_checks.passed.sum()),'negative requests:',int(process_checks.negative_cases.sum()),
      'registered anomaly suites:',int(process_checks.registered_sensor_suites.sum()))
print('Automatic dispatch:',scenario['automatic_dispatch'],'cross-scope bridge:',scenario['blocked_cross_scope_bridge']['status'])
''')
n.save()
