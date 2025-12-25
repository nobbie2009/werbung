from fastapi import APIRouter, HTTPException, Body
from app.services.settings_manager import settings_manager

router = APIRouter()

@router.get("/")
async def get_settings():
    return settings_manager.get_settings()

@router.post("/")
async def update_settings(settings: dict = Body(...)):
    try:
        updated = settings_manager.save_settings(settings)
        return updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
