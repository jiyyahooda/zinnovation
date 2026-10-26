"""CivicFlux research-only sustainability scoring and feasible CP-SAT selection.

No external side effect, real inventory, municipal cost estimate, or dispatch.
All case/resource data supplied to this component remain caller-owned.
"""
from dataclasses import dataclass
import math
from ortools.sat.python import cp_model

VERSION='1.0.0'
DEFAULT_WEIGHTS={'urgency':.25,'cascade':.20,'service':.20,'equity_proxy':.15,'environmental_benefit':.15,'carbon_penalty':.05}
FACTOR_FIELDS=tuple(DEFAULT_WEIGHTS)

def validate_weights(weights):
    if set(weights)!=set(FACTOR_FIELDS):raise ValueError('Score weights must include exactly the documented factors')
    if any(not math.isfinite(v) or v<0 for v in weights.values()) or sum(weights.values())<=0:raise ValueError('Weights must be finite, nonnegative and not all zero')
    total=sum(weights.values())
    return {k:v/total for k,v in weights.items()}

def score_intervention(case,weights=None):
    w=validate_weights(DEFAULT_WEIGHTS if weights is None else weights)
    vals={k:float(case[k]) for k in FACTOR_FIELDS}
    if any(not math.isfinite(v) or not 0<=v<=1 for v in vals.values()):raise ValueError('Score factors must be normalized to [0,1]')
    vals['carbon_penalty']=-vals['carbon_penalty']
    return sum(w[k]*vals[k] for k in FACTOR_FIELDS)

def validate_problem(cases,resources,weights=None):
    ids=[x['case_id'] for x in cases]
    if len(ids)!=len(set(ids)):raise ValueError('case_id must be unique')
    if not cases:raise ValueError('At least one intervention candidate is required')
    if resources.get('budget',-1)<0 or resources.get('pumps',-1)<0:raise ValueError('Resource inventory cannot be negative')
    for key,value in resources.get('crew_hours',{}).items():
        if value<0:raise ValueError('Crew hours cannot be negative')
    for c in cases:
        if c['crew_type'] not in resources.get('crew_hours',{}):raise ValueError(f"Incompatible or unavailable crew: {c['crew_type']}")
        if c['cost']<0 or c['duration_hours']<0 or c['pumps_required']<0:raise ValueError('Resource requirements cannot be negative')
        c['utility']=score_intervention(c,weights if weights is not None else c.get('weights'))
    return cases

def solve_cpsat(cases,resources,weights=None,time_limit=5):
    """Binary selection, at most one package per case, shared people/pumps/budget."""
    cases=[dict(c) for c in cases];validate_problem(cases,resources,weights)
    model=cp_model.CpModel();x={c['case_id']:model.NewBoolVar('select_'+c['case_id']) for c in cases}
    scale=10000
    model.Maximize(sum(round(c['utility']*scale)*x[c['case_id']] for c in cases))
    for c in cases:model.Add(x[c['case_id']]<=1)
    model.Add(sum(c['cost']*x[c['case_id']] for c in cases)<=int(resources['budget']))
    model.Add(sum(c['pumps_required']*x[c['case_id']] for c in cases)<=int(resources['pumps']))
    for crew,hours in resources['crew_hours'].items():
        model.Add(sum(int(c['duration_hours']*60)*x[c['case_id']] for c in cases if c['crew_type']==crew)<=int(hours*60))
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=time_limit;solver.parameters.num_search_workers=1;solver.parameters.random_seed=42
    status=solver.Solve(model)
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        return {'component':'resource_optimizer','version':VERSION,'status':solver.StatusName(status),'selected':[],
                'objective':0,'warnings':['No feasible allocation was found. No intervention was dispatched.'],'approval_required':True,'dispatch_allowed':False}
    selected=[c for c in cases if solver.Value(x[c['case_id']])]
    used={'budget':sum(c['cost'] for c in selected),'pumps':sum(c['pumps_required'] for c in selected),
          'crew_hours':{crew:sum(c['duration_hours'] for c in selected if c['crew_type']==crew) for crew in resources['crew_hours']}}
    result={'component':'resource_optimizer','version':VERSION,'status':solver.StatusName(status),'selected':selected,
            'objective':sum(c['utility'] for c in selected),'available':resources,'used':used,
            'solver_seconds':solver.WallTime(),'approval_required':True,'dispatch_allowed':False,
            'provenance':'synthetic scenario; user-provided constraints and assumptions'}
    assert_feasible(selected,resources)
    return result

def greedy_allocate(cases,resources,method='utility',weights=None):
    """Equivalent hard constraints; deterministic severity-first/utility baselines."""
    if method not in {'utility','severity'}:raise ValueError('method must be utility or severity')
    cases=[dict(c) for c in cases];validate_problem(cases,resources,weights)
    key=(lambda c:(c['urgency'],c['utility'],c['case_id'])) if method=='severity' else (lambda c:(c['utility'],c['urgency'],c['case_id']))
    selected=[];remaining={k:float(v) for k,v in resources['crew_hours'].items()};budget=resources['budget'];pumps=resources['pumps'];seen=set()
    for c in sorted(cases,key=key,reverse=True):
        crew=c['crew_type']
        if c['case_id'] in seen or c['cost']>budget or c['pumps_required']>pumps or c['duration_hours']>remaining[crew]:continue
        selected.append(c);seen.add(c['case_id']);budget-=c['cost'];pumps-=c['pumps_required'];remaining[crew]-=c['duration_hours']
    result={'component':'resource_optimizer','version':VERSION,'method':method,'status':'HEURISTIC_FEASIBLE','selected':selected,
            'objective':sum(c['utility'] for c in selected),'available':resources,
            'used':{'budget':sum(c['cost'] for c in selected),'pumps':sum(c['pumps_required'] for c in selected),
                    'crew_hours':{crew:sum(c['duration_hours'] for c in selected if c['crew_type']==crew) for crew in resources['crew_hours']}},
            'approval_required':True,'dispatch_allowed':False,'provenance':'synthetic scenario; user-provided constraints and assumptions'}
    assert_feasible(selected,resources)
    return result

def assert_feasible(selected,resources):
    if sum(c['cost'] for c in selected)>resources['budget']:raise AssertionError('Budget exceeded')
    if sum(c['pumps_required'] for c in selected)>resources['pumps']:raise AssertionError('Pump inventory exceeded')
    ids=[c['case_id'] for c in selected]
    if len(ids)!=len(set(ids)):raise AssertionError('An incident was selected twice')
    for crew,hours in resources['crew_hours'].items():
        if sum(c['duration_hours'] for c in selected if c['crew_type']==crew)>hours+1e-9:raise AssertionError('Crew availability exceeded')
    return True

@dataclass
class SolverEvidence:
    config:dict
    metrics:dict
    results:list
