"""Read-only research verification. Never trains or regenerates notebooks."""
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from project_paths import PROJECT_ROOT, MODEL_REGISTRY
from src.civicflux.serving import discover

def main():
    out=ROOT/'reports/windows'
    (out/'inference').mkdir(parents=True,exist_ok=True)
    dependencies={}
    for name,module in [('numpy','numpy'),('pandas','pandas'),('scikit-learn','sklearn'),('xgboost','xgboost'),('networkx','networkx'),('ortools','ortools'),('joblib','joblib'),('fastapi','fastapi'),('uvicorn','uvicorn')]:
        try:
            importlib.import_module(module)
            dependencies[name]={'version':importlib.metadata.version(name),'import':'passed'}
        except Exception as error: dependencies[name]={'import':'failed','error':str(error)}
    results=[]
    for entry in discover(ROOT):
        component=entry['component']
        process=subprocess.run([sys.executable,str(ROOT/'scripts/check_research_inference.py'),component,'--output',str(out/'inference'/f'{component}.json')],cwd=ROOT,capture_output=True,text=True)
        report=out/'inference'/f'{component}.json'
        record=json.loads(report.read_text(encoding='utf-8')) if report.exists() else {}
        results.append({**entry,'exit_code':process.returncode,'passed':record.get('passed',False),'positive_status':record.get('positive',{}).get('status'),'warnings':record.get('positive',{}).get('warnings',[]),'negative_cases':len(record.get('negative_cases',{})),'stderr':process.stderr})
        print(component,process.returncode,flush=True)
    inventory={'root':str(PROJECT_ROOT),'registry':str(MODEL_REGISTRY),'source':str(ROOT/'src/civicflux/serving.py'),'import':'from src.civicflux.serving import serve','python':platform.python_version(),'executable':sys.executable,'training_python':'3.13.5 (recorded in transferred pyvenv.cfg)','dependencies':dependencies,'components':results}
    (out/'migration_inventory.json').write_text(json.dumps(inventory,indent=2,ensure_ascii=False),encoding='utf-8')
    lock=subprocess.run([sys.executable,'-m','pip','freeze'],capture_output=True,text=True,check=True)
    (out/'requirements-windows.lock.txt').write_text(lock.stdout,encoding='utf-8')
    return 0 if all(r['passed'] for r in results) else 1

if __name__=='__main__':sys.exit(main())
