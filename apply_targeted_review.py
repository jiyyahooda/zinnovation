"""Apply small versioned review deltas; preserve original EDA and working components.

Run after the original per-notebook builder if intentionally regenerating source.
A review appendix is tagged so reapplying this file is idempotent.
"""
from pathlib import Path
import shutil,textwrap
import nbformat as nb
ROOT=Path(__file__).resolve().parent
TAG='civicflux-targeted-review'

def md(s):
    c=nb.v4.new_markdown_cell(textwrap.dedent(s).strip());c.metadata['tags']=[TAG];return c

def code(s):
    c=nb.v4.new_code_cell(textwrap.dedent(s).strip());c.metadata['tags']=[TAG];return c

def load(prefix):
    p=next((ROOT/'notebooks').glob(prefix+'*.ipynb'))
    backup=ROOT/'reports/targeted_review/original_notebooks'/p.name
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(p,backup)
    b=nb.read(p,as_version=4);b.cells=[c for c in b.cells if TAG not in c.metadata.get('tags',[])]
    for c in b.cells:
        if c.cell_type=='code':c.source=c.source.replace('v1.0.0','v1.1.0').replace("'version':'1.0.0'","'version':'1.1.0'")
    return p,b

def save(p,b):nb.write(b,p);print(p.name,len(b.cells),'cells')

p,b=load('06')
for c in b.cells:
    if c.cell_type=='code' and 'OUT=ROOT' in c.source and 'select_score_threshold as choose_threshold' not in c.source:
        c.source += '\nfrom src.civicflux.review import select_score_threshold as choose_threshold'
    if c.cell_type=='markdown' and 'highest threshold among tied validation' in c.source:
        c.source='### Validation-only threshold repair\n\nSearch the observed validation score range, including scores below 0.05. Maximize validation F1 and retain the highest threshold on a tie. This research alert rule has no operational authority. The original coarse grid excluded useful low-score operating points; none of its cutoffs detected a validation positive.'
