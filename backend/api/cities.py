from fastapi import APIRouter
from backend.services.city_service import cities,city
router=APIRouter(prefix='/api/cities',tags=['cities'])
@router.get('')
def index(): return cities()
@router.get('/{identifier}')
def detail(identifier:str): return city(identifier)
