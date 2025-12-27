import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.routers import api, settings, admin_actions, system
from app.services.notion_sync import sync_notion_data
from app.services import calendar_service
from app.services.settings_manager import settings_manager

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# Ensure directories exist
Path("/app/data/media").mkdir(parents=True, exist_ok=True)
Path("app/static").mkdir(parents=True, exist_ok=True)

async def run_calendar_sync():
    """Fetches calendar data and updates settings cache."""
    try:
        current_settings = settings_manager.get_settings()
        if current_settings.get("countdown_mode") == "calendar":
            ical_url = current_settings.get("calendar_url")
            keyword = current_settings.get("calendar_filter")
            
            if ical_url:
                logger.info("Syncing Calendar...")
                title, start_time = await calendar_service.fetch_next_event(ical_url, keyword)
                if title and start_time:
                    settings_manager.update_calendar_cache(title, start_time.isoformat())
                else:
                    logger.info("No matching future event found in calendar.")
                    # Optionally clear cache or keep old? 
                    # Keeping old is safer vs blinking, but might show old stuff.
                    # Let's keep old for now or clear if specifically desired.
    except Exception as e:
        logger.error(f"Calendar sync failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Digital Signage Middleware...")
    
    # Start Scheduler
    scheduler = AsyncIOScheduler()
    interval = int(os.getenv("SYNC_INTERVAL", 300)) # Default 5 mins
    
    scheduler.add_job(sync_notion_data, 'interval', seconds=interval)
    scheduler.add_job(run_calendar_sync, 'interval', seconds=300) # Sync calendar every 5 mins
    
    scheduler.start()
    logger.info(f"Scheduler started with interval {interval}s")

    # Initial Sync
    try:
        await sync_notion_data()
        await run_calendar_sync() # Initial calendar check
    except Exception as e:
        logger.warning(f"Initial sync failed: {e}")

    yield
    logger.info("Shutting down...")

app = FastAPI(lifespan=lifespan)

# Mounts
app.mount("/media", StaticFiles(directory="/app/data/media"), name="media")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(api.router, prefix="/api")
app.include_router(settings.router, prefix="/api/settings")
app.include_router(admin_actions.router)
app.include_router(system.router)

templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})