b.cells += [md('''## Targeted review — operating points, events, false alarms and shift

The original 0.05–0.95 grid yielded zero validation F1 at every setting, then chose 0.95 by its tie rule. This is an inadequate search grid, not evidence that 0.95 is meaningful. We retain the same trained candidates and now examine actual validation-score operating points. Only validation labels determine thresholds; test labels diagnose the frozen policy.

Event recovery uses complete preceding-24-hour onset windows. One network-wide alert may overlap multiple leaks, so this is not localization or independent incident confirmation. False-alarm episodes are contiguous alert runs with no positive target hour; false-alert hours are also reported because a long false run can hide behind a small episode count.'''),code('''
from src.civicflux.review import SeasonalHydraulicRule,event_metrics,select_score_threshold
from src.civicflux.contracts import standardize
prior=float(ytrain.mean())
seasonal=SeasonalHydraulicRule().fit(Xtrain)
score_sets={'Selected ML':(pval,ptest),'Train prior':(np.repeat(prior,len(yval)),np.repeat(prior,len(ytest))),
 'Hydraulic changes':(rule.predict_proba(Xval)[:,1],rule.predict_proba(Xtest)[:,1]),
 'Seasonal directional residual':(seasonal.predict_proba(Xval)[:,1],seasonal.predict_proba(Xtest)[:,1])}
review_rows=[];event_rows=[];details=[]
review_predictions=pd.DataFrame({'time':Xtest.index,'target':ytest.to_numpy()})
for name,(validation_scores,test_scores) in score_sets.items():
    t,curve=select_score_threshold(yval,validation_scores)
    curve.to_csv(OUT/(name.replace(' ','_')+'_validation_thresholds.csv'),index=False)
    review_rows.append({'model':name,'threshold':t,'selection_period':'2018 validation',**binary_metrics(ytest,test_scores,t)})
    em,ed=event_metrics(Xtest.index,ytest,test_scores,t,events);event_rows.append({'model':name,**em});ed['model']=name;details.append(ed)
    review_predictions[name]=test_scores
baseline_review=pd.DataFrame(review_rows);event_review=pd.DataFrame(event_rows)
display(baseline_review);display(event_review)
baseline_review.to_csv(OUT/'baseline_comparison.csv',index=False);event_review.to_csv(OUT/'event_comparison.csv',index=False)
pd.concat(details).to_csv(OUT/'event_review_details.csv',index=False)
review_predictions.to_csv(OUT/'review_predictions.csv',index=False)
fig,ax=plt.subplots(1,2,figsize=(13,4))
baseline_review.plot.bar(x='model',y=['precision','recall'],ax=ax[0],rot=30)
event_review.plot.bar(x='model',y=['event_recall','false_alarm_episodes_per_30_days'],ax=ax[1],rot=30)
ax[1].set_title('Event recovery and false episodes (different units)');plt.tight_layout();plt.show()
'''),md('''### Temporal shift and uncertainty

Feature reference scales use training data only. The table reports median shifts in units of training standard deviation, not a causal explanation of failures. Score quantiles show whether thresholds extrapolate across periods. There are only two validation onsets, making threshold selection highly uncertain. The 2019 results were already inspected in the earlier study: this requested repair uses validation only, but cannot restore an untouched test set; a new future period is required for prospective confirmation. Retesting choices on 2019 would invalidate its role as the final evaluation.
'''),code('''
current=[c for c in feature_names if c.count('__')==1 and c.startswith(('pressure__','flow__','level__'))]
scale=Xtrain[current].std().clip(lower=.01)
shift=pd.DataFrame({'feature':current,'validation_median_shift':((Xval[current].median()-Xtrain[current].median())/scale).values,
 'test_median_shift':((Xtest[current].median()-Xtrain[current].median())/scale).values})
shift['abs_test_shift']=shift.test_median_shift.abs();display(shift.nlargest(12,'abs_test_shift'))
shift.to_csv(OUT/'temporal_distribution_shift.csv',index=False)
score_distribution=pd.DataFrame({name:pd.Series(scores).quantile([0,.1,.5,.9,.99,1]) for name,scores in
 [('training',model.predict_proba(Xtrain)[:,1]),('validation',pval),('2019 test',ptest)]})
display(score_distribution);score_distribution.to_csv(OUT/'score_distribution_by_period.csv')
shift.nlargest(12,'abs_test_shift').plot.barh(x='feature',y=['validation_median_shift','test_median_shift'],title='Median shift / training SD');plt.show()
print('Original test metrics:',json.loads((ROOT/'artifacts/water_network/v1.0.0/metrics.json').read_text()))
print('Repaired validation-only threshold:',threshold,'new metrics:',metrics)
print('Operational status: ABSTAIN. Benchmark onset scores do not establish municipal fault validity.')
metadata.update(version='1.1.0',operational_supported=False,operational_policy='abstain',validation_event_count=2)
bundle.metadata=metadata;joblib.dump(bundle,OUT/'pipeline.joblib');write_json(OUT/'metadata.json',metadata)
standardize('water_network',OUT,kind='supervised benchmark classifier',scope='L-TOWN simulated network only',units=UNITS,
 horizon='recent onset in preceding 24 hours',provenance='BattLeDIM CC BY 4.0 simulated SCADA',
 supported_inputs={'sensor_ids':bundle.sensors,'source_timezone':'unspecified naive','context':'24 hours five-minute history'},validation='weak temporal benchmark; operational abstention')
write_json(OUT/'example_prediction.json',bundle.predict(example,UNITS,detected_at='2026-10-25T00:00:00Z'))
assert bundle.predict(example,UNITS,purpose='operational')['probability'] is None
''')]
save(p,b)

