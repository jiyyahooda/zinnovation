"""Read saved experiments and verify their arithmetic; never train models."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score
from civicflux_core import CONFIGS,canonicalize,make_features
from .research import binary_metrics
from .serving import discover,directory_for,json_safe,interface_fingerprint


def recompute_metrics(root,tolerance=1e-5):
    root=Path(root);checks=[];baselines=[]
    for component in ['rainfall','aqi','traffic','flood','water_network','cascade_risk','intervention_outcomes']:
        directory=directory_for(root,component);path=directory/'test_predictions.csv'
        if not path.exists():
            checks.append({'component':component,'metric':'predictions','status':'unavailable'});continue
        prediction=pd.read_csv(path);metadata=json.loads((directory/'metadata.json').read_text())
        reported=json.loads((directory/('success_metrics.json' if component=='intervention_outcomes' else 'metrics.json')).read_text())
        if component in CONFIGS:
            y=prediction.target.to_numpy();p=prediction.prediction.to_numpy()
            calculated={'MAE':mean_absolute_error(y,p),'RMSE':mean_squared_error(y,p)**.5,'R2':r2_score(y,p),'bias':float(np.mean(p-y))}
            cfg=CONFIGS[component];raw=pd.read_csv(root/'data/raw'/cfg['file']);history,_=canonicalize(raw,cfg)
            # Reproduce the published BaselineRegressor fallback from training labels only.
            features=make_features(history,cfg)
            first=history.groupby('entity').time.min()
            warmup=pd.to_timedelta(max(cfg['lags']),unit='D' if cfg['freq']=='D' else 'h')
            ready=features.time>=features.entity.map(first)+warmup
            split=pd.read_csv(directory/'split_boundaries.csv').iloc[0]
            development=features[ready & features.target.notna() & features.time.between(pd.Timestamp(split.origin_start),pd.Timestamp(split.origin_end))]
            fallback=float(development.target.mean())
            history['time']=history.time.astype(str);history['entity']=history.entity.astype(str)
            keys=prediction[['time','entity']].copy();keys['entity']=keys.entity.astype(str)
            aligned=keys.merge(history[['time','entity','value']],on=['time','entity'],how='left',validate='one_to_one')
            missing_count=int(aligned.value.isna().sum())
            baseline=mean_absolute_error(y,aligned.value.fillna(fallback));calculated['MAE_skill_vs_persistence']=1-calculated['MAE']/baseline
            baselines.append({'component':component,'model_MAE':calculated['MAE'],'baseline_MAE':baseline,'baseline':'persistence; training-mean fallback for missing current',
                 'fallback_count':missing_count,'units':metadata['units'],'paired_n':len(y),'MAE_skill':calculated['MAE_skill_vs_persistence']})
        else:
            threshold=reported.get('threshold',metadata.get('success_threshold',metadata.get('threshold',.5)))
            calculated=binary_metrics(prediction.target,prediction.probability,threshold)
            calculated['average_precision']=calculated['PR_AUC_average_precision']
            calculated['Brier_calibrated']=calculated['Brier'];calculated['positive_prevalence']=calculated['prevalence']
            calculated['test_prevalence']=calculated['prevalence'];calculated['test_n']=calculated['n'];calculated['threshold']=threshold
        for metric,value in reported.items():
            if isinstance(value,bool) or not isinstance(value,(int,float)) or value is None:continue
            if metric not in calculated:
                checks.append({'component':component,'metric':metric,'reported':value,'recomputed':None,'status':'not recomputable from saved predictions'})
            else:
                actual=float(calculated[metric]);difference=abs(actual-value)
                checks.append({'component':component,'metric':metric,'reported':value,'recomputed':actual,'absolute_difference':difference,
                               'status':'consistent' if np.isclose(actual,value,rtol=tolerance,atol=tolerance) else 'MISMATCH'})
    return pd.DataFrame(checks),pd.DataFrame(baselines)


def artifact_inventory(root):
    from civicflux_core import sha256
    # Inventory all versions of the nine components, excluding self-referential report hashes.
    component_roots=[Path(root)/'artifacts'/entry['component'] for entry in discover(root)]
    paths=sorted(p for directory in component_roots for p in directory.rglob('*') if p.is_file())
    return pd.DataFrame([{'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'suffix':p.suffix,'sha256':sha256(p)} for p in paths])


def component_comparisons(root):
    root=Path(root);tables={}
    for c,filename in [('water_network','baseline_comparison.csv'),('cascade_risk','final_comparison.csv'),
                       ('resource_optimization','method_comparison.csv'),('intervention_outcomes','success_baseline_comparison.csv')]:
        path=directory_for(root,c)/filename
        if path.exists():tables[c]=pd.read_csv(path)
    path=directory_for(root,'flood');pred=pd.read_csv(path/'test_predictions.csv');split=pd.read_csv(path/'splits.csv')
    prior=float(split[split['split'].eq('dev')].prevalence.iloc[0]);meta=json.loads((path/'metadata.json').read_text())
    tables['flood']=pd.DataFrame([{'model':'selected simulated flood classifier',**binary_metrics(pred.target,pred.probability,meta['metrics']['threshold'])},
                                {'model':'training prior',**binary_metrics(pred.target,np.repeat(prior,len(pred)),.5)}])
    return tables


def registry_with_checks(root,check_directory=None):
    registry=discover(root)
    for row in registry:
        if check_directory is None:continue
        check=Path(check_directory)/(row['component']+'.json')
        if not check.exists():continue
        report=json.loads(check.read_text())
        from civicflux_core import sha256
        current=Path(root)/row['artifact'] if row['artifact'] else directory_for(root,row['component'])/'metadata.json'
        if report.get('artifact_sha256')!=sha256(current) or report.get('interface_sha256')!=interface_fingerprint(root):
            row['readiness_reason']='Artifact changed after fresh-process check';continue
        if report.get('passed') and not report.get('jupyter_imported'):
            row['readiness']='Simulation/demo only' if row['simulation_only'] else 'Backend-ready for research inference'
            row['readiness_reason']='Fresh Python process loaded artifact, predicted and abstained for negative input cases'
        else:row['readiness_reason']='Fresh-process load/inference/negative checks failed'
        row['fresh_process_report']=str(check)
    return registry
