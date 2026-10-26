"""Municipal workflow extensions on the existing JSON records and audit tables."""
import json
from fastapi import HTTPException
from backend.db import repository as repo
from backend.db.connection import connection

TRANSITIONS={
 'submitted':['under_review'], 'under_review':['confirmed','needs_information','rejected','deferred','in_progress','closed'],
 'needs_information':['under_review','rejected'], 'deferred':['under_review','rejected'],
 'confirmed':['assigned','under_review','rejected'], 'assigned':['in_progress','under_review'],
 'in_progress':['completed','under_review','closed'], 'completed':['verified','under_review'],
 'closed':['under_review','verified'], 'verified':[], 'rejected':['under_review']}

def review_report(identifier,body,actor):
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute("SELECT body FROM records WHERE kind='complaint' AND id=?",(identifier,)).fetchone()
        if not row:raise HTTPException(404,'Report not found')
        item=json.loads(row['body']);target=body.status
        if target not in TRANSITIONS.get(item['status'],[]):raise HTTPException(409,'Review this report in order; the requested status change is not permitted.')
        if target=='assigned' and (not body.assigned_to or not body.department):raise HTTPException(422,'An officer and department are required for assignment.')
        if target in ('completed','verified') and not body.evidence_ref:raise HTTPException(422,'An evidence reference is required.')
        if target=='assigned':
            from backend import config
            known=body.assigned_to==config.ADMIN_ID or db.execute('SELECT 1 FROM officers WHERE username=?',(body.assigned_to,)).fetchone()
            if not known:raise HTTPException(422,'Choose an authorized officer account for assignment.')
        stamp=repo.now();history=item.setdefault('history',[])
        if target=='verified':
            previous_actors={h.get('actor') for h in history if h['status'] in ('assigned','in_progress','completed','closed')}
            if actor in previous_actors:raise HTTPException(422,'The verifier must be a different authenticated officer from the assignment/work recorder.')
            if not body.verification_note:raise HTTPException(422,'Record what was independently checked.')
            item['verification']={'recorded_by':actor,'time':stamp,'evidence_ref':body.evidence_ref,'note':body.verification_note,'kind':'officer_attestation','externally_authenticated':False}
        item.update(status=target,updated_at=stamp,dispatch_allowed=False)
        for key in ['assigned_to','department','severity']:
            value=getattr(body,key,None)
            if value:item[key]=value
        if target=='completed':item['completion']={'time':stamp,'recorded_by':actor,'evidence_ref':body.evidence_ref}
        entry={'status':target,'note':body.note,'actor':actor,'time':stamp,'evidence_ref':body.evidence_ref,'assigned_to':item.get('assigned_to'),'department':item.get('department')}
        history.append(entry)
        db.execute('UPDATE records SET body=? WHERE id=?',(json.dumps(item,allow_nan=False),identifier))
        db.execute('INSERT INTO audit(created,actor,event,entity,detail) VALUES (?,?,?,?,?)',(stamp,actor,'report_'+target,identifier,json.dumps(entry)))
    return item

def plan_review(identifier,body,actor):
    scenario=repo.get('scenario',identifier)
    return repo.append('plan_review',{'scenario_id':identifier,'method':body.method,'decision':body.decision,'note':body.note,'reviewer':actor,
        'approval_scope':'internal_planning_only','approval_status':'approved_for_internal_planning' if body.decision=='approve' else body.decision,
        'dispatch_allowed':False,'real_outcome_verified':False},actor,'internal_plan_'+body.decision)

def response_options(scenario):
    """Readable projection of existing optimizer results; no benefit estimates invented."""
    candidates=scenario['allocation']['candidates'];case_ids={c['case_id'] for c in candidates}
    names={'CP-SAT':'Recommended plan','utility_greedy':'Benefit-first alternative','severity_greedy':'Urgent-problems-first alternative'}
    options=[]
    for method,r in scenario['allocation']['comparisons'].items():
        ids={c['case_id'] for c in r['selected']};unresolved=[c for c in candidates if c['case_id'] not in ids]
        remaining_budget=scenario['inputs']['resources']['budget']-(r.get('used') or {}).get('budget',0)
        available=scenario['inputs']['resources'];used=r.get('used') or {'pumps':0,'crew_hours':{}}
        bottlenecks=[]
        for c in unresolved:
            reasons=[]
            if c['cost']>remaining_budget:reasons.append('Budget remaining')
            if c['pumps_required']>available['pumps']-used.get('pumps',0):reasons.append('Pumps available')
            if c['duration_hours']>available['crew_hours'].get(c['crew_type'],0)-used.get('crew_hours',{}).get(c['crew_type'],0):reasons.append(c['crew_type']+' crew-hours')
            bottlenecks.append({'case_id':c['case_id'],'constraints':reasons or ['Combination of competing priorities and shared capacity']})
        options.append({'method':method,'name':names.get(method,method),'problems_addressed':len(ids),'unresolved':len(case_ids-ids),
                        'high_priority_addressed':sum(float(c.get('urgency',0))>=.8 for c in r['selected']),
                        'urgent_unresolved':sum(float(c.get('urgency',0))>=.8 for c in unresolved),
                        'budget_remaining':remaining_budget,'bottlenecks':bottlenecks,'status':r['status']})
    return {'alternatives':options,'priority_rule':'High priority in this planning exercise means candidate urgency ≥ 0.8 from the existing scenario input table.', 'expected_effect_status':'awaiting_evidence','dispatch_allowed':False}