p,b=load('07')
b.cells += [md('''## Targeted review — false positives, new dependencies and candidate routes

Retain the selected tuned Logistic Regression and the NetworkX reachability baseline. No model complexity or test-based threshold changes are introduced. Evaluate each held-out graph separately; the original test combined seen and unseen graphs. New dependency stress cases multiply weights or delays on copies of held-out graphs, generate new stochastic outcomes, and score the unchanged model. These are additional simulator diagnostics, not extra evidence of real infrastructure validity.

The selected snapshot features do not encode edge delays. Doubling delay therefore leaves its scores unchanged even when fewer simulated disruptions arrive within 60 minutes. The NetworkX baseline responds to delays; the stress table exposes this model limitation without adding an unvalidated estimator. Stress metrics pool event-node predictions across six events per held-out graph and three repetitions; per-event summaries are also retained.'''),code('''
from src.civicflux.cascade import dependency_trace
from src.civicflux.contracts import standardize
assert selected=='Logistic tuned'
error_data=test.copy();error_data['probability']=ptest;error_data['alert']=ptest>=threshold
error_data['false_positive']=(error_data.target.eq(0)&error_data.alert)
error_data['load_band']=pd.cut(error_data.load,[.5,1.,1.2,1.5],include_lowest=True).astype(str)
group_rows=[]
for column in ['graph_id','period','node_type','load_band']:
    for value,d in error_data.groupby(column,observed=True):
        group_rows.append({'dimension':column,'group':str(value),**binary_metrics(d.target,d.probability,threshold)})
error_slices=pd.DataFrame(group_rows);display(error_slices)
error_slices.to_csv(OUT/'false_positive_slices.csv',index=False)
error_slices[error_slices.dimension.eq('graph_id')].plot.bar(x='group',y=['precision','recall','false_positive_rate'],rot=25,title='Frozen model by held-out graph');plt.show()
stress_rows=[];stress_predictions=[]
unseen_manifest=pd.DataFrame([r for r in manifest if r['period']=='test_unseen_graph'])
for scenario in unseen_manifest.groupby('graph_id',sort=False).head(6).to_dict('records'):
    for condition,weight_scale,delay_scale in [('unchanged',1.,1.),('weaker_dependencies',.5,1.),('slower_dependencies',1.,2.)]:
        changed=graphs[scenario['graph_id']].copy()
        for u,v,d in changed.edges(data=True):d['weight']=min(1.,d['weight']*weight_scale);d['delay_minutes']*=delay_scale
        frame=node_features(changed,scenario['initial'],scenario['load']);scores=model.predict_proba(frame[feature_names])[:,1]
        for repeat in range(3):
            future=simulate_event(changed,scenario['initial'],scenario['load'],scenario['random_seed']+100000+repeat)
            truth=np.array([int(n in future) for n in frame.node_id]);reachable=propagation_rule(changed,scenario['initial'])
            for name,prob,t in [('Logistic (frozen)',scores,threshold),('NetworkX reachability',np.array([float(n in reachable) for n in frame.node_id]),.5)]:
                stress_rows.append({'event_id':scenario['event_id'],'repeat':repeat,'condition':condition,'method':name,**binary_metrics(truth,prob,t)})
                stress_predictions.extend([{'event_id':scenario['event_id'],'graph_id':scenario['graph_id'],'repeat':repeat,'condition':condition,'method':name,'node_id':node,'target':int(label),'probability':float(score),'threshold':t} for node,label,score in zip(frame.node_id,truth,prob)])
stress_detail=pd.DataFrame(stress_rows);stress_observations=pd.DataFrame(stress_predictions)
pooled=[]
for (condition,method),group in stress_observations.groupby(['condition','method']):
    pooled.append({'condition':condition,'method':method,'averaging':'pooled event-node observations',**binary_metrics(group.target,group.probability,group.threshold.iloc[0])})
stress_pooled=pd.DataFrame(pooled);display(stress_pooled)
stress_detail.to_csv(OUT/'dependency_condition_stress.csv',index=False)
stress_observations.to_csv(OUT/'dependency_condition_predictions.csv',index=False)
stress_pooled.to_csv(OUT/'dependency_condition_pooled.csv',index=False)
stress_pooled.pivot(index='condition',columns='method',values='false_positive_rate').plot.bar(title='Pooled false-positive rate under dependency changes',rot=20);plt.show()
'''),md('''### Explainable false-positive case

A route trace lists dependency direction, travel time, resilience and conditional edge factors. The product describes one possible route under the simulator; it is not the classifier score, a total path-union probability, a causal intervention effect, or proof that this route actually transmitted a disruption. A high-risk negative can arise because stochastic transmission did not occur.
'''),code('''
case=error_data[error_data.false_positive].sort_values('probability',ascending=False).iloc[0]
origin=lookup[case.event_id];case_graph=graphs[origin['graph_id']]
trace=dependency_trace(case_graph,origin['initial'],case.node_id,origin['load'])
trace.update(event_id=case.event_id,classifier_score=float(case.probability),observed_simulated_target=int(case.target))
write_json(OUT/'false_positive_trace.json',trace);display(trace)
path_nodes=set(n for route in trace['paths'] for n in route['path'])
subgraph=case_graph.subgraph(path_nodes);pos=nx.spring_layout(subgraph,seed=SEED)
plt.figure(figsize=(10,5));nx.draw(subgraph,pos,with_labels=True,node_color=['salmon' if n==case.node_id else 'lightblue' for n in subgraph],node_size=1000,font_size=8,arrows=True)
plt.title('Candidate dependency routes for a simulated false-positive');plt.show()
metadata.update(version='1.1.0',operational_supported=False)
bundle.metadata=metadata;joblib.dump(bundle,OUT/'pipeline.joblib');write_json(OUT/'metadata.json',metadata)
standardize('cascade_risk',OUT,kind='supervised simulator + graph rules',scope='synthetic civic dependency graphs',units='unitless simulated risk',horizon='60 minutes',
 provenance='seeded independent-cascade simulator',supported_inputs={'graph':'directed typed synthetic dependencies','load_range':[.5,1.5],'timestamp':'timezone-aware'},validation='unseen synthetic graph holdout; no municipal validity')
''')]
save(p,b)

