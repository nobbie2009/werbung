from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.services import notion_sync
from app.services.settings_manager import SETTINGS_FILE
import logging

router = APIRouter(prefix="/api", tags=["admin"])
logger = logging.getLogger(__name__)

@router.post("/trigger_sync")
async def trigger_sync():
    """Manually triggers the Notion sync process."""
    try:
        logger.info("Manual sync triggered via Admin API")
        await notion_sync.sync_notion_data()
        return {"status": "ok", "message": "Sync triggered successfully"}
    except Exception as e:
        logger.error(f"Manual sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/backup")
async def download_backup():
    """Downloads the current settings.json file."""
    if not SETTINGS_FILE.exists():
        raise HTTPException(status_code=404, detail="Settings file not found")
    
    return FileResponse(
        path=SETTINGS_FILE, 
        filename="settings_backup.json", 
        media_type="application/json"
    )
