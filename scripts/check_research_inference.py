"""Fresh Python worker used by Notebook 11; contains no Jupyter imports."""
from pathlib import Path
import sys,json,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.civicflux.serving import serve,json_safe,discover,directory_for,interface_fingerprint
from civicflux_core import sha256
from src.civicflux.integration import fixture,negative_requests,anomaly_sensor_fixtures

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('component');parser.add_argument('--output',required=True)
    args=parser.parse_args();request=fixture(args.component,ROOT);positive=serve(args.component,request,ROOT)
    negatives={name:serve(args.component,item,ROOT) for name,item in negative_requests(args.component,request).items()}
    sensor_results={}
    if args.component=='infrastructure_anomaly':
        sensor_results={sensor:serve(args.component,item,ROOT) for sensor,item in anomaly_sensor_fixtures(ROOT).items()}
    passed=all(r['status']=='supported_research' for r in sensor_results.values()) and positive['status'] in {'supported_research','supported_simulation'} and all(r['status']=='abstained' for r in negatives.values())
    entry=next(r for r in discover(ROOT) if r['component']==args.component)
    artifact=ROOT/entry['artifact'] if entry['artifact'] else directory_for(ROOT,args.component)/'metadata.json'
    report={'interface_sha256':interface_fingerprint(ROOT),'artifact_sha256':sha256(artifact),'component':args.component,'fresh_process':True,'jupyter_imported':'IPython' in sys.modules or 'ipykernel' in sys.modules,
            'python':sys.executable,'positive':positive,'negative_cases':negatives,'sensor_results':sensor_results,'passed':passed}
    Path(args.output).write_text(json.dumps(json_safe(report),indent=2,allow_nan=False))
    print(json.dumps({'component':args.component,'status':positive['status'],'negative_cases':len(negatives),'passed':passed}))
    sys.exit(0 if passed else 1)
