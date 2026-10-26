"""One research serving adapter for FastAPI callers; no web server or retraining.

Call serve(component, request, root). Requests and responses are JSON-compatible.
The interface keeps legacy artifacts unchanged and checks scope before inference.
"""
from pathlib import Path
import json,math
import numpy as np
import pandas as pd
import joblib
from civicflux_core import CONFIGS,FLOOD_FEATURES,canonicalize
from .contracts import CONTRACT_VERSION

SCOPES={'rainfall':'Delhi state aggregate','aqi':'Delhi aggregate (station lineage unverified)',
 'traffic':'unlocated benchmark junctions','flood':'hypothetical catchments with state-rainfall reference',
 'infrastructure_anomaly':'source-specific unmapped benchmark sensors','water_network':'L-TOWN simulated network only',
 'cascade_risk':'synthetic civic dependency graphs','resource_optimization':'synthetic intervention scenarios',
 'intervention_outcomes':'synthetic intervention records only'}
UNITS={**{k:v['unit'] for k,v in CONFIGS.items()},'flood':{'rain_mm':'mm','duration_h':'hours','area_m2':'m2','drain_mm_h':'mm/hour','initial_storage_mm':'mm','fractions':'unitless'},
 'water_network':{'pressure':'m','flow':'m3/h','level':'m'},'cascade_risk':'unitless simulated risk',
 'resource_optimization':{'budget':'hypothetical INR','crew_hours':'hours','pumps':'count'},'intervention_outcomes':{'cost':'hypothetical INR','duration':'hours'},
 'infrastructure_anomaly':'per registered sensor'}
HORIZONS={'rainfall':'next day','aqi':'next hour PM2.5','traffic':'next hour vehicle count','flood':'24-hour simulated scenario',
 'infrastructure_anomaly':'contemporaneous unusual measurement','water_network':'onset during preceding 24 hours','cascade_risk':'next 60 minutes',
 'resource_optimization':'simultaneous planning window','intervention_outcomes':'completed synthetic outcome'}
SIMULATION={'flood','water_network','cascade_risk','resource_optimization','intervention_outcomes'}
KINDS={'infrastructure_anomaly':'unsupervised detectors + data-quality rules','resource_optimization':'CP-SAT optimization + greedy rules',
 'cascade_risk':'supervised simulator + graph rules','flood':'supervised simulator','intervention_outcomes':'synthetic classification + duration regression'}


