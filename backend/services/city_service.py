import yaml
from fastapi import HTTPException
from project_paths import CONFIG

def cities(): return [yaml.safe_load(p.read_text(encoding='utf-8')) for p in sorted((CONFIG/'cities').glob('*.yaml'))]
def city(identifier):
    item=next((c for c in cities() if c['id']==identifier),None)
    if item is None: raise HTTPException(404,'Unknown city')
    return item
