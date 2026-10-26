import json
import os,sys
from pathlib import Path
from functools import lru_cache
from project_paths import PROJECT_ROOT, REPORTS
from src.civicflux.serving import serve, discover, directory_for
from src.civicflux.integration import fixture
from src.civicflux.validation import registry_with_checks

def checks_directory():
    return Path(os.environ.get('CIVICFLUX_CHECKS_DIR',str(REPORTS/('macos' if sys.platform=='darwin' else 'windows')/'inference')))

def inventory():
    checks=checks_directory()
    rows=registry_with_checks(PROJECT_ROOT, checks)
    for row in rows:
        path=directory_for(PROJECT_ROOT,row['component'])
        row['metrics']={}
        for name in ['metrics.json','success_metrics.json']:
            if (path/name).exists(): row['metrics'][name]=json.loads((path/name).read_text(encoding='utf-8'))
        if not row['metrics'] and row['metadata']:
            meta=json.loads((PROJECT_ROOT/row['metadata']).read_text(encoding='utf-8'));row['metrics']=meta.get('test_metrics',{})
    return rows

def predict(component,request): return serve(component,request,PROJECT_ROOT)

@lru_cache(maxsize=9)
def historical(component):
    request=fixture(component,PROJECT_ROOT)
    result=predict(component,request)
    return {'response':result,'request_clock':request['as_of'],'input_kind':'saved historical benchmark' if request['mode']=='historical' else 'saved synthetic fixture'}
