import math
from typing import Literal
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel,Field,ConfigDict,field_validator
from backend.auth import admin
from backend.db import repository as repo
from backend.services.scenario_service import execute
from backend.graph import dependencies
router=APIRouter(prefix='/api/scenarios',tags=['synthetic scenarios'])
class Flood(BaseModel):
    model_config=ConfigDict(allow_inf_nan=False,extra='forbid')
    rain_mm:float=Field(default=60,ge=0,le=200)
    duration_h:float=Field(default=6,ge=1,le=12)
    area_m2:float=Field(default=50000,ge=10000,le=100000)
    runoff_coefficient:float=Field(default=.7,ge=.3,le=.95)
    drain_mm_h:float=Field(default=3,ge=.2,le=8)
    blockage:float=Field(default=.5,ge=0,le=.9)
    ponding_fraction:float=Field(default=.1,ge=.03,le=.2)
    initial_storage_mm:float=Field(default=0,ge=0,le=2)
class Resources(BaseModel):
    model_config=ConfigDict(allow_inf_nan=False,extra='forbid')
    budget:int=Field(default=50000,ge=0,le=10000000,strict=True)
    pumps:int=Field(default=4,ge=0,le=1000,strict=True)
    crew_hours:dict[str,float]=Field(default_factory=lambda:{'water':24,'road':24,'drain':24})
    @field_validator('crew_hours')
    @classmethod
    def valid_hours(cls,v):
        if any(not math.isfinite(x) or not 0<=x<=10000 for x in v.values()): raise ValueError('Invalid crew hours')
        return v
class Scenario(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    name:str=Field(default='Monsoon stress test',min_length=3,max_length=100)
    city_id:str='delhi'
    flood_engine:Literal['mass_balance','trained_surrogate']='mass_balance'
    flood:Flood=Field(default_factory=Flood)
    initial:list[str]=Field(default_factory=lambda:['pump_0'],max_length=40)
    load:float=Field(default=1.1,ge=.5,le=1.5)
    resources:Resources=Field(default_factory=Resources)
    weights:dict[str,float]|None=None
@router.get('')
def index(): return repo.all_records('scenario')
@router.get('/graph')
def graph(): return dependencies()
@router.get('/defaults')
def defaults(): return Scenario().model_dump()
@router.post('/preview')
def preview(body:Scenario):
    from backend.services.city_service import city
    city(body.city_id);return execute(body,'public-preview',persist=False)
@router.get('/trace')
def trace(node:str,initial:str='pump_0',load:float=1.1):
    from backend.graph import scenario_graph
    from src.civicflux.cascade import dependency_trace
    from fastapi import HTTPException
    if not math.isfinite(load) or not .5<=load<=1.5:raise HTTPException(422,'Unsupported load')
    graph,_=scenario_graph()
    try:return dependency_trace(graph,initial.split(','),node,load)
    except ValueError as error:raise HTTPException(422,str(error)) from error

@router.post('/analyze')
def analyze(body:Scenario,request:Request,save:bool=False):
    import queue,threading,json
    from fastapi.responses import StreamingResponse
    from backend.services.city_service import city
    city(body.city_id);actor=admin(request) if save else 'public-preview'
    events=queue.Queue()
    def work():
        try:
            result=execute(body,actor,persist=save,progress=lambda stage,state:events.put({'event':'progress','stage':stage,'state':state}))
            events.put({'event':'result','result':result})
        except Exception as error:
            reason=error.detail if isinstance(error,HTTPException) and isinstance(error.detail,str) else 'The assessment could not complete. Check inputs and model availability.'
            events.put({'event':'error','message':reason})
    def stream():
        worker=threading.Thread(target=work,daemon=True);worker.start()
        while True:
            event=events.get();yield json.dumps(event,allow_nan=False)+'\n'
            if event['event'] in ('result','error'):break
    return StreamingResponse(stream(),media_type='application/x-ndjson',headers={'Cache-Control':'no-store','X-Accel-Buffering':'no'})
class DrainageComparison(BaseModel):
    before:Flood
    after:Flood
@router.post('/counterfactual')
def counterfactual(body:DrainageComparison):
    from backend.simulation import simulate
    for key in ['rain_mm','duration_h','area_m2','runoff_coefficient','ponding_fraction','initial_storage_mm']:
        if getattr(body.before,key)!=getattr(body.after,key):
            from fastapi import HTTPException
            raise HTTPException(422,'Keep rainfall, catchment and duration fixed when comparing drainage assumptions.')
    a=simulate(body.before.model_dump(),repo.now(),'mass_balance')['prediction'][0]['depth_m']
    b=simulate(body.after.model_dump(),repo.now(),'mass_balance')['prediction'][0]['depth_m']
    return {'before_depth_m':a,'after_depth_m':b,'difference_m':b-a,'kind':'what_if_assessment',
            'causal_intervention_effect':False,'explanation':'Same catchment and rainfall; only declared drainage capacity/blockage changes. No pump-to-drainage effectiveness mapping is asserted.'}

@router.get('/{identifier}')
def detail(identifier:str): return repo.get('scenario',identifier)
@router.post('')
def run(body:Scenario,actor:str=Depends(admin)):
    from backend.services.city_service import city
    city(body.city_id);return execute(body,actor)
