from fastapi import APIRouter, HTTPException
from backend.services.prediction_service import predict,historical
from src.civicflux.serving import SCOPES
router=APIRouter(prefix='/api/predictions',tags=['research inference'])
def check(component):
    if component not in SCOPES: raise HTTPException(404,'Unknown component')
@router.get('/{component}/series')
def series(component:str):
    check(component)
    if component not in {'rainfall','aqi','traffic'}: raise HTTPException(422,'No supported forecast series for this component')
    import pandas as pd
    from project_paths import PROJECT_ROOT
    from src.civicflux.serving import json_safe,directory_for
    frame=pd.read_csv(directory_for(PROJECT_ROOT,component)/'test_predictions.csv').head(72)
    return {'kind':'saved holdout research results','component':component,'rows':json_safe(frame.to_dict('records'))}
@router.get('/{component}/example')
def example(component:str):
    check(component);return historical(component)
@router.get('/{component}/fixture')
def input_fixture(component:str):
    check(component)
    from src.civicflux.integration import fixture
    from project_paths import PROJECT_ROOT
    return fixture(component,PROJECT_ROOT)
@router.post('/{component}')
def inference(component:str,body:dict):
    check(component);return predict(component,body)
