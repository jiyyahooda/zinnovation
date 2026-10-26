import json
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import HTTPException
from .connection import connection
from .schema import SQL

def now(): return datetime.now(timezone.utc).isoformat()

def initialize():
    with connection() as db: db.executescript(SQL)

def append(kind, body, actor='civilian', event='created'):
    item = {**body, 'id':str(uuid4()), 'created':now()}
    with connection() as db:
        db.execute('INSERT INTO records VALUES (?,?,?,?)', (item['id'], kind, item['created'], json.dumps(item, allow_nan=False)))
        db.execute('INSERT INTO audit(created,actor,event,entity,detail) VALUES (?,?,?,?,?)', (now(),actor,event,item['id'],json.dumps({'kind':kind})))
    return item

def all_records(kind):
    with connection() as db:
        return [json.loads(r['body']) for r in db.execute('SELECT body FROM records WHERE kind=? ORDER BY created DESC',(kind,))]

def get(kind, identifier):
    with connection() as db: row=db.execute('SELECT body FROM records WHERE kind=? AND id=?',(kind,identifier)).fetchone()
    if row is None: raise HTTPException(404, 'Record not found')
    return json.loads(row['body'])

def update_complaint(identifier, status, note, actor):
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute("SELECT body FROM records WHERE kind='complaint' AND id=?",(identifier,)).fetchone()
        if row is None: raise HTTPException(404,'Complaint not found')
        item=json.loads(row['body']); previous=item['status']
        transitions={'submitted':['under_review'], 'under_review':['in_progress','closed'], 'in_progress':['closed','under_review'], 'closed':['under_review']}
        if status not in transitions.get(previous,[]): raise HTTPException(409,'Invalid complaint transition')
        item['status']=status;item['history'].append({'status':status,'note':note,'actor':actor,'time':now()})
        db.execute('UPDATE records SET body=? WHERE id=?',(json.dumps(item),identifier))
        db.execute('INSERT INTO audit(created,actor,event,entity,detail) VALUES (?,?,?,?,?)',(now(),actor,'complaint_review',identifier,note))
    return item

def audit():
    with connection() as db: return [dict(r) for r in db.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 500')]
