"""Versioned synthetic 60-minute dependency cascades; never confirmed city faults."""
import heapq
import itertools
import numpy as np
import pandas as pd
import networkx as nx
from .graph import NODE_TYPES,synthetic_graph,graph_config,graph_fingerprint

NUMERIC=['criticality','resilience','load','in_degree','out_degree','betweenness','failed_predecessors','direct_exposure','seed_distance','upstream_failed_fraction']
CATEGORICAL=['node_type']
FEATURES=NUMERIC+CATEGORICAL

def validate_graph(g):
    if not g.is_directed():raise ValueError('Dependencies must be directed')
    if g.graph.get('synthetic') is not True:raise ValueError('Only validated synthetic graph contract is supported')
    for n,d in g.nodes(data=True):
        if d.get('node_type') not in NODE_TYPES:raise ValueError('Unknown node type')
        for key in ['resilience','criticality']:
            if not np.isfinite(d[key]) or not 0<=d[key]<=1:raise ValueError('Invalid node parameter')
    for u,v,d in g.edges(data=True):
        if not 0<=d['weight']<=1 or d['delay_minutes']<=0:raise ValueError('Invalid dependency edge')

def node_features(g,initial,load):
    validate_graph(g)
    initial=set(initial)
    if not initial or not initial.issubset(g):raise ValueError('Unknown/empty initial disruption set')
    if not np.isfinite(load) or not .5<=load<=1.5:raise ValueError('Load outside supported scenario range [.5,1.5]')
    centrality=nx.betweenness_centrality(g,normalized=True)
    distances={n:min((nx.shortest_path_length(g,s,n) for s in initial if nx.has_path(g,s,n)),default=99) for n in g}
    rows=[]
    for node,d in g.nodes(data=True):
        if node in initial:continue # Target applies only to operational nodes at origin.
        parents=list(g.predecessors(node));anc=nx.ancestors(g,node)
        rows.append({'node_id':node,'node_type':d['node_type'],'criticality':d['criticality'],'resilience':d['resilience'],'load':load,
                     'in_degree':g.in_degree(node),'out_degree':g.out_degree(node),'betweenness':centrality[node],
                     'failed_predecessors':len(set(parents)&initial),'direct_exposure':sum(g[p][node]['weight'] for p in parents if p in initial),
                     'seed_distance':distances[node],'upstream_failed_fraction':len(anc&initial)/max(1,len(anc))})
    return pd.DataFrame(rows)

def simulate_event(g,initial,load,seed,horizon=60):
    """Independent cascade: each newly failed node gets one chance per outgoing edge.

    Transmission probability = clip(weight * load * (1-target resilience),0,1).
    Delays are fixed scenario attributes. No spontaneous failures or repairs.
    Multiple incoming attempts are allowed; earliest successful arrival wins.
    """
    validate_graph(g);rng=np.random.default_rng(seed)
    failed={n:0 for n in initial};queue=[(0,n) for n in initial];heapq.heapify(queue)
    while queue:
        t,u=heapq.heappop(queue)
        if t!=failed[u]:continue
        for v in sorted(g.successors(u)):
            arrival=t+g[u][v]['delay_minutes']
            if arrival>horizon or (v in failed and failed[v]<=arrival):continue
            probability=np.clip(g[u][v]['weight']*load*(1-g.nodes[v]['resilience']),0,1)
            if rng.random()<probability:
                failed[v]=arrival;heapq.heappush(queue,(arrival,v))
    return failed

def generate_cascades(seed=42):
    """Independent event groups and unseen graph conditions; fixed seed."""
    rng=np.random.default_rng(seed);graphs={};rows=[];manifest=[]
    for graph_seed in range(100,106):
        g=synthetic_graph(graph_seed);graphs[g.graph['graph_id']]=g
        combinations=list(itertools.combinations(sorted(g.nodes),2));rng.shuffle(combinations)
        for j,initial in enumerate(combinations[:90]):
            event_id=f'{graph_seed}-{j}'
            # Graphs 104/105 are wholly unseen during learning and threshold selection.
            split='test_unseen_graph' if graph_seed>=104 else ('train' if j<60 else ('validation' if j<75 else 'test_seen_graph'))
            load=float(rng.uniform(.7,1.3) if graph_seed<104 else rng.uniform(1.1,1.5))
            f=node_features(g,initial,load);future=simulate_event(g,initial,load,seed*10000+graph_seed*100+j)
            f['target']=[int(n in future) for n in f.node_id]
            f['event_id']=event_id;f['graph_id']=g.graph['graph_id'];f['period']=split
            f['failure_minute']=[future.get(n,np.nan) for n in f.node_id]
            rows.append(f);manifest.append({'event_id':event_id,'graph_id':g.graph['graph_id'],'initial':list(initial),'load':load,'period':split,'random_seed':seed*10000+graph_seed*100+j})
    return pd.concat(rows,ignore_index=True),graphs,manifest

def propagation_rule(g,initial,horizon=60):
    """Deterministic reachability through directed edges within summed delays.

    Ignores uncertain transmission/resilience and is intentionally transparent.
    """
    reached=set()
    for s in initial:
        reached.update(nx.single_source_dijkstra_path_length(g,s,cutoff=horizon,weight='delay_minutes'))
    return reached-set(initial)

class CascadeBundle:
    def __init__(self,model,threshold,metadata):self.model=model;self.threshold=threshold;self.metadata=metadata
    def predict(self,g,initial,load,observation_time):
        t=pd.Timestamp(observation_time)
        if t.tzinfo is None:raise ValueError('Snapshot timestamp must be timezone-aware')
        f=node_features(g,initial,load)
        p=self.model.predict_proba(f[FEATURES])[:,1]
        return {'component':'cascade_risk','version':self.metadata.get('version','1.0.0'),'horizon_minutes':60,'observation_time':t.isoformat(),
                'graph_id':g.graph.get('graph_id'),'graph_fingerprint':graph_fingerprint(g),'synthetic':True,'research_only':True,
                'provenance':'Independent-cascade simulation on hypothetical service dependency graphs','dispatch_allowed':False,
                'warnings':['Simulation-trained risks are not real-world failure probabilities.','No verified municipal topology or incident labels.'],
                'nodes':[{'node_id':n,'risk':float(prob),'review':bool(prob>=self.threshold)} for n,prob in zip(f.node_id,p)]}


def dependency_trace(g, initial, node, load=1., horizon=60):
    """Explain a snapshot exposure path, never claim the stochastic future path."""
    validate_graph(g)
    if node not in g:raise ValueError('Unknown target node')
    paths=[]
    for seed in initial:
        if seed not in g:raise ValueError('Unknown initial node')
        try:path=nx.shortest_path(g,seed,node,weight='delay_minutes')
        except nx.NetworkXNoPath:continue
        elapsed=0;factor=1.;steps=[]
        for u,v in zip(path,path[1:]):
            edge=g[u][v];elapsed+=edge['delay_minutes']
            chance=float(np.clip(edge['weight']*load*(1-g.nodes[v]['resilience']),0,1));factor*=chance
            steps.append({'provider':u,'dependent':v,'edge_weight':edge['weight'],'delay_minutes':edge['delay_minutes'],
                          'target_resilience':g.nodes[v]['resilience'],'conditional_transmission':chance})
        paths.append({'initial_node':seed,'path':path,'arrival_minutes_if_transmitted':elapsed,'within_horizon':elapsed<=horizon,
                      'single_path_transmission_product':factor,'steps':steps})
    return {'node_id':node,'horizon_minutes':horizon,'paths':paths,'semantics':'Candidate dependency routes; not realized failures or total cascade probability'}
