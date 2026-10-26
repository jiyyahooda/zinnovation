from fastapi import APIRouter
from backend.services.prediction_service import inventory
router=APIRouter(prefix='/api/models',tags=['model inventory'])
@router.get('')
def index(): return inventory()
