import json
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()
PLAYLIST_FILE = Path("/app/data/playlist.json")

@router.get("/playlist")
async def get_playlist():
    if not PLAYLIST_FILE.exists():
        return []
    
    try:
        with open(PLAYLIST_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []
