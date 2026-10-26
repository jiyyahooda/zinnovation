"""Synthetic outcome study and noncausal record/verification contract."""
from dataclasses import dataclass
from datetime import datetime,timezone
import numpy as np
import pandas as pd

VERSION='1.0.0'
REQUIRED=['incident_id','intervention_id','intervention_type','initial_severity','planned_crew_type','planned_crew_count','planned_pump_count','planned_cost','risk_score_at_assignment','assignment_time','completion_time','status','outcome_status','verified_success','verified_by','verification_time','resolution_hours','evidence_ref','source_type']
FEATURES=['intervention_type','initial_severity','planned_crew_type','planned_crew_count','planned_pump_count','planned_cost','risk_score_at_assignment']

def validate_outcome_record(record):
    missing=set(REQUIRED)-set(record)
    if missing:raise ValueError(f'Missing outcome fields: {sorted(missing)}')
    if record['status'] not in {'proposed','approved','in_progress','completed','cancelled'}:raise ValueError('Invalid intervention status')
    if record['outcome_status'] not in {'unverified','verified_success','verified_failure','unknown'}:raise ValueError('Invalid outcome_status')
    if not pd.isna(record['verified_success']) and record['outcome_status'] not in {'verified_success','verified_failure'}:raise ValueError('Success label requires independent verification status')
    if record['outcome_status'] in {'verified_success','verified_failure'}:
        if record['status']!='completed' or not record['verified_by'] or not record['verification_time'] or not record['evidence_ref']:
            raise ValueError('Verified outcome requires completion, verifier, timestamp and evidence reference')
    if record['status']!='completed' and pd.notna(record['completion_time']):raise ValueError('Only completed work may have a completion time')
    if record['completion_time'] is not None and record['assignment_time'] is not None and pd.Timestamp(record['completion_time'])<pd.Timestamp(record['assignment_time']):raise ValueError('Completion precedes assignment')
    if record['resolution_hours'] is not None and record['resolution_hours']<0:raise ValueError('Resolution time cannot be negative')
    if pd.isna(record['assignment_time']) or pd.isna(pd.Timestamp(record['assignment_time'])):raise ValueError('Assignment timestamp is required')
    if record['status']=='completed' and (pd.isna(record['completion_time']) or pd.isna(pd.Timestamp(record['completion_time']))):raise ValueError('Completed work needs a completion timestamp')
    if record['outcome_status'] in {'verified_success','verified_failure'}:
        for field in ['verified_by','evidence_ref']:
            if not isinstance(record[field],str) or not record[field].strip():raise ValueError('Independent verifier and evidence must be nonempty strings')
        if pd.isna(pd.Timestamp(record['verification_time'])):raise ValueError('Valid verification timestamp is required')
        if pd.isna(record['verified_success']) or bool(record['verified_success'])!=(record['outcome_status']=='verified_success'):raise ValueError('Verification status and success label disagree')
        if pd.isna(record['verification_time']) or pd.Timestamp(record['verification_time'])<pd.Timestamp(record['completion_time']):raise ValueError('Verification precedes completion')
    return dict(record)

def verify_outcome(record,success,verifier,evidence_ref,when=None):
    """Require completed work and independent evidence before adding a label."""
    r=dict(record)
    if not isinstance(success,(bool,np.bool_)):raise ValueError('Verification success must be boolean')
    if r.get('status')!='completed':raise ValueError('Cannot verify an incomplete/cancelled intervention')
    if not isinstance(verifier,str) or not verifier.strip() or not isinstance(evidence_ref,str) or not evidence_ref.strip():raise ValueError('Independent verifier and evidence reference are required')
    if r.get('source_type')=='synthetic':raise ValueError('Simulation outcomes cannot be promoted to real verified outcomes')
    r.update(outcome_status='verified_success' if success else 'verified_failure',verified_success=bool(success),verified_by=verifier,
             verification_time=when or datetime.now(timezone.utc).isoformat(),evidence_ref=evidence_ref)
    return validate_outcome_record(r)

