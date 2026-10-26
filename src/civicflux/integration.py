"""Saved-artifact fixtures and a bounded synthetic decision demonstration."""
from copy import deepcopy
from pathlib import Path
import json
import numpy as np
import pandas as pd
from civicflux_core import CONFIGS
from .serving import SCOPES,UNITS,HORIZONS,serve,json_safe,directory_for


def fixture(component,root):
    root=Path(root);request={'scope':SCOPES[component],'units':UNITS[component],'horizon':HORIZONS[component],
        'purpose':'research','mode':'historical'}
    if component in CONFIGS:
        cfg=CONFIGS[component];raw=pd.read_csv(root/'data/raw'/cfg['file'])
        entity='1' if component=='traffic' else 'Delhi'
        raw=raw[raw[cfg['entity']].astype(str).eq(entity)].copy()
        test=pd.read_csv(root/'artifacts'/component/'test_predictions.csv');origin=pd.Timestamp(test.iloc[0].time)
        timestamps=pd.to_datetime(raw[cfg['time']],format=cfg['date_format'])
        cutoff=origin.tz_localize(None) if origin.tzinfo else origin
        raw=raw[timestamps<=cutoff].sort_values(cfg['time']).tail(max(cfg['lags'])+30)
        request.update(history=json_safe(raw.to_dict('records')),as_of=str(origin))
    elif component=='flood':
        row=pd.read_csv(root/'artifacts/flood/test_predictions.csv').iloc[0]
        from civicflux_core import FLOOD_FEATURES
        request.update(mode='simulation',synthetic=True,scenarios=[row[FLOOD_FEATURES].to_dict()],observation_time=str(row.time),as_of=str(row.time))
    elif component=='infrastructure_anomaly':
        from .anomaly import prepare_source
        cfg=CONFIGS['rainfall'];raw=pd.read_csv(root/'data/raw'/cfg['file']);history,specs,_=prepare_source(raw,'rainfall')
        history=history[history.sensor.eq('rainfall:Delhi')].sort_values('time')
        end=history[history.value.notna()].time.max();history=history[history.time<=end].tail(100)
        request.update(sensor='rainfall:Delhi',sensor_unit=specs['rainfall:Delhi'].unit,history=json_safe(history.to_dict('records')),observation_time=str(end),as_of=end.tz_localize('Asia/Kolkata').isoformat())
    elif component=='water_network':
        from .water import read_scada
        measurements={}
        for kind in ['Pressures','Flows','Levels']:
            frame=read_scada(root/f'data/raw/battledim/2019_SCADA_{kind}.csv')
            end=frame.index.max().floor('h');frame=frame.loc[:end].tail(24*12+1)
            measurements[kind]=json_safe(frame.reset_index().to_dict('records'))
        request.update(synthetic=True,measurements=measurements,network_id='L-TOWN',observation_time=str(end),as_of=str(end))
    elif component=='cascade_risk':
        from .graph import synthetic_graph,graph_config
        request.update(mode='simulation',synthetic=True,graph=graph_config(synthetic_graph(42)),initial=['pump_0'],load=1.1,
                       observation_time='2026-10-25T09:00:00Z',as_of='2026-10-25T09:00:00Z')
    elif component=='intervention_outcomes':
        row=pd.read_csv(directory_for(root,component)/'synthetic_intervention_records.csv').iloc[0]
        from .outcomes import FEATURES
        request.update(mode='simulation',synthetic=True,record=json_safe(row[FEATURES].to_dict()),observation_time=str(row.assignment_time),as_of=str(row.assignment_time))
    elif component=='resource_optimization':
        path=directory_for(root,component)
        cases=pd.read_csv(path/'scenario_candidates.csv').to_dict('records')
        results=json.loads((path/'optimization_results.json').read_text());resources=results['normal']['CP-SAT']['available']
        request.update(mode='simulation',synthetic=True,cases=json_safe(cases),resources=resources,observation_time='2026-10-25T09:00:00Z',as_of='2026-10-25T09:00:00Z')
    return json_safe(request)


