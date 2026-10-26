"""Source builder for only Notebooks 08 and 09; preserve all executed notebooks."""
from pathlib import Path
import sys,textwrap
import nbformat as nbf
ROOT=Path(__file__).resolve().parent

def make(name,title,description,cells):
 path=ROOT/'notebooks'/name
 if path.exists() and '--overwrite' not in sys.argv:raise SystemExit(f'Protecting existing {name}; use --overwrite deliberately.')
 book=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python (CivicFlux)','language':'python','name':'civicflux'},'language_info':{'name':'python','version':'3.13'}})
 nbf.write(book,path);print(path.name,len(cells),'cells')
def md(s):return nbf.v4.new_markdown_cell(textwrap.dedent(s).strip())
def code(s):return nbf.v4.new_code_cell(textwrap.dedent(s).strip())
def pair(cells,title,explain,source):cells += [md('### '+title+'\n\n'+textwrap.dedent(explain).strip()),code(textwrap.dedent(source).strip())]

# ---------------------------------------------------------------------------
# Notebook 08 — Optimize feasible research recommendations using existing graph.
# ---------------------------------------------------------------------------
a=[]
a.append(md('''# CivicFlux — Sustainability and Resource Optimization

**Notebook 08 · NetworkX topology review + OR-Tools resource allocation**

A reproducible decision-support experiment. BattLeDIM supplies one documented L-TOWN water graph, but the workspace has no municipal incident inventory, crew roster, intervention cost database, or resource optimizer. We reuse the existing graph parsers and represent resource decisions with a small pure CP-SAT component. The optimization inputs are explicitly synthetic; no recommendation is dispatched or approved automatically.'''))
a.append(md('''## 01. Research question and decision boundary

Given a finite set of hypothetical intervention proposals and a finite resource inventory, select a feasible set maximizing transparent weighted utility. This is a constrained selection model, not an ML model. It does not estimate the causal impact of interventions and does not define operational safety policy.

Compare OR-Tools CP-SAT with severity-first and utility-greedy baselines subject to the same budget, crew-hour and pump constraints. Test resource scarcity, conflicting priorities and weight sensitivity. Recommendations require human review.'''))
pair(a,'1.1 Reproducible setup','Use shared CivicFlux graph readers and the reusable versioned CP-SAT component. Every seed and score weight is saved.', '''
from pathlib import Path
import sys,json,time,platform,importlib.metadata
import numpy as np,pandas as pd,matplotlib.pyplot as plt,seaborn as sns
from IPython.display import display
ROOT=Path.cwd() if (Path.cwd()/'civicflux_core.py').exists() else Path.cwd().parent
sys.path.insert(0,str(ROOT))
from src.civicflux.graph import read_epanet,synthetic_graph,graph_fingerprint,NODE_TYPES
from src.civicflux.optimization import (DEFAULT_WEIGHTS,VERSION,validate_weights,score_intervention,
 solve_cpsat,greedy_allocate,assert_feasible)
from civicflux_core import sha256
sns.set_theme(style='whitegrid');SEED=42
OUT=ROOT/'artifacts'/'resource_optimization'/'v1.0.0';OUT.mkdir(parents=True,exist_ok=True)
print('Python',platform.python_version(),'NetworkX',importlib.metadata.version('networkx'),'OR-Tools',importlib.metadata.version('ortools'))
''')
pair(a,'1.2 Existing optimizer and approval-path audit','Repository inspection found no existing CivicFlux infrastructure optimizer, intervention database, or approval API. Nearby demo apps belong to unrelated domains. The new helper returns a plan and flags approval required; it has no dispatch or network capability.', '''
print('Optimization interface: src/civicflux/optimization.py')
print('Graph interface: src/civicflux/graph.py')
print('No verified civic crew/resource inventory or approval schema was found.')
''')
a.append(md('''## 02. Infrastructure graph and evidence

The L-TOWN EPANET file provides nominal hydraulic node/link topology for a benchmark network. It is not municipal Delhi data or a verified cross-sector drainage/road/pump/facility map. First visualize its real benchmark topology and derive centrality, keeping all dependency interpretation cautious. Then use the existing versioned `synthetic_graph` generator for the hypothetical multi-sector dependency example; its edge weights mean simulated service-dependency strength.'''))
pair(a,'2.1 Read and fingerprint supplied L-TOWN network','Node IDs and pipe lengths come from the checked source file. Their geographic coordinates are benchmark plotting coordinates, not a CivicFlux geographic join.', '''
water_path=ROOT/'data/raw/battledim/L-TOWN.inp'
water_graph=read_epanet(water_path)
water_fp=graph_fingerprint(water_graph)
print('L-TOWN nominal graph',water_graph.number_of_nodes(),'nodes',water_graph.number_of_edges(),'links')
print('Synthetic flag because the benchmark scenario/network is simulated:',water_graph.graph['synthetic'])
print('SHA256',sha256(water_path),'fingerprint',water_fp)
''')
pair(a,'2.2 Topology EDA','Connectivity and degree can help identify high-connectivity benchmark elements, but are not measured civic criticality.', '''
components=list(__import__('networkx').connected_components(water_graph))
print('Connected components',len(components),'largest',max(map(len,components)))
degree=pd.Series(dict(water_graph.degree()),name='degree')
display(degree.describe())
degree.value_counts().sort_index().plot.bar(title='L-TOWN node degree distribution',xlabel='Degree',ylabel='Nodes');plt.show()
''')
pair(a,'2.3 Visualize BattLeDIM L-TOWN reference topology','Use the supplied layout coordinates, pressure sensor placements and typed pipe/pump/reservoir nodes.', '''
import networkx as nx
pos=nx.get_node_attributes(water_graph,'pos')
fig,ax=plt.subplots(figsize=(11,8))
nx.draw_networkx_edges(water_graph,pos,ax=ax,alpha=.22,width=.45)
colors={'junction':'#4c78a8','reservoir':'#f58518','tank':'#e45756'}
for kind,color in colors.items():
    nodes=[n for n,d in water_graph.nodes(data=True) if d.get('node_type')==kind]
    nx.draw_networkx_nodes(water_graph,pos,nodelist=nodes,node_color=color,node_size=10 if kind=='junction' else 50,ax=ax,label=kind)
ax.legend();ax.set_title('BattLeDIM L-TOWN nominal water network');ax.axis('equal');plt.show()
''')
pair(a,'2.4 NetworkX centrality','Betweenness centrality is computed on the actual undirected hydraulic adjacency. It does not prove outage probability or system importance.', '''
bet=nx.betweenness_centrality(water_graph,weight='length',normalized=True)
centrality=pd.DataFrame({'node':list(bet),'betweenness':list(bet.values()),'degree':[water_graph.degree(n) for n in bet]})
display(centrality.nlargest(12,'betweenness'))
centrality.nlargest(20,'betweenness').sort_values('betweenness').plot.barh(x='node',y='betweenness',legend=False,title='High-betweenness benchmark nodes');plt.show()
''')
pair(a,'2.5 Explicitly hypothetical multi-sector service graph','Reuses the shared graph builder. Directed links mean service-provider node → dependent node. The topology is generated for illustration, not inferred from local geography.', '''
graph=synthetic_graph(seed=SEED,n_per_type=8)
assert graph.graph['synthetic'] is True
print(graph.number_of_nodes(),'hypothetical nodes;',graph.number_of_edges(),'directed dependency edges')
print(pd.Series(nx.get_node_attributes(graph,'node_type')).value_counts())
''')
pair(a,'2.6 Dependency weight and direction','Direction controls cascade interpretation. Weight is a declared synthetic probability-like service-dependency strength, not empirical failure transmission.', '''
edge_data=pd.DataFrame([{'provider_type':graph.nodes[u]['node_type'],'dependent_type':graph.nodes[v]['node_type'],'weight':d['weight'],'delay_minutes':d['delay_minutes']} for u,v,d in graph.edges(data=True)])
display(edge_data.groupby(['provider_type','dependent_type']).agg(edges=('weight','size'),mean_weight=('weight','mean')))
sns.histplot(edge_data.weight,bins=20);plt.title('Hypothetical dependency-edge weights');plt.xlabel('Assumed weight');plt.show()
''')
a.append(md('''## 03. Scenario inventory and provenance

Create proposals from hypothetical nodes in the synthetic graph. Severity, expected service improvement, cascade reach, equity proxy, environmental benefit, carbon burden, crew skill, job duration, pump use and monetary cost are generated under fixed distributions below. **The equity value is a randomized placeholder, not demographic or service-access data.** Carbon and cost coefficients are scenario assumptions, not life-cycle accounting or procurement quotations.
'''))
pair(a,'3.1 Generate synthetic intervention candidates','Four conflict/scarcity scenarios share the same candidate cases so resource feasibility and objective comparisons are interpretable.', '''
rng=np.random.default_rng(SEED)
node_list=list(graph.nodes(data=True))
node_importance=nx.betweenness_centrality(graph)
crew_map={'water':'water','pump':'water','drainage':'drain','road':'road','facility':'water'}
def make_cases(seed,n=30):
    r=np.random.default_rng(seed);rows=[]
    for i in range(n):
        node,d=node_list[i%len(node_list)]
        # A candidate is a plan under a synthetic scenario, not a real recommendation.
        rows.append({'case_id':f'S{seed}-C{i:02d}','node_id':node,'node_type':d['node_type'],
          'urgency':float(r.integers(1,6)/5),'cascade':float(min(1,node_importance[node]*50+r.uniform(.1,.6))),
          'service':float(r.uniform(.25,1)),'equity_proxy':float(r.uniform(0,1)),
          'environmental_benefit':float(r.uniform(0,1)),'carbon_penalty':float(r.uniform(0,1)),
          'crew_type':crew_map[d['node_type']],'duration_hours':float(r.integers(1,5)),
          'pumps_required':int(r.random()<.35),'cost':int(r.integers(3000,16000)),
          'budget_assumption_currency':'INR (hypothetical)','scenario_seed':seed,
          'resource_note':'Synthetic planning assumption; no measured crew or inventory data.'})
    return rows
cases=make_cases(SEED,32)
candidate_frame=pd.DataFrame(cases)
display(candidate_frame.head());display(candidate_frame.describe(include='all').T)
candidate_frame.to_csv(OUT/'scenario_candidates.csv',index=False)
''')
pair(a,'3.2 Score construction and normalization','Factors are supplied on [0,1]; weighted sum preserves a transparent unitless utility. Carbon is a penalty (negative contribution); affordability is also enforced as a hard budget constraint.', '''
weights=validate_weights(DEFAULT_WEIGHTS)
print('Normalized score weights',weights,'sum',sum(weights.values()))
candidate_frame['utility']=[score_intervention(c,weights) for c in cases]
display(candidate_frame[['case_id',*weights,'utility','cost']].sort_values('utility',ascending=False).head(12))
''')
pair(a,'3.3 Score-factor distributions and rank','No outcome data exists to validate these scores. Weight sensitivity asks how the hypothetical ranking changes under alternative declared priorities.', '''
fig,ax=plt.subplots(1,2,figsize=(13,4))
candidate_frame[list(weights)].plot.box(ax=ax[0],rot=40,title='Synthetic normalized factors')
candidate_frame.utility.plot.hist(bins=20,ax=ax[1],title='Default weighted utility');plt.tight_layout();plt.show()
''')
a.append(md('''## 04. Decision model

For candidate interventions i, choose binary xᵢ. Maximize Σᵢ uᵢxᵢ subject to: (a) each incident/case appears at most once; (b) total assumed cost ≤ scenario budget; (c) total pump units ≤ inventory; (d) assigned team hours ≤ available hours per skill. CP-SAT uses integer-scaled utilities and deterministic single-worker settings. An infeasible result is surfaced; there is no relax-and-dispatch fallback.

Severity-first and utility-greedy baselines apply the **same constraints** while walking a fixed ranking. The exact optimum can outperform these heuristics, but its selected set reflects only the synthetic scoring assumptions supplied here.'''))
pair(a,'4.1 Resource scenarios','Normal, scarce budget, pump shortage and crew shortage are explicit hypothetical inventories.', '''
scenarios={
 'normal':{'budget':150000,'pumps':8,'crew_hours':{'water':36,'drain':30,'road':24}},
 'budget_scarce':{'budget':55000,'pumps':8,'crew_hours':{'water':36,'drain':30,'road':24}},
 'pump_shortage':{'budget':100000,'pumps':2,'crew_hours':{'water':24,'drain':24,'road':24}},
 'crew_shortage':{'budget':100000,'pumps':5,'crew_hours':{'water':8,'drain':7,'road':6}}}
display(pd.DataFrame([{'scenario':k,'budget_INR_assumption':v['budget'],'pumps':v['pumps'],**{f'{c}_hours':h for c,h in v['crew_hours'].items()}} for k,v in scenarios.items()]))
''')
pair(a,'4.2 Solve and enforce feasibility','OR-Tools returns a recommended set and metrics. The output requires a human to review each choice.', '''
methods={};timings=[]
for scenario_name,resource in scenarios.items():
    for method in ['severity_greedy','utility_greedy','CP-SAT']:
        start=time.perf_counter()
        result=(solve_cpsat(cases,resource,time_limit=3) if method=='CP-SAT' else greedy_allocate(cases,resource,method='severity' if method.startswith('severity') else 'utility'))
        elapsed=time.perf_counter()-start;assert_feasible(result['selected'],resource)
        methods[(scenario_name,method)]=result
        timings.append({'scenario':scenario_name,'method':method,'status':result['status'],'utility':result['objective'],
          'selected_count':len(result['selected']),'budget_used':result['used']['budget'],'pump_use':result['used']['pumps'],
          'solver_seconds':elapsed,'approval_required':result['approval_required'],'dispatch_allowed':result['dispatch_allowed']})
comparison=pd.DataFrame(timings);display(comparison)
''')
pair(a,'4.3 Constraint satisfaction and utilization','Every method satisfies the same hard budget, pump and crew-hour constraints. Verify solver status and feasibility rather than assuming it.', '''
assert all(assert_feasible(r['selected'],r['available']) for r in methods.values())
assert not any(r['dispatch_allowed'] for r in methods.values())
comparison['budget_utilization']=comparison.budget_used/comparison.scenario.map({k:v['budget'] for k,v in scenarios.items()})
comparison['incident_coverage']=comparison.selected_count/len(cases)
display(comparison.groupby('method').agg(mean_utility=('utility','mean'),mean_selected=('selected_count','mean'),mean_budget_use=('budget_utilization','mean'),mean_solver_seconds=('solver_seconds','mean')))
comparison.to_csv(OUT/'method_comparison.csv',index=False)
''')
pair(a,'4.4 Utility, coverage and resource-use plots','Solver runtime is machine-dependent. Utility, feasibility and use are measured on synthetic examples only.', '''
fig,ax=plt.subplots(1,3,figsize=(15,4))
sns.barplot(data=comparison,x='scenario',y='utility',hue='method',ax=ax[0]);ax[0].tick_params(axis='x',rotation=25)
sns.barplot(data=comparison,x='scenario',y='selected_count',hue='method',ax=ax[1]);ax[1].tick_params(axis='x',rotation=25)
sns.barplot(data=comparison,x='scenario',y='budget_utilization',hue='method',ax=ax[2]);ax[2].tick_params(axis='x',rotation=25)
plt.tight_layout();plt.show()
''')
a.append(md('''## 05. Weight sensitivity and robustness

Weights can change rankings. Do not tune them on synthetic solver output to imply a preferred real public policy. Run transparent perturbations and report selected-set stability, objective and affordability. Equity inputs are fictional until linked to a valid, privacy-reviewed service-access indicator; no demographic inference is made.'''))
pair(a,'5.1 Sustainability and equity weighting','Raise each configured weight while renormalizing the remaining weight mass proportionally. Inventory constraints do not change.', '''
weight_rows=[]
for focus in ['cascade','environmental_benefit','equity_proxy','carbon_penalty']:
    for target in [.05,.15,.30,.45]:
        w=dict(weights);rest=sum(v for k,v in w.items() if k!=focus)
        for k in w:
            w[k]=target if k==focus else (1-target)*w[k]/rest
        w=validate_weights(w);weighted=[{**c,'utility':score_intervention(c,w)} for c in cases]
        r=solve_cpsat(weighted,scenarios['normal'],weights=w,time_limit=3)
        weight_rows.append({'focus':focus,'weight':w[focus],'utility':r['objective'],'selected_count':len(r['selected']),
                            'selected_ids':tuple(sorted(c['case_id'] for c in r['selected'])),'weights':json.dumps(w,sort_keys=True)})
weight_sensitivity=pd.DataFrame(weight_rows);display(weight_sensitivity.drop(columns='weights'))
weight_sensitivity.to_csv(OUT/'weight_sensitivity.csv',index=False)
''')
pair(a,'5.2 Selected-set stability','Jaccard overlap reveals whether the top-level selection depends strongly on one subjective score factor.', '''
reference=set(methods[('normal','CP-SAT')]['selected'][i]['case_id'] for i in range(len(methods[('normal','CP-SAT')]['selected'])))
stability=[]
for row in weight_sensitivity.itertuples():
    selected=set(row.selected_ids);stability.append({'focus':row.focus,'weight':row.weight,'jaccard_vs_default':len(reference&selected)/max(1,len(reference|selected))})
stability=pd.DataFrame(stability);display(stability)
sns.lineplot(data=stability,x='weight',y='jaccard_vs_default',hue='focus',marker='o');plt.ylim(0,1);plt.title('Synthetic allocation sensitivity');plt.show()
''')
pair(a,'5.3 Random scenario stress test','Repeated random cases test implementation stability across different hypothetical inputs. They do not estimate real city-wide solver performance.', '''
stress=[]
for seed in range(10,20):
    sample=make_cases(seed,32)
    resource=scenarios['budget_scarce']
    for method in ['severity','utility','CP-SAT']:
        result=solve_cpsat(sample,resource,time_limit=2) if method=='CP-SAT' else greedy_allocate(sample,resource,method=method)
        assert_feasible(result['selected'],resource)
        stress.append({'seed':seed,'method':method,'utility':result['objective'],'selected':len(result['selected']),'cost':result['used']['budget']})
stress=pd.DataFrame(stress);display(stress.groupby('method').agg(mean_utility=('utility','mean'),std_utility=('utility','std'),mean_selected=('selected','mean')))
sns.boxplot(data=stress,x='method',y='utility');plt.title('Stress-test objective variability');plt.show()
stress.to_csv(OUT/'scenario_stress.csv',index=False)
''')
a.append(md('''## 06. Explainability, integration and export

Export the normalized weights, graph fingerprint, assumptions, scenario cases, feasible selections and solver metrics as versioned JSON/CSV. Recommendations carry scenario provenance and human-approval flags. The workspace contains no reusable CivicFlux OR-Tools optimizer or approval API, so this is a pure research interface; it does not change a backend route.'''))
pair(a,'6.1 Explain each recommended intervention','Expose factor contributions, cost and resource consumption. The score is a ranking aid, not an authorization.', '''
selected=methods[('normal','CP-SAT')]['selected'];contrib=[]
for case in selected:
    vals={k:case[k] for k in weights};vals['carbon_penalty']=-vals['carbon_penalty']
    contrib.append({'case_id':case['case_id'],'node_id':case['node_id'],'node_type':case['node_type'],'utility':case['utility'],
       'cost_assumption':case['cost'],'crew_type':case['crew_type'],'hours':case['duration_hours'],'pumps':case['pumps_required'],
       **{f'{k}_contribution':weights[k]*vals[k] for k in weights}})
explanation=pd.DataFrame(contrib);display(explanation)
explanation.to_csv(OUT/'selected_explanations.csv',index=False)
''')
pair(a,'6.2 Save selected allocation artifacts','Artifacts include optimality/feasibility status, objective and hard limits.', '''
comparison.to_csv(OUT/'metrics.csv',index=False)
all_results={scenario:{method:result for (s,method),result in methods.items() if s==scenario} for scenario in scenarios}
(OUT/'optimization_results.json').write_text(json.dumps(all_results,indent=2,default=str))
(OUT/'scenario_manifest.json').write_text(json.dumps({'version':VERSION,'seed':SEED,'graph_id':graph.graph['graph_id'],'graph_fingerprint':graph_fingerprint(graph),
  'weights':weights,'synthetic':True,'unit_cost':'hypothetical INR','inventory':'scenario-specific fictional availability',
  'human_approval_required':True,'dispatch_allowed':False},indent=2))
''')
pair(a,'6.3 CivicFlux recommendation envelope','An application can pass this envelope to an existing human review queue after its schema is verified. Predictions alone cannot approve procurement or dispatch.', '''
recommendations=[{'case_id':c['case_id'],'node_id':c['node_id'],'utility':c['utility'],'estimated_cost_assumption':c['cost'],
 'resources':{'crew_type':c['crew_type'],'hours':c['duration_hours'],'pumps':c['pumps_required']},
 'provenance':'synthetic scenario','requires_human_approval':True,'dispatch_allowed':False} for c in selected]
(OUT/'approval_envelope_example.json').write_text(json.dumps({'component':'resource_optimizer','version':VERSION,'scenario':'normal','recommendations':recommendations,'approval_status':'not_requested','automatic_dispatch':False},indent=2))
print(json.dumps({'selected':len(recommendations),'approval_required':True,'dispatch_allowed':False},indent=2))
''')
a.append(md('''### Findings and limitations

CP-SAT provides an optimal solution relative to the declared integer objective when status is `OPTIMAL`; baselines offer feasible comparison policies. A timeout may produce only `FEASIBLE`, and such status is retained. All numerical costs, crew capacities, carbon burdens, benefits and equity proxies are synthetic. The L-TOWN benchmark topology is water-only and is kept separate from the synthetic cross-sector service graph. No real affordability, environmental justice, procurement, crew safety or intervention-effect claim follows from this exercise. A CivicFlux deployment needs an operator-approved incident schema, live inventory, validated compatibility constraints, transparent policy weights, and an explicit approval workflow.'''))
make('08_Sustainability_and_Resource_Optimization.ipynb','Sustainability-aware resource-allocation research',None,a)

