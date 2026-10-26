import json
import yaml
from project_paths import PROJECT_ROOT, CONFIG
from src.civicflux.graph import from_config,graph_config,graph_fingerprint
from fastapi import HTTPException

def scenario_graph():
    manifest=yaml.safe_load((CONFIG/'scenarios/research.yaml').read_text(encoding='utf-8'))
    source=(PROJECT_ROOT/manifest['graph_file']).resolve()
    if not source.is_relative_to((PROJECT_ROOT/'artifacts').resolve()): raise HTTPException(409,'Graph source leaves artifact directory')
    graph=from_config(json.loads(source.read_text(encoding='utf-8'))[manifest['graph_id']])
    if graph_fingerprint(graph)!=manifest['graph_fingerprint']: raise HTTPException(409,'Saved scenario graph fingerprint does not match configuration')
    return graph,manifest

def dependencies():
    graph,_=scenario_graph()
    return {**graph_config(graph),'fingerprint':graph_fingerprint(graph),'layout':'schematic; no geographic coordinates','edge_direction':'upstream service -> dependent asset'}
