from fastapi import APIRouter, HTTPException
import subprocess
import sys
import time
import logging
from pathlib import Path

router = APIRouter(prefix="/api/system", tags=["system"])
logger = logging.getLogger(__name__)

# Store startup time as logical "version"
STARTUP_TIME = int(time.time())

# Fetch Git Commit Hash
COMMIT_HASH = "unknown"
try:
    COMMIT_HASH = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], 
        cwd="/app", 
        text=True
    ).strip()
except Exception as e:
    logger.warning(f"Failed to get git commit hash: {e}")

@router.get("/version")
async def get_version():
    """Returns server startup timestamp and git commit hash."""
    return {
        "version": STARTUP_TIME,
        "commit": COMMIT_HASH
    }

@router.post("/update")
async def trigger_update():
    """
    Triggers a git pull and restarts the application.
    """
    try:
        logger.info("Starting system update via git pull...")
        # 1. Git Pull
        result = subprocess.run(
            ["git", "pull"], 
            capture_output=True, 
            text=True, 
            cwd="/app" 
        )
        
        if result.returncode != 0:
            logger.error(f"Git pull failed: {result.stderr}")
            raise HTTPException(status_code=500, detail=f"Git pull failed: {result.stderr}")
        
        logger.info(f"Git pull successful: {result.stdout}")

        # 2. Restart Application (Exit process, rely on Docker restart policy)
        # We start a delayed exit to allow the response to return to the client
        try:
             # We can't easily schedule a sys.exit in an async loop without blocking. 
             # But uvicorn handles sys.exit() gracefully typically.
             # We'll rely on the client receiving the 200 OK before the server dies.
             pass
        except: 
             pass
        
        # Schedule exit?
        import threading
        def kill_server():
            time.sleep(1)
            logger.info("Restarting server process...")
            sys.exit(0)
            
        threading.Thread(target=kill_server).start()

        return {"status": "success", "message": "Update successful. Server restarting..."}

    except Exception as e:
        logger.error(f"Update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