def generate_synthetic_outcomes(n=6000,seed=42):
    """Educational mechanism-generated records with endogenous intervention choice.

    Outcomes are synthetic assumptions; treatment assignment depends on risk,
    so associations are intentionally not causal intervention effects.
    """
    rng=np.random.default_rng(seed);t=pd.date_range('2019-01-01','2025-01-01',freq='h')
    chosen=rng.choice(len(t),n,replace=False);assignment=t[chosen]
    types=np.array(['pump_repair','pipe_repair','drain_clear','road_barrier'])
    kinds=rng.choice(types,n,p=[.23,.29,.31,.17])
    severity=rng.integers(1,6,n);crew=np.where(kinds=='road_barrier','road',np.where(kinds=='drain_clear','drain','water'))
    risk=np.clip(.1+.16*severity+rng.normal(0,.12,n),0,1)
    crew_count=np.where(severity>=4,3,2);pump_count=np.where(kinds=='pump_repair',rng.integers(1,3,n),0)
    cost=np.maximum(1000,np.round((1800+severity*900+pump_count*2200+rng.normal(0,1000,n))/100)*100).astype(int)
    # Allocation is associated with severity; success mechanism includes confounding by resource assignment.
    lp=1.2-.45*severity+.65*(crew_count-2)+.35*(kinds=='pipe_repair')-.25*pump_count+.2*(kinds=='drain_clear')
    prob=1/(1+np.exp(-lp));success=rng.binomial(1,prob)
    logtime=2.5+.34*severity-.32*crew_count+.22*pump_count+rng.normal(0,.5,n)
    resolution=np.clip(np.exp(logtime),1,240)
    complete=rng.random(n)<.94;completion=assignment+pd.to_timedelta(resolution,unit='h')
    verify_delay=rng.integers(1,49,n);verified=complete&(rng.random(n)<.63)
    outcome=np.where(~complete,'unverified',np.where(verified,np.where(success==1,'verified_success','verified_failure'),'unverified'))
    records=pd.DataFrame({'incident_id':[f'SYN-I-{i:06}' for i in range(n)],'intervention_id':[f'SYN-A-{i:06}' for i in range(n)],
        'intervention_type':kinds,'initial_severity':severity,'planned_crew_type':crew,'planned_crew_count':crew_count,
        'planned_pump_count':pump_count,'planned_cost':cost,'risk_score_at_assignment':risk,'assignment_time':assignment,
        'completion_time':[t if ok else pd.NaT for t,ok in zip(completion,complete)],'status':np.where(complete,'completed','in_progress'),
        'outcome_status':outcome,'verified_success':np.where(verified,success,np.nan),'verified_by':np.where(verified,'independent_simulated_auditor',None),
        'verification_time':[t+pd.Timedelta(hours=d) if ok else pd.NaT for t,d,ok in zip(completion,verify_delay,verified)],
        'resolution_hours':np.where(complete,resolution,np.nan),'evidence_ref':np.where(verified,'synthetic-simulation-record',None),
        'source_type':'synthetic','event_group':[f'SYN-G-{i:06}' for i in range(n)],'underlying_simulated_success':success,
        'latent_success_probability':prob,'expected_cost_assumption':cost})
    return records

def leakage_safe_features(records):
    """Only plan and baseline covariates known when assignment is made."""
    return records[FEATURES].copy()

@dataclass
class OutcomeBundle:
    success_model:object
    duration_model:object
    feature_schema:list
    metadata:dict
    def predict(self,record,purpose='research'):
        missing=set(FEATURES)-set(record)
        if missing:raise ValueError(f'Unsupported input; missing {sorted(missing)}')
        if record['intervention_type'] not in {'pump_repair','pipe_repair','drain_clear','road_barrier'}:raise ValueError('Unknown intervention type')
        if record['planned_crew_type'] not in {'water','road','drain'}:raise ValueError('Unknown crew type')
        numeric=[k for k in FEATURES if k not in {'intervention_type','planned_crew_type'}]
        if any(not np.isfinite(float(record[k])) for k in numeric):raise ValueError('Missing or invalid numeric inputs')
        if not 1<=float(record['initial_severity'])<=5 or not 0<=float(record['risk_score_at_assignment'])<=1:raise ValueError('Unsupported severity/risk')
        if any(float(record[k])<0 for k in ['planned_crew_count','planned_pump_count','planned_cost']):raise ValueError('Negative resource input')
        if purpose!='research':
            return {'component':'intervention_outcome_research','version':self.metadata.get('version',VERSION),'status':'abstained',
                    'prediction_success_probability':None,'predicted_resolution_hours':None,'dispatch_allowed':False,'causal_effect':None,
                    'warnings':['Synthetic outcome models cannot support operational success estimates.']}
        x=pd.DataFrame([{k:record[k] for k in FEATURES}])
        p=float(self.success_model.predict_proba(x)[0,1])
        hours=float(np.expm1(self.duration_model.predict(x)[0])) if self.metadata.get('duration_log1p') else float(self.duration_model.predict(x)[0])
        return {'component':'intervention_outcome_research','version':self.metadata.get('version',VERSION),'source_type':'synthetic_research_surrogate',
                'status':'supported_research','operational_supported':False,'allocation_eligible':False,
                'prediction_success_probability':None,'research_success_score':p,'predicted_resolution_hours':max(0,hours),'causal_effect':None,
                'requires_human_review':True,'auto_approve':False,'dispatch_allowed':False,
                'warnings':['Synthetic records only; model does not estimate the causal benefit of an intervention.',
                            'Do not use as a real success probability or approval decision.']}
