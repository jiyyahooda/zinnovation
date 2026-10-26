from fastapi import HTTPException
from src.civicflux.integration import review_proposal
from backend.db import repository as repo

def review(identifier,decision,note,actor):
    scenario=repo.get('scenario',identifier)
    try: result=review_proposal({'proposal_id':identifier},decision,actor,True)
    except ValueError as error: raise HTTPException(409,str(error)) from error
    return repo.append('review',{**result,'scenario_id':scenario['id'],'note':note},actor,'human_review')

def verification(identifier,body,actor):
    scenario=repo.get('scenario',identifier)
    from datetime import datetime
    if body.completion_time<datetime.fromisoformat(scenario['created']): raise HTTPException(422,'Completion cannot precede the scenario')
    reviews=[r for r in repo.all_records('review') if r['scenario_id']==identifier]
    if not reviews: raise HTTPException(409,'Record a human review before independent outcome evidence')
    if body.verifier==actor or any(r['reviewer']==body.verifier for r in reviews): raise HTTPException(422,'Verifier must differ from the reviewer and evidence recorder')
    return repo.append('verification',{'scenario_id':identifier,**body.model_dump(),'recorded_by':actor,'status':'simulation_evidence_recorded','independence':'named external verifier; identity/evidence not independently authenticated','real_outcome_verified':False,'dispatch_allowed':False},actor,'outcome_evidence_recorded')
