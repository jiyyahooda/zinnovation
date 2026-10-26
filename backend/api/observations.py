from fastapi import APIRouter
from backend.services.observation_service import observations
router=APIRouter(prefix='/api/observations',tags=['source observations'])
@router.get('')
async def index(city_id:str='delhi'): return await observations(city_id)