p,b=load('08')
b.cells += [md('''## Targeted review — common artifact and inference contract

The working scoring function and CP-SAT/greedy comparisons are retained. The shared interface validates scenario units, resources and provenance and always leaves approval pending. Outcome success scores are explicitly ineligible for allocation. We add essential metadata and schema so the consolidated registry can describe this optimization algorithm alongside ML artifacts without presenting the optimizer as a trained model.'''),code('''
from src.civicflux.contracts import standardize
(OUT/'feature_schema.json').write_text(json.dumps({'candidate_fields':list(candidate_frame.columns),'resources':['budget','pumps','crew_hours'],
 'units':{'cost':'hypothetical INR','duration_hours':'hours','crew_hours':'hours','pumps_required':'count'},'untrusted_success_estimate_policy':'rejected by shared serving interface'},indent=2))
standardize('resource_optimization',OUT,kind='OR-Tools CP-SAT + feasible greedy baselines',scope='synthetic intervention scenarios',
 units={'budget':'hypothetical INR','crew_hours':'hours','pumps':'count'},horizon='one simultaneous allocation window',provenance='documented fictional costs, resources and policy factors',
 supported_inputs={'cases':'finite factors in [0,1], integer costs/pump counts','resources':'nonnegative capacities'},validation='scenario feasibility verified; no real resource inventory')
''')]
save(p,b)

p,b=load('09')
for c in b.cells:
    if c.cell_type!='code':continue
    c.source=c.source.replace('assert loaded.predict(test.iloc[0].to_dict())==pred','reloaded=loaded.predict(test.iloc[0].to_dict())\nfor key,value in pred.items():\n    if isinstance(value,float):assert np.isclose(reloaded[key],value,rtol=1e-12,atol=1e-12)\n    else:assert reloaded[key]==value')
    if 'thresholds=np.linspace(.05,.95,91)' in c.source:
        c.source="""from src.civicflux.review import select_score_threshold
pv=final.predict_proba(Xv)[:,1]
threshold,threshold_review=select_score_threshold(yv,pv,objective='balanced_accuracy')
threshold_review.to_csv(OUT/'success_validation_operating_points.csv',index=False)
threshold_review.plot(x='threshold',y=['F1','balanced_accuracy'],title='Validation discrimination and operating points');plt.show()
print('Research diagnostic threshold',threshold,'not an allocation decision')"""
    if 'def duration_pipeline(est)' in c.source:c.source=c.source.replace("return Pipeline([('preprocess',prep_duration)","return Pipeline([('preprocess',__import__('sklearn.base',fromlist=['clone']).clone(prep_duration))")
    if 'duration_best=min([r for r in rows' in c.source:
        c.source=c.source.replace("duration_best=min([r for r in rows if r['model']!='Train median baseline'],key=lambda z:z['MAE_hours'])['model']", "validation_duration={name:mean_absolute_error(vad.resolution_hours,np.maximum(0,np.expm1(est.predict(vad[FEATURES])))) for name,est in regressors.items()}\nduration_best=min(validation_duration,key=validation_duration.get)\nprint('Duration selection by validation MAE only',validation_duration)")
    if "'duration_log1p':True}" in c.source:c.source=c.source.replace("'duration_log1p':True}","'duration_log1p':True,'success_supported':False,'operational_supported':False}")
