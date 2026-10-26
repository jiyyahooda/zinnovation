"""Shared transport metadata for existing CivicFlux components; no server required."""
from pathlib import Path
import json
from civicflux_core import sha256

CONTRACT_VERSION='civicflux.research.v1'


def metadata(component, directory, kind, scope, units, horizon, provenance, supported_inputs, validation):
    path=Path(directory)
    artifacts={p.name:{'path':str(p),'sha256':sha256(p)} for p in sorted(path.iterdir()) if p.is_file() and p.suffix in {'.joblib','.json','.csv'} and p.name not in {'metadata.json','standard_metadata.json'}}
    return {'contract_version':CONTRACT_VERSION,'component':component,'artifact_version':path.name if path.name.startswith('v') else 'legacy-unversioned',
            'component_kind':kind,'geographic_scope':scope,'units':units,'horizon':horizon,'provenance':provenance,
            'supported_inputs':supported_inputs,'validation_status':validation,'operational_supported':False,'research_only':True,
            'automatic_dispatch':False,'artifacts':artifacts}


def standardize(component,directory,**kwargs):
    path=Path(directory);result=metadata(component,path,**kwargs)
    existing=path/'metadata.json';old=json.loads(existing.read_text()) if existing.exists() else {}
    old.update({k:v for k,v in result.items() if k!='artifacts'})
    old['version']='1.1.0';existing.write_text(json.dumps(old,indent=2,default=str))
    (path/'standard_metadata.json').write_text(json.dumps(result,indent=2,default=str))
    return result
