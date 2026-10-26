from typing import Literal
from datetime import datetime
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field,ConfigDict,field_validator
from backend.auth import admin
from backend.db import repository as repo
from backend.services.municipal_service import review_report,plan_review,response_options
router=APIRouter(prefix='/api/municipal',tags=['municipal workflow'])
class ReportReview(BaseModel):
    model_config=ConfigDict(extra='forbid')
    status:Literal['under_review','confirmed','assigned','in_progress','completed','verified','needs_information','rejected','deferred']
    note:str=Field(min_length=3,max_length=2000)
    assigned_to:str|None=Field(default=None,min_length=2,max_length=100)
    department:str|None=Field(default=None,min_length=2,max_length=100)
    severity:Literal['unassessed','low','medium','high']|None=None
    evidence_ref:str|None=Field(default=None,min_length=3,max_length=500)
    verification_note:str|None=Field(default=None,min_length=5,max_length=2000)
class PlanReview(BaseModel):
    method:Literal['CP-SAT','utility_greedy','severity_greedy']='CP-SAT'
    decision:Literal['approve','defer','reject','comment']
    note:str=Field(min_length=3,max_length=2000)
@router.post('/reports/{identifier}/review')
def report_review(identifier:str,body:ReportReview,actor:str=Depends(admin)):return review_report(identifier,body,actor)
@router.post('/plans/{identifier}/review')
def review_plan(identifier:str,body:PlanReview,actor:str=Depends(admin)):return plan_review(identifier,body,actor)
@router.get('/plans/{identifier}/options')
def options(identifier:str):return response_options(repo.get('scenario',identifier))
@router.get('/reviews')
def reviews():return repo.all_records('plan_review')
@router.get('/settings')
def settings(actor:str=Depends(admin)):
    import os
    from backend import config
    if actor!=config.ADMIN_ID:raise HTTPException(403,'Administrator access required.')
    from backend.services.city_service import cities
    return {'sources':[{'provider':'CPCB / OGD','configured':bool(os.getenv('CIVICFLUX_DATA_GOV_KEY')),'variable':'CIVICFLUX_DATA_GOV_KEY','setup_url':'https://www.data.gov.in/help'},
                       {'provider':'TomTom road flow','configured':bool(os.getenv('CIVICFLUX_TOMTOM_KEY')),'variable':'CIVICFLUX_TOMTOM_KEY','setup_url':'https://docs.tomtom.com/pricing'}],
            'cities':[{'id':c['id'],'name':c['name'],'model_coverage':c['research_components'],'verified_asset_mapping':c['verified_asset_mapping']} for c in cities()],
            'indian_aqi_policy':'Official source only. OGD pollutant averages do not establish validated averaging windows and completeness; a complete Indian AQI is not reconstructed from this snapshot.',
            'dispatch_connected':False,'verification_policy':'Verification requires a distinct authenticated officer and evidence; this is an auditable attestation, not automated external authentication.'}

class Officer(BaseModel):
    username:str=Field(min_length=3,max_length=80,pattern=r'^[A-Za-z0-9_.-]+$')
    password:str=Field(min_length=12,max_length=200)
    department:str=Field(min_length=3,max_length=100)
@router.post('/officers',status_code=201)
def create_officer(body:Officer,actor:str=Depends(admin)):
    from backend import config
    from backend.db.connection import connection
    import hashlib,secrets,sqlite3
    if actor!=config.ADMIN_ID:raise HTTPException(403,'Only the system administrator can create officer accounts.')
    if body.username==config.ADMIN_ID:raise HTTPException(409,'This account already exists.')
    salt=secrets.token_bytes(16);digest=hashlib.pbkdf2_hmac('sha256',body.password.encode(),salt,250000).hex()
    try:
        with connection() as db:
            db.execute('INSERT INTO officers VALUES (?,?,?,?,?)',(body.username,digest,salt.hex(),body.department,repo.now()))
            db.execute('INSERT INTO audit(created,actor,event,entity,detail) VALUES (?,?,?,?,?)',(repo.now(),actor,'officer_created',body.username,body.department))
    except sqlite3.IntegrityError:raise HTTPException(409,'This account already exists.')
    return {'username':body.username,'department':body.department,'password_returned':False}

@router.get('/officers')
def officers(actor:str=Depends(admin)):
    from backend import config
    from backend.db.connection import connection
    with connection() as db:rows=[dict(r) for r in db.execute('SELECT username,department FROM officers ORDER BY username')]
    return [{'username':config.ADMIN_ID,'department':'Municipal coordination'},*rows]
