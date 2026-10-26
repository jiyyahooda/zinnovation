"""Persistent last-good feeds, single-flight polling and provider backoff."""
import asyncio,json,os
from datetime import datetime,timezone,timedelta
from backend.db.connection import connection
from backend.integrations import live
from backend.services.city_service import city,cities
_locks={}
PROVIDERS={'weather':live.weather,'air':live.air,'stations':live.stations,'traffic':live.traffic}
def initialize():
    with connection() as db:db.executescript("CREATE TABLE IF NOT EXISTS live_feeds(city TEXT,provider TEXT,payload TEXT,last_success TEXT,last_attempt TEXT,next_attempt TEXT,error TEXT,PRIMARY KEY(city,provider)); CREATE TABLE IF NOT EXISTS live_history(city TEXT,provider TEXT,retrieved_at TEXT,payload TEXT);")
def now():return datetime.now(timezone.utc)
def read(identifier,provider):
    initialize()
    with connection() as db:r=db.execute('SELECT * FROM live_feeds WHERE city=? AND provider=?',(identifier,provider)).fetchone()
    return dict(r) if r else None
async def refresh(identifier,provider):
    c=city(identifier)
    async with _locks.setdefault((identifier,provider),asyncio.Lock()):
        state=read(identifier,provider);clock=now()
        credential_added=state and state['error'] in ('Station API credential is not configured','Traffic API credential is not configured') and bool(os.getenv({'stations':'CIVICFLUX_DATA_GOV_KEY','traffic':'CIVICFLUX_TOMTOM_KEY'}.get(provider,'')))
        if state and not credential_added and state['next_attempt'] and datetime.fromisoformat(state['next_attempt'])>clock:return
        try:
            points=await PROVIDERS[provider](c)
            if not points:raise ValueError('Empty readings')
            payload=json.dumps(points,allow_nan=False);stamp=now().isoformat()
            with connection() as db:
                db.execute('INSERT OR REPLACE INTO live_feeds VALUES (?,?,?,?,?,?,?)',(identifier,provider,payload,stamp,clock.isoformat(),(clock+timedelta(minutes=30 if provider=='traffic' else 60 if provider=='stations' else 10)).isoformat(),None))
                db.execute('INSERT INTO live_history VALUES (?,?,?,?)',(identifier,provider,stamp,payload))
                db.execute('DELETE FROM live_history WHERE retrieved_at<?',((clock-timedelta(days=7)).isoformat(),))
        except Exception as e:
            error=str(e) if isinstance(e,live.ProviderError) else 'Provider payload failed schema/unit/time validation'
            delay=e.retry_after if isinstance(e,live.ProviderError) else 120
            with connection() as db:db.execute('INSERT OR REPLACE INTO live_feeds VALUES (?,?,?,?,?,?,?)',(identifier,provider,state['payload'] if state else '[]',state['last_success'] if state else None,clock.isoformat(),(clock+timedelta(seconds=delay)).isoformat(),error))
def snapshot(identifier):
    c=city(identifier);feeds=[];points=[];clock=now()
    for provider in PROVIDERS:
        state=read(identifier,provider);rows=json.loads(state['payload']) if state else []
        for p in rows:
            age=(clock-datetime.fromisoformat(p.get('observed_at') or p['retrieved_at'])).total_seconds()
            p.update(age_seconds=max(0,age),status='stale' if age>10800 or state['error'] else 'fresh');points.append(p)
        feeds.append(dict(source=provider,status=('stale' if state['error'] or any(p['status']=='stale' for p in rows) else 'fresh') if rows else ('unavailable' if state else 'connecting'),reason=state['error'] if state else 'First ingestion in progress',last_success=state['last_success'] if state else None,last_attempt=state['last_attempt'] if state else None,next_attempt=state['next_attempt'] if state else None,points=len(rows)))
    return dict(city_id=identifier,center=c['center'],checked_at=clock.isoformat(),feeds=feeds,points=points,coverage=dict(research_components=c['research_components'],verified_asset_mapping=c['verified_asset_mapping']))
async def refresh_city(identifier):await asyncio.gather(*(refresh(identifier,p) for p in PROVIDERS))
async def poll():
    while True:
        try: await asyncio.gather(*(refresh_city(c['id']) for c in cities()))
        except Exception:
            import logging
            logging.getLogger(__name__).exception('Live polling cycle failed; retrying next cycle')
        await asyncio.sleep(60)