def negative_requests(component,request):
    variants={}
    for name,field,value in [('wrong_units','units','unsupported'),('wrong_scope','scope','Delhi real asset'),
      ('wrong_horizon','horizon','unsupported'),('operational','purpose','operational')]:
        item=deepcopy(request);item[field]=value;variants[name]=item
    stale=deepcopy(request);stale['as_of']=str(pd.Timestamp(request['as_of'])+pd.Timedelta(days=365));variants['stale']=stale
    missing=deepcopy(request)
    key='history' if component in CONFIGS or component=='infrastructure_anomaly' else {'flood':'scenarios','water_network':'measurements','cascade_risk':'graph','intervention_outcomes':'record','resource_optimization':'cases'}[component]
    missing.pop(key,None);variants['missing_payload']=missing
    if component in {'cascade_risk','water_network','flood','resource_optimization','intervention_outcomes'}:
        false_provenance=deepcopy(request);false_provenance['synthetic']=False;variants['false_provenance']=false_provenance
    if component in CONFIGS:
        cfg=CONFIGS[component]
        missing_current=deepcopy(request);missing_current['history'][-1][cfg['value']]=None;variants['missing_current_reading']=missing_current
        unknown=deepcopy(request)
        for row in unknown['history']:row[cfg['entity']]='unregistered'
        variants['unknown_entity']=unknown
    elif component=='water_network':
        missing_reading=deepcopy(request)
        for key in list(missing_reading['measurements']['Pressures'][-1]):
            if key!='Timestamp':missing_reading['measurements']['Pressures'][-1][key]=None
        variants['missing_current_readings']=missing_reading
        unknown=deepcopy(request);unknown['network_id']='unverified-network';variants['unknown_network']=unknown
    elif component=='infrastructure_anomaly':
        unknown=deepcopy(request);unknown['sensor']='unknown';variants['unknown_sensor']=unknown
        unit=deepcopy(request);unit['sensor_unit']='unverified';variants['sensor_unit_mismatch']=unit
    elif component=='cascade_risk':
        outside=deepcopy(request);outside['load']=2.;variants['outside_load_support']=outside
        naive=deepcopy(request);naive['observation_time']='2026-10-25 09:00:00';variants['naive_snapshot_clock']=naive
    elif component=='resource_optimization':
        contaminated=deepcopy(request);contaminated['cases'][0]['success_probability']=.99;variants['unsupported_success_score']=contaminated
        invalid=deepcopy(request);invalid['resources']['budget']=-1;variants['negative_capacity']=invalid
    elif component=='intervention_outcomes':
        unknown=deepcopy(request);unknown['record']['intervention_type']='unsupported';variants['unknown_intervention']=unknown
        invalid=deepcopy(request);invalid['record']['planned_cost']=None;variants['missing_planned_cost']=invalid
    return variants


def compatible_graph_evidence(evidence,graph):
    """No guessed city-name, sensor-to-asset or cross-domain matching."""
    from .graph import graph_fingerprint
    return bool(evidence.get('synthetic') is True and evidence.get('graph_id')==graph.graph.get('graph_id') and
                evidence.get('graph_fingerprint')==graph_fingerprint(graph) and evidence.get('node_id') in graph)


def review_proposal(proposal,decision='pending',reviewer=None,synthetic=True):
    if decision not in {'pending','defer','reject'}:raise ValueError('This research demonstration cannot approve or dispatch')
    if decision!='pending' and not reviewer:raise ValueError('Named reviewer is required')
    return {'proposal_id':proposal['proposal_id'],'decision':decision,'reviewer':reviewer,'synthetic_demonstration':synthetic,
            'approval_status':'not_approved','dispatch_allowed':False,'outcome_verified':False}


