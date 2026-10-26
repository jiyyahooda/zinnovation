"""Run existing saved-model checks in fresh macOS Python processes; no training."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.civicflux.serving import discover
from src.civicflux.runtime import research_environment

def main():
    out=ROOT/'reports/macos/inference';out.mkdir(parents=True,exist_ok=True);rows=[]
    for entry in discover(ROOT):
        component=entry['component'];destination=out/(component+'.json')
        result=subprocess.run([sys.executable,str(ROOT/'scripts/check_research_inference.py'),component,'--output',str(destination)],
            cwd=ROOT,env=research_environment(),capture_output=True,text=True,timeout=180)
        report=json.loads(destination.read_text()) if destination.exists() else {}
        rows.append({'component':component,'passed':report.get('passed',False),'status':report.get('positive',{}).get('status','not_ready'),
                     'warnings':report.get('positive',{}).get('warnings',[]),'return_code':result.returncode,'stderr':result.stderr[-3000:]})
        print(component,rows[-1]['status'],'PASS' if rows[-1]['passed'] else 'UNAVAILABLE',flush=True)
    (ROOT/'reports/macos/verification.json').write_text(json.dumps({'python':sys.executable,'components':rows},indent=2))
    return 0 if all(r['passed'] for r in rows) else 1

if __name__=='__main__':sys.exit(main())