# ---------------------------------------------------------------------------
# Notebook 09 — verification-aware synthetic outcome model.
# ---------------------------------------------------------------------------
b=[]
b.append(md('''# CivicFlux — Intervention Outcomes Research

**Notebook 09 · synthetic outcome-data experiment · predictive association only**

No verified municipal intervention outcomes or approval workflow is present in the inspected repository. This notebook creates an explicitly synthetic schema and experiment so data handling and evaluation can be demonstrated. It does not report real intervention success or causal benefits.'''))
b.append(md('''## 01. Objective and label integrity

Research design: predict independently verified completion success and resolution time from **pre-intervention** planned conditions in a synthetic dataset. An approved or completed work order is not automatically a success. A valid success label requires completion, named independent verifier, verification timestamp and evidence reference.

Synthetic labels are generated by a declared mechanism with resource allocation associated with initial severity. This induces selection bias. Forecasting labels in this toy population does not tell us what would have happened under a different intervention; predictive association is not a treatment effect.'''))
pair(b,'1.1 Setup','Use versioned CivicFlux schema and inference helpers.', '''
from pathlib import Path
import sys,json,platform,importlib.metadata
import numpy as np,pandas as pd,seaborn as sns,matplotlib.pyplot as plt
from IPython.display import display
import joblib
ROOT=Path.cwd() if (Path.cwd()/'civicflux_core.py').exists() else Path.cwd().parent
sys.path.insert(0,str(ROOT))
from src.civicflux.outcomes import (VERSION,REQUIRED,FEATURES,OutcomeBundle,generate_synthetic_outcomes,
 validate_outcome_record,verify_outcome,leakage_safe_features)
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder,StandardScaler
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression,Ridge
from sklearn.ensemble import RandomForestClassifier,RandomForestRegressor,HistGradientBoostingRegressor
from sklearn.model_selection import TimeSeriesSplit,RandomizedSearchCV,cross_validate
from sklearn.metrics import (average_precision_score,roc_auc_score,brier_score_loss,precision_score,recall_score,f1_score,
 mean_absolute_error,mean_squared_error,classification_report,ConfusionMatrixDisplay,PrecisionRecallDisplay)
from sklearn.calibration import calibration_curve
from scipy.stats import loguniform
sns.set_theme(style='whitegrid');SEED=42
OUT=ROOT/'artifacts'/'intervention_outcomes'/'v1.0.0';OUT.mkdir(parents=True,exist_ok=True)
print(platform.python_version(),{p:importlib.metadata.version(p) for p in ['pandas','numpy','scikit-learn']})
''')
pair(b,'1.2 Existing backend audit','No intervention records, verification service, resource optimizer or civic approval endpoint is present in the reviewed project. Existing SAGE components refer to synthetic electronics burn-in; they are excluded.', '''
print('Outcome fields are generated in src/civicflux/outcomes.py')
print('No verified real intervention outcomes discovered in available project datasets.')
print('Existing unrelated backend approvals are not relabeled as CivicFlux municipal interventions.')
''')
b.append(md('''## 02. Outcome schema and synthetic data provenance

The schema distinguishes proposal, approval, progress, completion and independent outcome verification. In this experiment every record is tagged `source_type=synthetic`. The seed and label mechanism are fixed and exported. The generated row count is a pedagogical sample size, not an observed civic record count.'''))
pair(b,'2.1 Define all fields','Feature candidates are known at assignment time. Completion, verification evidence and resolution fields are post-assignment outcomes and never model inputs.', '''
print('Required schema:',REQUIRED)
print('Pre-assignment features:',FEATURES)
data=generate_synthetic_outcomes(n=6000,seed=SEED)
assert data.source_type.eq('synthetic').all()
assert set(FEATURES).isdisjoint({'status','completion_time','outcome_status','verified_success','verification_time','resolution_hours'})
display(data.head());display(data.dtypes.to_frame('dtype'))
(OUT/'synthetic_intervention_records.csv').write_text(data.to_csv(index=False))
''')
pair(b,'2.2 Provenance and assumptions','Generated records have synthetic identifiers, hypothetical severity/resource distributions, simulated outcomes and dates. None encodes a real municipal incident.', '''
manifest={'component':'intervention_outcome_research','version':VERSION,'synthetic':True,'seed':SEED,'n':len(data),
 'period':[str(data.assignment_time.min()),str(data.assignment_time.max())],
 'completion_rate':float(data.status.eq('completed').mean()),'verification_rate':float(data.outcome_status.str.startswith('verified_').mean()),
 'success_mechanism':'simulated logistic response to severity/intervention/resource choices; assignment is confounded',
 'causal_claim':None,'limitations':['No observed interventions','No real outcome verification','No counterfactual outcomes','Selection bias is built into simulation']}
(OUT/'synthetic_data_manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest,indent=2))
''')
b.append(md('''## 03. Inspection and EDA

Describe completion and verification separately. Resolution time is available only for completed jobs in this generator; verified success is available only for independently verified completed records. Missing outcomes remain missing. Never code an unverified row as success=0.'''))
pair(b,'3.1 Coverage, missing values and status','A verified outcome subset can be selected for classification. Completion alone does not create an outcome label.', '''
quality=pd.DataFrame({'missing':data.isna().sum(),'missing_percent':100*data.isna().mean()})
display(quality)
fig,ax=plt.subplots(1,3,figsize=(14,4))
data.status.value_counts().plot.bar(ax=ax[0],title='Work status')
data.outcome_status.value_counts().plot.bar(ax=ax[1],title='Independent outcome verification')
(100*data.outcome_status.str.startswith('verified_').groupby(data.intervention_type).mean()).plot.bar(ax=ax[2],title='Verified fraction by synthetic intervention type',ylabel='%')
plt.tight_layout();plt.show()
''')
pair(b,'3.2 Intervention type and severity','Outcomes differ by type only because the synthetic generator assigns differing inputs and mechanisms.', '''
fig,ax=plt.subplots(1,2,figsize=(12,4))
sns.countplot(data=data,x='intervention_type',hue='initial_severity',ax=ax[0]);ax[0].tick_params(axis='x',rotation=25)
sns.boxplot(data=data,x='intervention_type',y='planned_cost',ax=ax[1]);ax[1].tick_params(axis='x',rotation=25)
plt.tight_layout();plt.show()
''')
pair(b,'3.3 Completion, verification delay and resolution','Verification delay is defined only for verified rows and is not a predictor.', '''
verified=data[data.outcome_status.str.startswith('verified_')].copy()
verified['verification_delay_hours']=(pd.to_datetime(verified.verification_time)-pd.to_datetime(verified.completion_time)).dt.total_seconds()/3600
fig,ax=plt.subplots(1,2,figsize=(12,4))
sns.histplot(data=data[data.status.eq('completed')],x='resolution_hours',hue='intervention_type',bins=40,ax=ax[0]);ax[0].set_xscale('log')
sns.histplot(verified,x='verification_delay_hours',bins=35,ax=ax[1]);ax[1].set_title('Synthetic verification delay (hours)')
plt.tight_layout();plt.show()
''')
pair(b,'3.4 Seasonal assignment patterns','Chronological shift is important even for generated records.', '''
monthly=data.assign(month=pd.to_datetime(data.assignment_time).dt.to_period('M').astype(str)).groupby('month').agg(rows=('incident_id','size'),verified=('outcome_status',lambda x:x.str.startswith('verified_').mean()))
monthly.rows.plot(title='Synthetic records by assignment month',ylabel='Rows',figsize=(12,3));plt.show()
''')
pair(b,'3.5 Planned resource and outcome associations','These are descriptive associations inside a biased simulation, not benefits caused by using more resources.', '''
valid=data[data.outcome_status.isin(['verified_success','verified_failure'])].copy();valid['label']=valid.verified_success.astype(int)
display(valid.groupby('intervention_type').agg(n=('label','size'),success=('label','mean'),severity=('initial_severity','mean'),crew=('planned_crew_count','mean'),pumps=('planned_pump_count','mean')))
fig,ax=plt.subplots(1,2,figsize=(12,4))
sns.boxplot(data=valid,x='label',y='planned_crew_count',ax=ax[0]);sns.boxplot(data=valid,x='label',y='initial_severity',ax=ax[1]);plt.tight_layout();plt.show()
''')
b.append(md('''## 04. Preprocessing and leakage review

Parse timestamps explicitly, enforce verification rules, preserve missing outcomes and remove any row with contradictory completed/verification state. Train/test split is by assignment chronology. Classification uses only independently verified records; regression uses completed records whose resolution time is observed. Planned resources can reflect policy decisions and are predictive associations only.
'''))
pair(b,'4.1 Validate record states','Validate a representative complete record and demonstrate that a completed-but-unverified item has no supervised success label.', '''
example=data.iloc[0].to_dict();validated=validate_outcome_record(example)
display(pd.Series({k:validated[k] for k in ['status','outcome_status','verified_success','verified_by','evidence_ref','source_type']}))
assert not data.loc[~data.outcome_status.str.startswith('verified_'),'verified_success'].notna().any()
''')
pair(b,'4.2 Leakage audit','Feature allowlist is fixed in the shared inference implementation. Outcome, completion time, verifier, evidence and resolution duration are forbidden predictors.', '''
assert set(leakage_safe_features(data).columns)==set(FEATURES)
forbidden={'incident_id','intervention_id','completion_time','outcome_status','verified_success','verified_by','verification_time','evidence_ref','resolution_hours','status'}
assert set(FEATURES).isdisjoint(forbidden)
print('PASS. Prediction fields available at assignment:',FEATURES)
''')
pair(b,'4.3 Train-only preprocessing','One-hot categories and numeric scaling/imputation are fit inside each pipeline and refit within chronological CV.', '''
cat=['intervention_type','planned_crew_type'];num=[c for c in FEATURES if c not in cat]
def preprocess(scale=False):
    nums=[('numeric',SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True),num)]
    if scale:nums=[('numeric',Pipeline([('impute',SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True)),('scale',StandardScaler())]),num)]
    return ColumnTransformer(nums+[('categorical',OneHotEncoder(handle_unknown='ignore'),cat)])
def classification_pipeline(estimator,scale=False):return Pipeline([('preprocess',preprocess(scale)),('model',estimator)])
''')
b.append(md('''## 05. Time-aware prediction strategy

Use the first 60% of assignment dates for development, the next 20% for validation/threshold selection, and the last 20% as a final time holdout. All generated records have unique synthetic event IDs; each event is kept wholly within one time block. Three expanding CV folds evaluate the verified development subset. A target threshold is chosen on validation records only. Test scores never select the model.'''))
pair(b,'5.1 Split data and preserve group boundaries','Split on global assignment timestamps before filtering into task-specific cohorts.', '''
data['assignment_time']=pd.to_datetime(data.assignment_time)
times=np.sort(data.assignment_time.unique());cut1,cut2=times[int(.6*len(times))],times[int(.8*len(times))]
data['period']=np.where(data.assignment_time<cut1,'train',np.where(data.assignment_time<cut2,'validation','test'))
assert data.event_group.is_unique
print('Boundaries',cut1,cut2)
display(data.groupby('period').agg(rows=('incident_id','size'),groups=('event_group','nunique'),start=('assignment_time','min'),end=('assignment_time','max')))
''')
pair(b,'5.2 Build verified success cohort','Only completed interventions with independent verification enter classification.', '''
classification=data[data.outcome_status.isin(['verified_success','verified_failure'])].copy()
classification['target']=classification.verified_success.astype(int)
train=classification[classification.period.eq('train')];val=classification[classification.period.eq('validation')];test=classification[classification.period.eq('test')]
for label,part in [('train',train),('validation',val),('test',test)]:print(label,len(part),'verified positives',int(part.target.sum()),'prevalence',part.target.mean())
assert train.target.nunique()==2 and val.target.nunique()==2 and test.target.nunique()==2
''')
pair(b,'5.3 TimeSeries CV for verified success','A group cannot cross folds; each event is a unique intervention and groups are assigned before CV.', '''
train=train.sort_values('assignment_time').reset_index(drop=True)
cv=list(TimeSeriesSplit(n_splits=3).split(train))
for tr,va in cv:
    assert train.iloc[tr].assignment_time.max()<train.iloc[va].assignment_time.min()
    assert set(train.iloc[tr].event_group).isdisjoint(set(train.iloc[va].event_group))
''')
b.append(md('''## 06. Success model experiments

Compare a prior baseline, Logistic Regression, Random Forest and XGBoost on verified synthetic records. Average precision is the primary ranking metric for potentially imbalanced labels. Report Brier score, ROC-AUC and threshold metrics. The trained predictions are synthetic research surrogates.'''))
pair(b,'6.1 Candidate models','Tree candidates do not need scaling; Logistic Regression scales numeric features.', '''
from xgboost import XGBClassifier,XGBRegressor
models={'Prior':classification_pipeline(DummyClassifier(strategy='prior')),
 'Logistic':classification_pipeline(LogisticRegression(max_iter=2000,class_weight='balanced',random_state=SEED),True),
 'Random Forest':classification_pipeline(RandomForestClassifier(n_estimators=120,min_samples_leaf=8,class_weight='balanced',random_state=SEED,n_jobs=2)),
 'XGBoost':classification_pipeline(XGBClassifier(n_estimators=120,max_depth=3,learning_rate=.05,subsample=.85,colsample_bytree=.85,eval_metric='logloss',tree_method='hist',n_jobs=2,random_state=SEED))}
Xtr=train[FEATURES];ytr=train.target;Xv=val[FEATURES];yv=val.target;Xt=test[FEATURES];yt=test.target
''')
pair(b,'6.2 Cross-validation comparison','The folds use development data only; no temporal shuffling.', '''
cv_rows=[]
for name,est in models.items():
    scores=cross_validate(est,Xtr,ytr,cv=cv,scoring={'ap':'average_precision','brier':'neg_brier_score','auc':'roc_auc'},error_score='raise')
    for i in range(3):cv_rows.append({'model':name,'fold':i,'AP':scores['test_ap'][i],'Brier':-scores['test_brier'][i],'AUC':scores['test_auc'][i]})
cv_results=pd.DataFrame(cv_rows);cv_summary=cv_results.groupby('model').agg(AP=('AP','mean'),AP_std=('AP','std'),Brier=('Brier','mean'),AUC=('AUC','mean')).sort_values('AP',ascending=False)
display(cv_summary);cv_results.to_csv(OUT/'success_cv.csv',index=False)
cv_summary.AP.plot.barh(xerr=cv_summary.AP_std,title='Development temporal CV average precision');plt.show()
''')
pair(b,'6.3 Tune leading learned candidates','A small declared randomized search compares Logistic Regression and XGBoost. Both tune within temporal folds.', '''
spaces={'Logistic':{'model__C':loguniform(.03,30),'model__class_weight':[None,'balanced']},
 'XGBoost':{'model__n_estimators':[80,120,180],'model__max_depth':[2,3,5],'model__learning_rate':[.03,.08,.15],'model__min_child_weight':[1,5,10]}}
searches={};ranking=cv_summary.AP.to_dict()
for name,space in spaces.items():
    search=RandomizedSearchCV(models[name],space,n_iter=5,cv=cv,scoring='average_precision',refit=True,random_state=SEED,n_jobs=1,error_score='raise')
    search.fit(Xtr,ytr);searches[name]=search;ranking[name+' tuned']=search.best_score_
    pd.DataFrame(search.cv_results_).to_csv(OUT/(name+'_success_search.csv'),index=False)
    print(name,search.best_params_,-search.best_score_ if False else search.best_score_)
selected=max(ranking,key=ranking.get)
final=searches[selected.removesuffix(' tuned')].best_estimator_ if selected.endswith(' tuned') else models[selected].fit(Xtr,ytr)
print('CV selection:',selected)
''')
pair(b,'6.4 Validation-only decision threshold','Select threshold by F1 on the validation cohort. This is not an approval or resource dispatch rule.', '''
pv=final.predict_proba(Xv)[:,1]
thresholds=np.linspace(.05,.95,91)
f1s=[f1_score(yv,pv>=t,zero_division=0) for t in thresholds]
threshold=float(thresholds[int(np.argmax(f1s))])
plt.plot(thresholds,f1s);plt.axvline(threshold,color='red');plt.title('Validation F1 and locked threshold');plt.show()
''')
b.append(md('''## 07. Locked test evaluation for success

Evaluate once on the final period. Report discrimination, precision/recall, calibration, confusion matrix, error slices and leave results intact even if poor. The metrics describe this synthetic, selection-biased data generator.'''))
pair(b,'7.1 Final classification metrics','No test label alters the threshold or model selection.', '''
from sklearn.metrics import precision_score,recall_score,f1_score,roc_auc_score,average_precision_score,brier_score_loss,classification_report,ConfusionMatrixDisplay,PrecisionRecallDisplay
pt=final.predict_proba(Xt)[:,1];yh=pt>=threshold
success_metrics={'average_precision':float(average_precision_score(yt,pt)),'ROC_AUC':float(roc_auc_score(yt,pt)),
 'Brier':float(brier_score_loss(yt,pt)),'precision':float(precision_score(yt,yh,zero_division=0)),
 'recall':float(recall_score(yt,yh,zero_division=0)),'F1':float(f1_score(yt,yh,zero_division=0)),
 'threshold':threshold,'test_n':len(yt),'test_prevalence':float(yt.mean()),'synthetic':True}
print(json.dumps(success_metrics,indent=2));print(classification_report(yt,yh,zero_division=0))
fig,ax=plt.subplots(1,2,figsize=(12,4));ConfusionMatrixDisplay.from_predictions(yt,yh,ax=ax[0]);PrecisionRecallDisplay.from_predictions(yt,pt,ax=ax[1]);plt.tight_layout();plt.show()
''')
pair(b,'7.2 Reliability and calibration','Evaluate probability calibration on synthetic test data; reliability does not make the probabilities valid for real operations.', '''
observed,predicted=calibration_curve(yt,pt,n_bins=10,strategy='quantile')
plt.plot(predicted,observed,'o-');plt.plot([0,1],[0,1],'k--');plt.xlabel('Predicted probability');plt.ylabel('Observed synthetic success fraction');plt.title('Final reliability');plt.show()
''')
pair(b,'7.3 Performance by intervention type','Small subgroup counts and simulated assignment bias can make subgroup estimates unstable.', '''
sub=[]
for kind,idx in test.groupby('intervention_type').groups.items():
    loc=test.index.get_indexer(idx);true=test.loc[idx,'target'];prob=pt[loc]
    sub.append({'intervention_type':kind,'n':len(true),'prevalence':true.mean(),'AP':average_precision_score(true,prob),'Brier':brier_score_loss(true,prob)})
subgroup=pd.DataFrame(sub);display(subgroup);subgroup.to_csv(OUT/'success_type_slices.csv',index=False)
''')
b.append(md('''## 08. Resolution-time estimation

Model positive observed time among completed synthetic jobs. The naive median and category median are training-only baselines. Compare Ridge and Random Forest regression with log1p target where suitable. Right-censoring is not modelled: incomplete items have unknown resolution duration and are excluded, so results apply only to completed records in this toy generator.'''))
pair(b,'8.1 Build completed-time cohorts','Only completion status and recorded duration define eligibility. Completion time itself is not a feature.', '''
completed=data[data.status.eq('completed') & data.resolution_hours.notna()].copy()
trd=completed[completed.period.eq('train')];vad=completed[completed.period.eq('validation')];ted=completed[completed.period.eq('test')]
assert trd.resolution_hours.gt(0).all()
duration_cat=['intervention_type','planned_crew_type'];duration_num=[c for c in FEATURES if c not in duration_cat]
prep_duration=ColumnTransformer([('numeric',Pipeline([('impute',SimpleImputer(strategy='median',keep_empty_features=True)),('scale',StandardScaler())]),duration_num),
 ('categorical',OneHotEncoder(handle_unknown='ignore'),duration_cat)])
def duration_pipeline(est):return Pipeline([('preprocess',prep_duration),('model',est)])
''')
pair(b,'8.2 Compare historical baseline and regressors','MAE/RMSE in hours describe synthetic completed work only.', '''
from sklearn.metrics import mean_absolute_error,mean_squared_error
regressors={'Ridge':duration_pipeline(Ridge(alpha=10)),
 'Random Forest':Pipeline([('preprocess',ColumnTransformer([('numeric',SimpleImputer(strategy='median',keep_empty_features=True),duration_num),('categorical',OneHotEncoder(handle_unknown='ignore'),duration_cat)])),('model',RandomForestRegressor(n_estimators=120,min_samples_leaf=8,max_depth=12,random_state=SEED,n_jobs=2))]),
 'XGBoost':Pipeline([('preprocess',ColumnTransformer([('numeric',SimpleImputer(strategy='median',keep_empty_features=True),duration_num),('categorical',OneHotEncoder(handle_unknown='ignore'),duration_cat)])),('model',XGBRegressor(n_estimators=120,max_depth=3,learning_rate=.05,objective='reg:squarederror',tree_method='hist',n_jobs=2,random_state=SEED))])}
Xdt=ted[FEATURES];ydt=ted.resolution_hours.to_numpy();rows=[]
for name,est in regressors.items():
    est.fit(trd[FEATURES],np.log1p(trd.resolution_hours));pred=np.maximum(0,np.expm1(est.predict(Xdt)))
    rows.append({'model':name,'MAE_hours':mean_absolute_error(ydt,pred),'RMSE_hours':mean_squared_error(ydt,pred)**.5})
base=float(trd.resolution_hours.median());rows.append({'model':'Train median baseline','MAE_hours':mean_absolute_error(ydt,np.repeat(base,len(ydt))),'RMSE_hours':mean_squared_error(ydt,np.repeat(base,len(ydt)))**.5})
duration_results=pd.DataFrame(rows);display(duration_results);duration_results.to_csv(OUT/'duration_comparison.csv',index=False)
''')
pair(b,'8.3 Duration residual analysis','Long durations may remain difficult. Quantile spread and errors by type are descriptive.', '''
duration_best=min([r for r in rows if r['model']!='Train median baseline'],key=lambda z:z['MAE_hours'])['model']
duration_model=regressors[duration_best]
duration_pred=np.maximum(0,np.expm1(duration_model.predict(Xdt)))
resid=ydt-duration_pred
sns.scatterplot(x=duration_pred,y=resid,hue=ted.intervention_type);plt.axhline(0,color='black');plt.xlabel('Predicted hours');plt.ylabel('Observed minus predicted hours');plt.title('Synthetic test residuals');plt.show()
''')
b.append(md('''## 09. Explainability, verification interface and export

Permutation importance uses validation data. The bundle accepts only known pre-intervention fields and emits synthetic-research warnings. Verification helpers reject work that is not completed, missing an independent verifier, or lacking evidence. Synthetic rows cannot be promoted to real verified labels.'''))
pair(b,'9.1 Permutation importance','Importance reflects synthetic generator associations, not intervention mechanisms or causal effects.', '''
from sklearn.inspection import permutation_importance
imp=permutation_importance(final,val[FEATURES],val.target,scoring='average_precision',n_repeats=4,random_state=SEED,n_jobs=1)
importance=pd.Series(imp.importances_mean,index=FEATURES).sort_values()
importance.tail(15).plot.barh(title='Validation permutation importance');plt.show()
importance.to_csv(OUT/'success_permutation_importance.csv')
''')
pair(b,'9.2 Validate completed versus verified distinction','A verified result cannot be created from an approved or in-progress work order.', '''
unverified=data[data.outcome_status.eq('unverified')].iloc[0].to_dict()
try:verify_outcome(unverified,True,'reviewer-1','evidence://example')
except ValueError as error:print('Expected abstention:',error)
else:raise AssertionError('Unverified item incorrectly promoted')
completed_verified=data[data.outcome_status.str.startswith('verified_')].iloc[0].to_dict()
assert validate_outcome_record(completed_verified)['verified_by']
''')
pair(b,'9.3 Train bundle and validate prediction contract','The saved artifact is a synthetic surrogate. It cannot approve or dispatch an intervention.', '''
chosen_duration=regressors[duration_best]
metadata={'component':'intervention_outcome_research','version':VERSION,'source_type':'synthetic','selected_success_model':selected,
 'selected_duration_model':duration_best,'features':FEATURES,'success_metrics':success_metrics,'duration_metric':duration_best,
 'synthetic_data_manifest':manifest,'causal_effect_estimate':None,'auto_approve':False,'dispatch_allowed':False,'duration_log1p':True}
bundle=OutcomeBundle(final,chosen_duration,FEATURES,metadata)
joblib.dump(bundle,OUT/'pipeline.joblib')
example=leakage_safe_features(test.iloc[[0]])
pred=bundle.predict(test.iloc[0].to_dict());print(json.dumps(pred,indent=2))
assert pred['dispatch_allowed'] is False and pred['causal_effect'] is None
(OUT/'example_prediction.json').write_text(json.dumps(pred,indent=2))
(OUT/'metadata.json').write_text(json.dumps(metadata,indent=2,default=str))
''')
pair(b,'9.4 Artifact reload and inference schema','Reload the exact saved object and check stable prediction on a held-out example.', '''
loaded=joblib.load(OUT/'pipeline.joblib')
assert loaded.predict(test.iloc[0].to_dict())==pred
(OUT/'feature_schema.json').write_text(json.dumps({'features':FEATURES,'excluded_post_intervention_fields':['completion_time','verification_time','verified_by','verified_success','outcome_status','resolution_hours']},indent=2))
(OUT/'success_metrics.json').write_text(json.dumps(success_metrics,indent=2))
''')
b.append(md('''### Findings and limitations

The notebook demonstrates a valid verification-aware schema and time-separated modelling workflow, but all fitted model metrics refer to synthetic outcomes. The simulation deliberately assigns resources based on severity, creating selection bias; logistic prediction does not estimate the intervention’s causal effect. Independent real intervention/completion/verification records, an established audit policy, representative resource histories and a clearly defined target population are prerequisites for real ML evaluation. Continue to use human approval and independently confirm outcomes.'''))
make('09_Intervention_Outcomes.ipynb','Intervention outcomes research',None,b)