def scenario_pipeline(root):
    from .graph import from_config,graph_fingerprint
    from .outcomes import verify_outcome
    cascade_request=fixture('cascade_risk',root);cascade=serve('cascade_risk',cascade_request,root)
    graph=from_config(cascade_request['graph']);trace=[{'stage':'scenario_origin','source':'declared synthetic pump outage; not inferred from rainfall/water/outcome scores',
          'graph_id':graph.graph['graph_id'],'graph_fingerprint':graph_fingerprint(graph)}]
    if cascade['status']!='supported_simulation':return {'status':'abstained','cascade':cascade,'audit_trace':trace}
    risks={row['node_id']:row['risk'] for row in cascade['prediction']}
    request=fixture('resource_optimization',root)
    manifest=json.loads((directory_for(root,'resource_optimization')/'scenario_manifest.json').read_text())
    if manifest['graph_fingerprint']!=graph_fingerprint(graph):raise ValueError('Optimization and cascade graphs differ')
    cases=[]
    for case in request['cases']:
        if case['node_id'] not in risks:continue
        evidence={'synthetic':True,'graph_id':graph.graph['graph_id'],'graph_fingerprint':graph_fingerprint(graph),'node_id':case['node_id']}
        if not compatible_graph_evidence(evidence,graph):raise ValueError('Unmapped dependency evidence')
        case['cascade']=risks[case['node_id']];cases.append(case)
    request['cases']=cases
    allocations=[]
    for name,ratio in [('normal',1.),('scarce_budget',.35)]:
        experiment=deepcopy(request);experiment['resources']['budget']=int(experiment['resources']['budget']*ratio)
        allocation=serve('resource_optimization',experiment,root)
        proposal={'proposal_id':'SYNTHETIC-'+name,'plan':allocation['prediction']}
        review=review_proposal(proposal)
        deferred=review_proposal(proposal,decision='defer',reviewer='fictional reviewer in explicitly synthetic walkthrough')
        allocations.append({'scenario':name,'allocation':allocation,'review':review,'demonstration_review_record':deferred})
    row=pd.read_csv(directory_for(root,'intervention_outcomes')/'synthetic_intervention_records.csv').query("status=='completed'").iloc[0].to_dict()
    try:verify_outcome(row,True,'demo-auditor','synthetic-evidence')
    except ValueError as error:verification={'status':'abstained','reason':str(error),'completed_work_is_verified_success':False}
    trace += [{'stage':'cascade','status':cascade['status'],'interpretation':'synthetic node evidence only'},
              {'stage':'optimization','status':'research proposals','human_approval':'pending','dispatch_allowed':False},
              {'stage':'outcome_verification','status':verification['status'],'reason':verification['reason']}]
    return json_safe({'status':'supported_simulation','cascade':cascade,'allocations':allocations,'verification':verification,
                     'blocked_cross_scope_bridge':{'status':'abstained','reason':'Delhi aggregate forecasts, L-TOWN sensors and synthetic dependency assets have no verified common mapping'},
                     'audit_trace':trace,'automatic_dispatch':False})


def anomaly_sensor_fixtures(root):
    import joblib
    from .anomaly import prepare_source
    root=Path(root);service=joblib.load(directory_for(root,'infrastructure_anomaly')/'detectors.joblib');cache={};requests={}
    for sensor,spec in service.specs.items():
        if sensor not in service.suites:continue
        if spec.family not in cache:
            cfg=CONFIGS[spec.family];cache[spec.family]=prepare_source(pd.read_csv(root/'data/raw'/cfg['file']),spec.family)[0]
        h=cache[spec.family];h=h[h.sensor.eq(sensor)].sort_values('time');end=h[h.value.notna()].time.max();h=h[h.time<=end].tail(200)
        req={'scope':SCOPES['infrastructure_anomaly'],'units':UNITS['infrastructure_anomaly'],'horizon':HORIZONS['infrastructure_anomaly'],
            'mode':'historical','purpose':'research','sensor':sensor,'sensor_unit':spec.unit,'history':json_safe(h.to_dict('records')),
            'observation_time':str(end),'as_of':end.tz_localize(spec.timezone).isoformat() if spec.timezone else str(end)}
        if spec.timezone is None:req['receipt_time_utc']=end.tz_localize('UTC').isoformat()
        requests[sensor]=req
    return requests
