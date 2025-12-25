import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.routers import api, settings, admin_actions
from app.services.notion_sync import sync_notion_data

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# Ensure directories exist
Path("/app/data/media").mkdir(parents=True, exist_ok=True)
Path("app/static").mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Digital Signage Middleware...")
    
    # Start Scheduler
    scheduler = AsyncIOScheduler()
    interval = int(os.getenv("SYNC_INTERVAL", 300)) # Default 5 mins
    scheduler.add_job(sync_notion_data, 'interval', seconds=interval)
    scheduler.start()
    logger.info(f"Scheduler started with interval {interval}s")

    # Initial Sync (Non-blocking or blocking? Blocking is better for first load)
    # But if Notion is down, it delays startup. Let's do it background or just warn.
    # For now, let's await it so the user sees something immediately if credentials are right.
    try:
        await sync_notion_data()
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

templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})
