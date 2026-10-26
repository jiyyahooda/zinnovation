from datetime import datetime
from typing import Literal
from fastapi import APIRouter,Depends
from pydantic import BaseModel,Field,model_validator
from backend.auth import admin
from backend.db import repository as repo
from backend.services.feedback_service import review,verification
router=APIRouter(prefix='/api',tags=['human review and community'])
class Review(BaseModel):
    decision:Literal['pending','defer','reject','approve']
    note:str=Field(min_length=3,max_length=2000)
class Verification(BaseModel):
    verifier:str=Field(min_length=3,max_length=100)
    evidence_ref:str=Field(min_length=3,max_length=500)
    success:bool
    completion_time:datetime
    verification_time:datetime
    note:str=Field(min_length=3,max_length=2000)
    @model_validator(mode='after')
    def chronology(self):
        from datetime import timezone
        if self.completion_time.tzinfo is None or self.verification_time.tzinfo is None: raise ValueError('Timezone-aware timestamps required')
        if self.verification_time<self.completion_time or self.verification_time>datetime.now(timezone.utc): raise ValueError('Invalid outcome chronology')
        return self
    def model_dump(self,**kwargs): return super().model_dump(mode='json',**kwargs)
class Complaint(BaseModel):
    city_id:str
    category:Literal['waterlogging','road','drainage','water','air_quality','traffic','infrastructure','other']
    location:str=Field(min_length=3,max_length=200)
    description:str=Field(min_length=8,max_length=2000)
    severity:Literal['unassessed','low','medium','high']='unassessed'
    evidence_ref:str|None=Field(default=None,min_length=3,max_length=500)
    latitude:float|None=Field(default=None,ge=-90,le=90,allow_inf_nan=False)
    longitude:float|None=Field(default=None,ge=-180,le=180,allow_inf_nan=False)
    @model_validator(mode='after')
    def coordinates(self):
        if (self.latitude is None)!=(self.longitude is None):raise ValueError('Supply both latitude and longitude')
        return self
class ComplaintReview(BaseModel):
    status:Literal['under_review','in_progress','closed']
    note:str=Field(min_length=3,max_length=2000)
@router.get('/feedback')
def feedback(): return {'reviews':repo.all_records('review'),'verifications':repo.all_records('verification')}
@router.post('/feedback/{identifier}/review')
def review_scenario(identifier:str,body:Review,actor:str=Depends(admin)): return review(identifier,body.decision,body.note,actor)
@router.post('/feedback/{identifier}/verification')
def verify(identifier:str,body:Verification,actor:str=Depends(admin)): return verification(identifier,body,actor)
@router.get('/complaints')
def complaints(): return repo.all_records('complaint')
@router.post('/complaints',status_code=201)
def complain(body:Complaint):
    from backend.services.city_service import city
    c=city(body.city_id)
    if body.latitude is not None and (abs(body.latitude-c['center'][0])>.5 or abs(body.longitude-c['center'][1])>.5):
        from fastapi import HTTPException
        raise HTTPException(422,'Coordinates outside selected city reporting area (±0.5 degrees)')
    return repo.append('complaint',{**body.model_dump(),'status':'submitted','history':[],'claim_type':'citizen_report','dispatch_allowed':False,'verification':None,'provenance':'Unverified civilian submission; stored locally, not sent to government'})
@router.post('/complaints/{identifier}')
def update(identifier:str,body:ComplaintReview,actor:str=Depends(admin)): return repo.update_complaint(identifier,body.status,body.note,actor)
@router.get('/audit')
def audit(actor:str=Depends(admin)): return repo.audit()