def json_safe(value):
    if isinstance(value,dict):return {str(k):json_safe(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [json_safe(v) for v in value]
    if isinstance(value,(np.integer,np.bool_)):return value.item()
    if isinstance(value,(float,np.floating)):return float(value) if np.isfinite(value) else None
    if isinstance(value,(pd.Timestamp,Path)):return str(value)
    if value is pd.NA or value is pd.NaT:return None
    return value


def directory_for(root,component):
    root=Path(root)
    registry=root/'artifacts/model_validation/v1.0.0/model_registry.json'
    if registry.exists():
        rows=json.loads(registry.read_text(encoding='utf-8'))
        selected=next((r for r in rows if r['component']==component),None)
        if selected:
            path=(root/selected['artifact_directory']).resolve()
            if not path.is_relative_to((root/'artifacts').resolve()):raise ValueError('Registry path leaves artifacts directory')
            return path
    # Never promote a version merely because its directory sorts newest.
    # Legacy unversioned components remain discoverable; missing files abstain.
    return Path(root)/'artifacts'/component


def discover(root):
    rows=[]
    for component in SCOPES:
        path=directory_for(root,component);artifact=path/('detectors.joblib' if component=='infrastructure_anomaly' else 'pipeline.joblib')
        meta_file=path/('model_card.json' if component=='infrastructure_anomaly' else 'metadata.json')
        meta=json.loads(meta_file.read_text()) if meta_file.exists() else {}
        schema=path/'feature_schema.json'
        entry={'component':component,'component_kind':KINDS.get(component,'supervised time-series regression'),
          'artifact_directory':str(path.relative_to(root)),'artifact':str(artifact.relative_to(root)) if artifact.exists() else None,
          'metadata':str(meta_file.relative_to(root)) if meta_file.exists() else None,'feature_schema':str(schema.relative_to(root)) if schema.exists() else None,
          'version':path.name[1:] if path.name.startswith('v') else 'legacy-unversioned','geographic_scope':SCOPES[component],
          'units':UNITS[component],'horizon':HORIZONS[component],'supported_modes':['historical','simulation'] if component in SIMULATION else ['historical'],
          'provenance':meta.get('provenance',meta.get('source_url',meta.get('source_doi','see source-specific metadata/model card'))),
          'validation_status':meta.get('validation_status',meta.get('deployment_status','research evidence only')),
          'readiness':'Not ready','readiness_reason':'Fresh-process loading/inference not yet checked',
          'operational_supported':False,'simulation_only':component in SIMULATION,'missing':[],
          'selected_model':meta.get('selected_model',meta.get('winner',meta.get('selected_success_model','not a supervised selected model'))),
          'timestamp_policy':CONFIGS[component]['tz'] if component in CONFIGS else 'component-specific; see schema',
          'supported_inputs':{'required_request_fields':['scope','units','horizon','mode','as_of'],'input_schema':str(schema.relative_to(root)) if schema.exists() else None}}
        if not schema.exists():entry['missing'].append('feature_schema.json')
        if not meta_file.exists():entry['missing'].append(meta_file.name)
        if not artifact.exists() and component!='resource_optimization':entry['missing'].append('fitted artifact')
        rows.append(entry)
    return rows


def _clock(request,observation,limit_hours,timezone=None):
    mode=request.get('mode')
    if mode not in {'historical','simulation'}:raise ValueError('Only explicit historical/simulation modes are supported')
    if 'as_of' not in request:raise ValueError('as_of timestamp is required')
    t=pd.Timestamp(observation);now=pd.Timestamp(request['as_of'])
    if pd.isna(t) or pd.isna(now):raise ValueError('Timestamp is missing')
    if t.tzinfo is None and timezone:t=t.tz_localize(timezone)
    if now.tzinfo is None and timezone:now=now.tz_localize(timezone)
    if (t.tzinfo is None)!=(now.tzinfo is None):raise ValueError('Clock timezone mismatch')
    age=(now-t).total_seconds()/3600
    if age<0:raise ValueError('Future data relative to as_of')
    if age>limit_hours:raise ValueError('Stale inputs relative to explicit historical/simulation clock')
    return {'age_hours':age,'clock':'verified timezone' if t.tzinfo else 'source clock only; timezone unknown'}


def serve(component,request,root):
    root=Path(root);entry=next((r for r in discover(root) if r['component']==component),None)
    result={'contract_version':CONTRACT_VERSION,'component':component,'model_version':entry['version'] if entry else None,
      'status':'abstained','prediction':None,'uncertainty':None,'provenance':entry['provenance'] if entry else None,
      'validation_status':entry['validation_status'] if entry else 'unknown component','geographic_scope':entry['geographic_scope'] if entry else None,
      'units':entry['units'] if entry else None,'horizon':entry['horizon'] if entry else None,'research_only':True,
      'operational_supported':False,'allocation_eligible':False,'dispatch_allowed':False,'warnings':[]}
    try:
        if entry is None:raise ValueError('Unsupported component')
        if request.get('purpose','research')!='research':raise ValueError('Operational prediction/dispatch is unsupported')
        if request.get('scope')!=entry['geographic_scope']:raise ValueError('Unsupported geographic/entity scope')
        if request.get('units')!=entry['units']:raise ValueError('Unit contract mismatch')
        if request.get('horizon')!=entry['horizon']:raise ValueError('Horizon contract mismatch')
        if request.get('mode') not in entry['supported_modes']:raise ValueError('Unsupported inference mode')
        if entry['simulation_only'] and request.get('synthetic') is not True:raise ValueError('Explicit synthetic provenance is required')
        path=directory_for(root,component)
        if entry['missing']:raise ValueError('Missing artifact requirements: '+str(entry['missing']))
        bundle=joblib.load(root/entry['artifact']) if entry['artifact'] else None
        if component in CONFIGS:
            raw=pd.DataFrame(request['history']);cfg=bundle.cfg
            expected={'Delhi'} if component!='traffic' else {'1','2','3'}
            if not set(raw[cfg['entity']].astype(str)).issubset(expected):raise ValueError('Unsupported entity identity')
            if raw[[cfg['time'],cfg['entity']]].duplicated().any():raise ValueError('Duplicate observations are unsupported at serving')
            values=pd.to_numeric(raw[cfg['value']],errors='coerce')
            if values.isna().all() or (values.dropna()<0).any() or not np.isfinite(values.dropna()).all():raise ValueError('Missing/invalid measurement history')
            history,_=canonicalize(raw,cfg)
            for entity,g in history.groupby('entity'):
                if g.tail(max(cfg['lags'])+1).value.isna().mean()>.1 or pd.isna(g.iloc[-1].value):raise ValueError('Missing current reading or excessive gaps')
            observation=history.time.max();result['freshness']=_clock(request,observation,48 if component=='rainfall' else 2,cfg['tz'])
            split=pd.read_csv(path/'split_boundaries.csv');train_end=pd.Timestamp(split.iloc[0].last_label)
            if observation<=train_end:raise ValueError('Observation is not after the training cutoff')
            predictions=bundle.predict(raw);result['prediction']=predictions.drop(columns=['lower_90','upper_90']).to_dict('records')
            result['uncertainty']={'method':'calibration-period pooled absolute residual radius; no conditional coverage guarantee',
                'level':.9,'intervals':predictions[['entity','lower_90','upper_90']].to_dict('records')}
        elif component=='flood':
            result['freshness']=_clock(request,request['observation_time'],24)
            frame=pd.DataFrame(request['scenarios'])
            ranges={'duration_h':(1,12),'area_m2':(10000,100000),'runoff_coefficient':(.3,.95),'drain_mm_h':(.2,8),'blockage':(0,.9),'ponding_fraction':(.03,.2),'initial_storage_mm':(0,2)}
            for column,(low,high) in ranges.items():
                if not frame[column].between(low,high).all():raise ValueError('Outside simulated support: '+column)
            result['prediction']=bundle.predict(frame).to_dict('records')
        elif component=='water_network':
            from .water import UNITS as water_units
            measurements={key:pd.DataFrame(rows).assign(Timestamp=lambda d:pd.to_datetime(d.Timestamp)).set_index('Timestamp') for key,rows in request['measurements'].items()}
            observation=measurements['Pressures'].index.max();result['freshness']=_clock(request,observation,1)
            response=bundle.predict(measurements,water_units,network_id=request.get('network_id'),purpose='research')
            if response['probability'] is None:raise ValueError('; '.join(response['warnings']))
            result['prediction']={'benchmark_onset_score':response['probability'],'research_alert':response['alert'],'operational_fault_prediction':None}
            result['warnings']+=response['warnings']
        elif component=='cascade_risk':
            from .graph import from_config
            result['freshness']=_clock(request,request['observation_time'],1)
            graph=from_config(request['graph']);response=bundle.predict(graph,request['initial'],request['load'],request['observation_time'])
            result['prediction']=response['nodes'];result['graph_fingerprint']=response['graph_fingerprint'];result['warnings']+=response['warnings']
        elif component=='intervention_outcomes':
            result['freshness']=_clock(request,request['observation_time'],48)
            response=bundle.predict(request['record'],purpose='research')
            result['prediction']={'research_resolution_hours':response['predicted_resolution_hours'],'success_probability':None,
                                  'success_estimation_status':'unsupported for decisions'}
            result['warnings']+=response['warnings']
        elif component=='infrastructure_anomaly':
            if request.get('sensor') not in bundle.specs:raise ValueError('Unknown sensor identity')
            if request.get('sensor_unit')!=bundle.specs[request['sensor']].unit:raise ValueError('Sensor-specific unit mismatch')
            result['freshness']=_clock(request,request['observation_time'],48,bundle.specs[request['sensor']].timezone)
            response=bundle.predict(request['sensor'],pd.DataFrame(request['history']),request['observation_time'],detected_at=request.get('receipt_time_utc',request['as_of']))
            if response['anomaly_score'] is None:raise ValueError('; '.join(response['warnings']))
            if response['input_freshness']['status'] in {'stale','no_valid_history'}:raise ValueError('Stale or unavailable sensor history')
            result['prediction']=response;result['warnings']+=response['warnings']
        elif component=='resource_optimization':
            from .optimization import solve_cpsat
            result['freshness']=_clock(request,request['observation_time'],24)
            cases=request['cases'];resources=request['resources']
            for c in cases:
                forbidden={'research_success_score','prediction_success_probability','success_probability'} & set(c)
                if forbidden:raise ValueError('Unsupported success estimates cannot drive allocation')
                for field in ['cost','duration_hours','pumps_required']:
                    if not np.isfinite(float(c[field])) or float(c[field])<0:raise ValueError('Invalid resource requirement')
                if int(c['cost'])!=c['cost'] or int(c['pumps_required'])!=c['pumps_required']:raise ValueError('Costs and pump counts must be integer units')
            for v in [resources['budget'],resources['pumps'],*resources['crew_hours'].values()]:
                if not np.isfinite(v) or v<0:raise ValueError('Invalid capacity')
            result['prediction']=solve_cpsat(cases,resources,weights=request.get('weights'))
        result['status']='supported_simulation' if entry['simulation_only'] else 'supported_research'
        result['warnings'].append('Research inference only; independent validation and human review are required.')
        if component=='water_network':result['warnings'].append('Weak onset detection: explicitly abstain from operational fault predictions.')
    except (ValueError,KeyError,TypeError,IndexError,AttributeError,FileNotFoundError) as error:
        result['status']='abstained';result['prediction']=None;result['uncertainty']=None;result['warnings'].append(str(error))
    except Exception as error:
        result['status']='not_ready';result['prediction']=None;result['warnings'].append(type(error).__name__+': '+str(error))
    return json_safe(result)


def interface_fingerprint(root):
    import hashlib
    digest=hashlib.sha256()
    paths=[Path(root)/'civicflux_core.py',*sorted((Path(root)/'src/civicflux').glob('*.py'))]
    for path in paths:
        digest.update(str(path.relative_to(root)).encode());digest.update(path.read_bytes())
    return digest.hexdigest()
