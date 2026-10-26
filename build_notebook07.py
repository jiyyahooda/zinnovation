from notebook_builder import *
n=ResearchNotebook('07_Cascade_Risk_Analysis.ipynb','CivicFlux — ML-Based Cascade Risk Analysis')
n.section(1,'Objective and research boundary','''Predict whether a node that is operational at snapshot time will experience a **secondary disruption within the next 60 minutes**. Initial disrupted nodes are excluded from targets. There is no verified cross-sector municipal dependency topology or incident log in this workspace; the experiment uses explicitly synthetic dependency graphs and stochastic cascades.

The newly shared `src/civicflux/graph.py` also parses Notebook 06’s benchmark water topology. Physical pipe adjacency and civic service-dependency direction are distinct graph semantics. We reuse one graph module/serialization interface rather than inventing a disconnected backend. No real-city validity or dispatch authority is claimed.''')
n.step('Setup and reusable modules','The optional GraphSAGE experiment is omitted: these small synthetic graphs do not justify an additional deep-learning dependency.',SETUP+"\nfrom src.civicflux.graph import *\nfrom src.civicflux.cascade import *\nOUT=ROOT/'artifacts/cascade_risk/v1.0.0'\nOUT.mkdir(parents=True,exist_ok=True)\n")
n.section(2,'Graph provenance and dependency semantics','''Forty hypothetical nodes per graph: eight drainage assets, roads, water assets, pumps and facilities each. Directed edges mean upstream service provider → dependent asset. Examples: pump→water, pump→drainage, drainage→road, water→facility, road→facility and road→pump. Cycles are possible and meaningful in this illustrative dependency model.

Edge weights are sampled dependency-transmission factors in [0.2,0.85]; delay is 10, 20 or 30 minutes. Resilience and criticality are dimensionless sampled assumptions, not measured engineering capacity. Edges are neither verified municipal links nor calibrated probabilities.''')
n.step('Construct and inspect a reference graph','Graph attributes explicitly retain synthetic provenance and a version.', '''
g=synthetic_graph(100)
validate_graph(g)
node_table=pd.DataFrame([{'node':node,**d} for node,d in g.nodes(data=True)])
edge_table=pd.DataFrame([{'source':u,'target':v,**d} for u,v,d in g.edges(data=True)])
display(node_table.head(10));display(edge_table.head(10))
print('Directed',g.is_directed(),'nodes',len(g),'edges',g.number_of_edges(),'fingerprint',graph_fingerprint(g))
''')
n.step('Validate graph semantics','Reverse edge direction changes the causal dependency scenario and is not silently treated as equivalent.', '''
assert set(node_table.node_type)==set(NODE_TYPES)
assert edge_table.weight.between(0,1).all()
assert edge_table.delay_minutes.gt(0).all()
assert not list(nx.selfloop_edges(g))
print('Strongly connected component sizes',sorted(map(len,nx.strongly_connected_components(g)),reverse=True))
''')
n.section(3,'Graph EDA','''Topology, degree, centrality and dependency paths are known at the snapshot. Centrality summarizes graph position; it does not prove physical importance or calibrated hazard.''')
n.step('Network visualization','Colors identify node types. Arrows retain the direction of service dependency.', '''
pos=nx.spring_layout(g,seed=SEED)
colors={kind:sns.color_palette('tab10')[i] for i,kind in enumerate(NODE_TYPES)}
plt.figure(figsize=(13,9))
nx.draw_networkx_edges(g,pos,alpha=.25,arrows=True,arrowsize=10)
for kind in NODE_TYPES:
    nodes=[n for n,d in g.nodes(data=True) if d['node_type']==kind]
    nx.draw_networkx_nodes(g,pos,nodelist=nodes,node_color=[colors[kind]],node_size=180,label=kind)
nx.draw_networkx_labels(g,pos,font_size=6);plt.legend();plt.title('Synthetic civic dependency graph');plt.axis('off');plt.show()
''')
n.step('Degree and centrality distributions','Degree and betweenness expose bottleneck hypotheses, not measured real-world failure likelihood.', '''
node_table['in_degree']=node_table.node.map(dict(g.in_degree()))
node_table['out_degree']=node_table.node.map(dict(g.out_degree()))
node_table['betweenness']=node_table.node.map(nx.betweenness_centrality(g))
display(node_table.sort_values('betweenness',ascending=False).head(10))
fig,ax=plt.subplots(1,2,figsize=(12,4))
sns.boxplot(data=node_table,x='node_type',y='in_degree',ax=ax[0])
sns.barplot(data=node_table.groupby('node_type',as_index=False).betweenness.mean(),x='node_type',y='betweenness',ax=ax[1]);plt.tight_layout();plt.show()
''')
n.step('Edge weights and dependency-type matrix','These distributions expose the simulation assumptions that drive later labels.', '''
edge_table['from_type']=edge_table.source.map(dict(g.nodes(data='node_type')))
edge_table['to_type']=edge_table.target.map(dict(g.nodes(data='node_type')))
fig,ax=plt.subplots(1,2,figsize=(13,4))
sns.histplot(edge_table.weight,bins=20,ax=ax[0]);ax[0].set_title('Assumed dependency weights')
sns.heatmap(pd.crosstab(edge_table.from_type,edge_table.to_type),annot=True,fmt='d',ax=ax[1],cmap='Blues');plt.tight_layout();plt.show()
''')
n.section(4,'Reproducible cascade simulation','''An independent-cascade process begins with two externally specified primary disruptions. Each newly disrupted node attempts transmission once to each outgoing neighbor with probability `clip(edge_weight × event_load × (1 − target_resilience),0,1)`. Successful transmission arrives after the edge delay. The earliest arrival wins; no spontaneous failures, repairs or interventions occur.

The probability law is a documented scenario assumption. Sixty-minute secondary outcomes are generated only after origin features are frozen. No future failure times or random outcomes enter the model features.''')
n.step('One event and its time evolution','The deterministic NetworkX reachability baseline assumes every possible transmission succeeds; simulation adds uncertainty.', '''
initial=['pump_0','drainage_3'];load=1.1
future=simulate_event(g,initial,load,seed=42)
trace=pd.DataFrame({'node':list(future),'failure_minute':list(future.values())}).sort_values('failure_minute')
display(trace)
trace.groupby('failure_minute').size().cumsum().plot(marker='o',title='One simulated cascade trajectory',ylabel='Cumulative disrupted nodes');plt.show()
print('Rule reachable nodes',len(propagation_rule(g,initial)),'Actual simulated secondary',len(future)-len(initial))
''')
n.step('Visualize primary and secondary disruptions','This map shows generated outcomes, not observations of municipal failures.', '''
plt.figure(figsize=(12,8))
node_colors=['black' if node in initial else ('red' if node in future else 'lightgrey') for node in g]
nx.draw(g,pos,node_color=node_colors,node_size=160,with_labels=True,font_size=6,edge_color='lightgrey',arrows=True)
plt.title('Black: initial; red: simulated secondary; grey: operational at 60 min');plt.show()
''')
n.section(5,'Event dataset and coverage','''Generate six graph realizations and 90 distinct primary-disruption pairs per graph. Graphs 100–103 provide training, validation and new-event tests; graphs 104–105 are wholly held out and use heavier load ranges. Repeated nodes within one event are dependent and must stay in one split.''')
n.step('Generate and audit labeled scenarios','Synthetic provenance, event IDs and graph IDs remain attached for grouping and audit, but IDs are excluded from predictors.', '''
data,graphs,manifest=generate_cascades(SEED)
display(data.head());display(data.groupby(['period','node_type']).target.agg(['count','mean']))
print('Rows',len(data),'events',data.event_id.nunique(),'graphs',len(graphs),'nulls outside failure-time audit',data.drop(columns='failure_minute').isna().sum().sum())
write_json(OUT/'scenario_manifest.json',manifest)
data.to_csv(OUT/'scenario_data.csv',index=False)
''')
n.step('Class balance and node-type differences','Failure-time NaN means no disruption in the 60-minute simulation horizon, not a missing measured incident report.', '''
fig,ax=plt.subplots(1,2,figsize=(12,4))
sns.countplot(data=data,x='period',hue='target',ax=ax[0]);ax[0].tick_params(axis='x',rotation=20)
sns.barplot(data=data.groupby(['period','node_type'],as_index=False).target.mean(),x='node_type',y='target',hue='period',ax=ax[1]);plt.tight_layout();plt.show()
''')
n.section(6,'Snapshot features and leakage prevention','''Features include node type, static criticality/resilience, degree/betweenness, event load, number/weight of already-disrupted predecessors, shortest hop distance from primary disruptions and fraction of ancestors already disrupted. All refer to the graph and status at origin. `failure_minute`, target, event ID, graph ID and future outcomes are forbidden inputs.''')
n.step('Feature schema and availability','Operational nodes only receive predictions; initially disrupted nodes cannot trivially inflate target accuracy.', '''
feature_names=FEATURES;numeric=NUMERIC;categorical=CATEGORICAL
assert not {'target','failure_minute','event_id','graph_id','node_id'}.intersection(feature_names)
first=manifest[0];origin=node_features(graphs[first['graph_id']],first['initial'],first['load'])
assert not set(origin.node_id).intersection(first['initial'])
pd.testing.assert_frame_equal(origin,node_features(graphs[first['graph_id']],first['initial'],first['load']))
write_json(OUT/'feature_schema.json',{'numeric':numeric,'categorical':categorical,'available_at':'origin graph/status only'})
display(origin.head())
''')
n.step('Feature distributions and correlations','Correlation may be created by topology; importance does not imply causal engineering benefit.', '''
train=data[data.period.eq('train')].copy()
fig,ax=plt.subplots(1,2,figsize=(13,4))
sns.boxplot(data=train,x='target',y='direct_exposure',ax=ax[0])
sns.heatmap(train[numeric].corr(),cmap='coolwarm',center=0,ax=ax[1]);plt.tight_layout();plt.show()
''')
n.section(7,'Event-grouped training strategy','''Use three GroupKFold folds grouped by complete event ID within development. Final testing reports unseen events on familiar graphs separately from unseen graphs under heavier loads. The same primary pair never appears in train/validation/test within a graph. There is no random node-row split.''')
n.step('Construct and verify event groups','Model selection sees only development events; threshold selection uses separate validation events.', '''
val=data[data.period.eq('validation')].copy();test=data[data.period.str.startswith('test')].copy()
Xtrain,ytrain=train[feature_names],train.target
Xval,yval=val[feature_names],val.target
Xtest,ytest=test[feature_names],test.target
folds=list(GroupKFold(n_splits=3).split(Xtrain,ytrain,groups=train.event_id))
for tr,va in folds:assert not set(train.iloc[tr].event_id)&set(train.iloc[va].event_id)
assert not set(train.event_id)&set(test.event_id)
assert not set(train.graph_id)&set(test[test.period.eq('test_unseen_graph')].graph_id)
print('Train/validation/test rows',len(train),len(val),len(test))
''')
n.step('NetworkX rule propagation baseline','Directed delay-limited reachability is conservative because it ignores failed transmission and resilience.', '''
lookup={r['event_id']:r for r in manifest}
rule_scores=[]
for event,group in test.groupby('event_id',sort=False):
    r=lookup[event];reach=propagation_rule(graphs[r['graph_id']],r['initial'])
    rule_scores.extend((idx,float(node in reach)) for idx,node in zip(group.index,group.node_id))
rule_scores=pd.Series(dict(rule_scores)).reindex(test.index)
print('Rule final coverage',rule_scores.mean())
''')
n.section(8,'Model comparison and hyperparameter analysis','''Compare a prior baseline, Logistic Regression and XGBoost. NetworkX propagation remains an external deterministic baseline. Tuning and threshold selection use grouped development and validation data; no automatic dispatch action is coupled to the classifier.''')
classification_experiment(n,False)
n.section(9,'Final generalization and calibration','''Report unseen disruption events and unseen graph/load conditions separately. The pooled metric can obscure a failure on new topology. All metrics concern simulation-generated labels.''')
classification_evaluation(n)
n.step('Baseline and domain-shift comparisons','Final results never change the already locked model choice.', '''
comparison=pd.DataFrame([{'method':selected,**metrics},{'method':'NetworkX reachability',**binary_metrics(ytest,rule_scores,.5)}])
display(comparison);comparison.to_csv(OUT/'final_comparison.csv',index=False)
results=test[['node_id','node_type','event_id','graph_id','period','target','failure_minute']].copy();results['probability']=ptest;results['predicted']=ptest>=threshold
results.to_csv(OUT/'test_predictions.csv',index=False)
slices=pd.DataFrame([{'split':name,**binary_metrics(z.target,z.probability,threshold)} for name,z in results.groupby('period')])
display(slices);slices.to_csv(OUT/'generalization_slices.csv',index=False)
''')
n.step('Per-node-type errors','Critical facilities can have different exposure and error rates than pumps or roads.', '''
types=pd.DataFrame([{'node_type':kind,**binary_metrics(z.target,z.probability,threshold)} for kind,z in results.groupby('node_type')])
display(types);types.plot.bar(x='node_type',y=['precision','recall','F1'],title='Final metrics by node type');plt.tight_layout();plt.show()
types.to_csv(OUT/'node_type_metrics.csv',index=False)
''')
n.section(10,'Error cases and sensitivity','''Inspect false positives/negatives and controlled load shifts. Learned risks need not obey every monotonic physical expectation; this simulator is not a calibrated infrastructure model.''')
n.step('Inspect incorrect node predictions','An apparent false positive can be a plausible stochastic pathway that simply did not occur in that simulation draw.', '''
wrong=results[results.predicted!=results.target]
display(wrong.sort_values('probability',ascending=False).head(12))
print('Incorrect node predictions',len(wrong),'from',results.event_id.nunique(),'independent final events')
''')
n.step('Risk sensitivity to load','Use the same graph/initial disruptions while changing only a declared scenario input. No labels are changed to flatter a model.', '''
sensitivity=[]
for load_value in [.5,.75,1.,1.25,1.5]:
    frame=node_features(g,initial,load_value)
    sensitivity.append({'load':load_value,'mean_risk':model.predict_proba(frame[feature_names])[:,1].mean()})
sensitivity=pd.DataFrame(sensitivity);display(sensitivity)
sensitivity.plot(x='load',y='mean_risk',marker='o',title='Learned mean risk under load sensitivity');plt.show()
''')
n.section(11,'Explainability','''Associations reflect the simulator and graph-feature construction. No SHAP feature contribution is an intervention effect.''')
explanations(n)
n.section(12,'Versioned export and inference validation','''Reuse the shared graph serialization and `src/civicflux/` component namespace. Unsupported node types, invalid edges, unknown initial nodes, out-of-range load and naive snapshot timestamps are rejected. Inference returns only operational nodes and has no graph mutation or dispatch side effect.''')
n.step('Export fitted model and graph configurations','The graph artifact records every sampled dependency assumption, making the scenario reproducible.', '''
metadata={'component':'cascade_risk','version':'1.0.0','selected_model':selected,'threshold':threshold,'horizon_minutes':60,'synthetic':True,'research_only':True,
          'metrics':metrics,'training_graphs':sorted(train.graph_id.unique()),'dispatch_allowed':False,'label':'secondary disruption by +60 min',
          'limitations':['Synthetic dependency weights','No verified municipal graph','No real cascade labels','Stochastic labels and event dependence']}
write_json(OUT/'metadata.json',metadata)
write_json(OUT/'graph_configurations.json',{key:graph_config(value) for key,value in graphs.items()})
bundle=CascadeBundle(model,threshold,metadata);joblib.dump(bundle,OUT/'pipeline.joblib')
loaded=joblib.load(OUT/'pipeline.joblib')
output=loaded.predict(g,initial,1.1,'2026-10-25T00:00:00Z')
assert output==bundle.predict(g,initial,1.1,'2026-10-25T00:00:00Z')
assert graph_fingerprint(from_config(graph_config(g)))==graph_fingerprint(g)
write_json(OUT/'example_prediction.json',output)
display(pd.DataFrame(output['nodes']).head())
''')
n.section(13,'CivicFlux integration and conclusions','''The component exports node-level risk with a 60-minute horizon, graph fingerprint, provenance, version and warnings. The current workspace has no live CivicFlux graph API/approval schema; integration is a reusable pure contract, not fabricated backend wiring. It shares graph representation with the water topology reader and will supply hypothetical node/criticality context to Notebook 08.

Before field use, obtain a verified dependency graph, measured weights/delays, incident timelines and restoration data; validate across future incidents and cities; calibrate probabilities; retain independent corroboration and approval gates. Predictions must not automatically allocate or dispatch resources.''')
n.step('Actual results summary','These values are produced by the executed experiment, not assumed accuracy.', '''
print('Selected',selected,'events',data.event_id.nunique(),'rows',len(data))
print(json.dumps(metrics,indent=2));display(slices)
''')
n.save()
