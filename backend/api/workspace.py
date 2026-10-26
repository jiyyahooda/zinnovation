from fastapi import APIRouter
from backend.services.city_service import city
from backend.services.live_service import refresh_city
from backend.services.workspace_service import workspace
router=APIRouter(prefix='/api/workspace',tags=['geographic workspace'])
@router.get('')
def index(city_id:str='delhi'):return workspace(city_id)
@router.get('/refresh')
async def refresh(city_id:str='delhi'):
    city(city_id);await refresh_city(city_id);return workspace(city_id)
@router.get('/history')
def history(city_id:str='delhi'):
    import json
    from backend.db.connection import connection
    city(city_id)
    with connection() as db:rows=db.execute('SELECT provider,retrieved_at,payload FROM live_history WHERE city=? ORDER BY retrieved_at DESC LIMIT 100',(city_id,)).fetchall()
    return [dict(provider=r['provider'],retrieved_at=r['retrieved_at'],points=json.loads(r['payload'])) for r in rows]
