import json
from copy import deepcopy
from fastapi import HTTPException
from project_paths import PROJECT_ROOT
from src.civicflux.integration import fixture,compatible_graph_evidence
from src.civicflux.graph import from_config,graph_fingerprint
from src.civicflux.serving import serve,directory_for
from src.civicflux.cascade import dependency_trace
from backend.simulation import simulate
from backend.optimizer import plan
from backend.graph import scenario_graph
from backend.db import repository as repo

def execute(body,actor,persist=True):
    clock=repo.now();flood=simulate(body.flood.model_dump(),clock,body.flood_engine)
    request=fixture('cascade_risk',PROJECT_ROOT)
    request.update(initial=body.initial,load=body.load,observation_time=clock,as_of=clock)
    graph,manifest=scenario_graph()
    from src.civicflux.graph import graph_config
    request['graph']=graph_config(graph)
    if not body.initial or any(node not in graph for node in body.initial): raise HTTPException(422,'Initial asset must exist in the synthetic graph')
    cascade=serve('cascade_risk',request,PROJECT_ROOT)
    if manifest['graph_fingerprint']!=graph_fingerprint(graph): raise HTTPException(409,'Cascade and planning graph evidence are incompatible')
    if flood['status']!='supported_simulation' or cascade['status']!='supported_simulation':
        raise HTTPException(409,{'reason':'Scenario abstained; no plan created','flood':flood,'cascade':cascade})
    risks={r['node_id']:r['risk'] for r in cascade['prediction']}
    # The cascade model scores future failures only and omits outage seeds.
    # A declared seed is already failed in this synthetic scenario, not a forecast.
    risks.update({node:1.0 for node in body.initial})
    import pandas as pd
    template=(PROJECT_ROOT/manifest['candidate_template']).resolve()
    if not template.is_relative_to((PROJECT_ROOT/'artifacts').resolve()): raise HTTPException(409,'Invalid candidate source')
    cases=pd.read_csv(template).to_dict('records')
    for case in cases:
        evidence={'synthetic':True,'graph_id':graph.graph['graph_id'],'graph_fingerprint':graph_fingerprint(graph),'node_id':case['node_id']}
        if not compatible_graph_evidence(evidence,graph) or case['node_id'] not in risks: raise HTTPException(409,'Unmapped asset evidence')
        case['cascade']=risks[case['node_id']]
        case['cascade_evidence']='declared synthetic outage' if case['node_id'] in body.initial else 'same-graph research cascade score'
    try: allocation=plan(cases,body.resources.model_dump(),body.weights)
    except (ValueError,KeyError,TypeError) as error: raise HTTPException(422,str(error)) from error
    payload={'name':body.name,'city_id':body.city_id,'inputs':body.model_dump(),'synthetic':True,'flood':flood,'cascade':cascade,'allocation':allocation,
        'graph_id':graph.graph['graph_id'],'graph_fingerprint':graph_fingerprint(graph),
        'affected_assets':[r for r in cascade['prediction'] if r['node_id'] in body.initial or r.get('review')],
        'dependency_traces':[dependency_trace(graph,body.initial,n,body.load) for n in sorted((n for n in risks if n not in body.initial),key=lambda n:risks[n],reverse=True)[:10]],
        'review_status':'pending','dispatch_allowed':False,
        'assumptions':['All asset IDs and intervention costs are synthetic; city selection does not geolocate them.',
            manifest['candidate_assignment'],
            'Flood surrogate and cascade outage are parallel scenario evidence. Outages are explicitly chosen by the operator; no learned flood-to-asset mapping exists.',
            'Cascade scores enter planning only on the identical graph fingerprint. Delhi/L-TOWN/traffic evidence is never fused.',
            'Weights represent policy assumptions; no causal intervention benefit is estimated.',
            'Research approval is disabled by the existing review contract. No intervention is dispatched.']}
    if persist:return repo.append('scenario',payload,actor,'scenario_executed')
    from uuid import uuid4
    return {**payload,'id':'preview-'+str(uuid4()),'created':clock,'preview':True}
