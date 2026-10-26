"""Shared graph representation for benchmark water topology and synthetic dependencies.

Water pipe connectivity is undirected physical adjacency. Civic dependency
edges are directed upstream service -> dependent asset. Never conflate them.
"""
import hashlib,json
from pathlib import Path
import networkx as nx
import numpy as np

NODE_TYPES=('drainage','road','water','pump','facility')

def read_epanet(path):
    sections={};section=None
    for line in Path(path).read_text(errors='replace').splitlines():
        line=line.split(';')[0].strip()
        if line.startswith('['):section=line.upper();sections.setdefault(section,[])
        elif line and section:sections[section].append(line.split())
    g=nx.MultiGraph(provenance='BattLeDIM nominal EPANET topology; simulated benchmark',synthetic=True)
    for sect,kind in [('[JUNCTIONS]','junction'),('[RESERVOIRS]','reservoir'),('[TANKS]','tank')]:
        for row in sections.get(sect,[]):g.add_node(row[0],node_type=kind,elevation=float(row[1]),base_demand=float(row[2]) if kind=='junction' and len(row)>2 else 0.)
    for sect,kind in [('[PIPES]','pipe'),('[PUMPS]','pump'),('[VALVES]','valve')]:
        for row in sections.get(sect,[]):
            g.add_edge(row[1],row[2],key=row[0],link_id=row[0],link_type=kind,length=float(row[3]) if kind=='pipe' else 1.)
    for row in sections.get('[COORDINATES]',[]):
        if row[0] in g:g.nodes[row[0]]['pos']=(float(row[1]),float(row[2]))
    return g

def synthetic_graph(seed=42,n_per_type=8):
    """Synthetic service dependencies, with known weights but stochastic futures."""
    rng=np.random.default_rng(seed);g=nx.DiGraph(graph_id=f'synthetic-civic-{seed}',synthetic=True,version='1.0.0')
    for kind in NODE_TYPES:
        for i in range(n_per_type):g.add_node(f'{kind}_{i}',node_type=kind,criticality=float(rng.uniform(.3,1)),resilience=float(rng.uniform(.15,.7)))
    allowed=[('drainage','road'),('pump','drainage'),('pump','water'),('water','facility'),('road','facility'),('road','pump')]
    for a,b in allowed:
        for i in range(n_per_type):
            for j in rng.choice(n_per_type,2,replace=False):
                g.add_edge(f'{a}_{i}',f'{b}_{j}',weight=float(rng.uniform(.2,.85)),delay_minutes=int(rng.choice([10,20,30])),relationship='service_dependency')
    return g

def graph_fingerprint(g):
    nodes=sorted((str(n),dict(sorted(d.items()))) for n,d in g.nodes(data=True))
    edges=sorted((str(u),str(v),dict(sorted(d.items()))) for u,v,d in g.edges(data=True))
    return hashlib.sha256(json.dumps([nodes,edges],sort_keys=True).encode()).hexdigest()

def graph_config(g):
    return {'attributes':dict(g.graph),'nodes':[{'id':n,**d} for n,d in g.nodes(data=True)],'edges':[{'source':u,'target':v,**d} for u,v,d in g.edges(data=True)]}

def from_config(c):
    g=nx.DiGraph(**c['attributes'])
    for n in c['nodes']:g.add_node(n['id'],**{k:v for k,v in n.items() if k!='id'})
    for e in c['edges']:g.add_edge(e['source'],e['target'],**{k:v for k,v in e.items() if k not in ['source','target']})
    return g