for c in b.cells:
    if c.cell_type=='markdown' and 'Select threshold by F1' in c.source:c.source='### Validation discrimination threshold\n\nThe original F1 search selected an almost-all-positive policy. Balanced accuracy now defines a diagnostic validation threshold. Success estimates remain unsupported for operational decisions regardless of this threshold.'
b.cells += [md('''## Targeted review — honest success baselines and simulation predictability

A low F1-selected cutoff can simply label everyone successful: its precision equals prevalence and its recall is one. Compare the classifier with a constant 0.5 score, the training success rate and per-intervention historical training rates. Also show the generator's latent success probability as an **oracle diagnostic only**, never as a fitted input or exported predictor. It bounds the mechanism's intrinsic predictability under this particular noisy simulation.

All post-intervention data remain outside predictors. The duration experiment is retained; its model is now chosen by validation MAE rather than test MAE. Its test period was already inspected previously, so these repaired results remain retrospective diagnostics. Uncompleted work is censored and excluded, so duration estimates apply only to the completed synthetic cohort.'''),code('''
from src.civicflux.contracts import standardize
from src.civicflux.research import binary_metrics
prior=float(ytr.mean());rate=train.groupby('intervention_type').target.mean()
historical=val.intervention_type.map(rate).fillna(prior).to_numpy();historical_test=test.intervention_type.map(rate).fillna(prior).to_numpy()
baseline_scores={'Selected classifier':(pv,pt),'Constant 0.5':(np.repeat(.5,len(yv)),np.repeat(.5,len(yt))),
 'Training success rate':(np.repeat(prior,len(yv)),np.repeat(prior,len(yt))),'Historical type rate':(historical,historical_test),
 'Generator oracle (not deployable)':(val.latent_success_probability.to_numpy(),test.latent_success_probability.to_numpy())}
rows_success=[];saved=pd.DataFrame({'intervention_id':test.intervention_id,'assignment_time':test.assignment_time,'target':yt,'probability':pt})
for name,(vs,ts) in baseline_scores.items():
    t,_=select_score_threshold(yv,vs,objective='balanced_accuracy')
    rows_success.append({'model':name,'threshold':t,**binary_metrics(yt,ts,t)})
    saved[name]=ts
success_comparison=pd.DataFrame(rows_success);display(success_comparison)
success_comparison.to_csv(OUT/'success_baseline_comparison.csv',index=False);saved.to_csv(OUT/'test_predictions.csv',index=False)
success_comparison.plot.bar(x='model',y=['PR_AUC_average_precision','ROC_AUC','Brier'],rot=25,title='Synthetic success: model, historical rates and oracle');plt.show()
duration_saved=pd.DataFrame({'intervention_id':ted.intervention_id,'target':ydt,'prediction':duration_pred,'baseline':base})
duration_saved.to_csv(OUT/'duration_test_predictions.csv',index=False)
(OUT/'duration_validation.json').write_text(json.dumps(validation_duration,indent=2))
print('Threshold may change classification tradeoffs; it cannot improve ROC-AUC or average precision.')
print('Success scores remain simulation diagnostics and are ineligible for resource allocation.')
metadata.update(version='1.1.0',success_supported=False,operational_supported=False,success_threshold=threshold,
 duration_selection='validation MAE; completed synthetic cohort only')
bundle.metadata=metadata;joblib.dump(bundle,OUT/'pipeline.joblib');(OUT/'metadata.json').write_text(json.dumps(metadata,indent=2,default=str))
standardize('intervention_outcomes',OUT,kind='synthetic success classifier + duration regressor',scope='synthetic intervention records only',
 units={'resolution':'hours','success_score':'unvalidated unitless simulation score'},horizon='post-completion synthetic outcome',
 provenance='seeded, confounded outcome generator; no real verification records',supported_inputs={'features':FEATURES,'out_of_scope':'real success estimates, causal effects and allocation'},
 validation='chronological synthetic holdout; unsupported success prediction, duration research only')
(OUT/'example_prediction.json').write_text(json.dumps(bundle.predict(test.iloc[0].to_dict()),indent=2))
assert bundle.predict(test.iloc[0].to_dict())['prediction_success_probability'] is None
assert bundle.predict(test.iloc[0].to_dict(),purpose='operational')['status']=='abstained'
''')]
save(p,b)
