import os
import json
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse
from pathlib import Path
from notion_client import AsyncClient
from app.services import file_manager

logger = logging.getLogger(__name__)

# Constants for Notion Properties
PROP_NAME = "Name"
PROP_DESCRIPTION = "Description"
PROP_MEDIA = "Media"
PROP_START = "Start"
PROP_END = "End"
PROP_DURATION = "Duration"
PROP_ACTIVE = "Active"

PLAYLIST_FILE = Path("/app/data/playlist.json")

async def sync_notion_data():
    """
    Main sync function.
    1. Fetch unique block/pages from Notion Database.
    2. Filter by date/active status.
    3. Download media.
    4. Update playlist.json.
    """
    token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")

    if not token or not database_id:
        logger.warning("NOTION_TOKEN or NOTION_DATABASE_ID not set. Skipping sync.")
        return

    client = AsyncClient(auth=token)
    
    try:
        logger.info("Querying Notion Database...")
        query = await client.databases.query(database_id=database_id)
        results = query.get("results", [])
        
        active_slides = []
        active_filenames = set()
        
        now = datetime.now(timezone.utc)

        for page in results:
            props = page.get("properties", {})
            
            # Extract basic info
            title_list = props.get(PROP_NAME, {}).get("title", [])
            title = title_list[0]["plain_text"] if title_list else "Untitled"
            
            # Check Active Checkbox
            is_active_checkbox = props.get(PROP_ACTIVE, {}).get("checkbox", True)
            if not is_active_checkbox:
                continue

            # Check Dates
            date_prop = props.get(PROP_START, {}).get("date")
            start_date = None
            end_date = None
            
            if date_prop:
                start_str = date_prop.get("start")
                end_str = date_prop.get("end")
                if start_str:
                    d = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    if d.tzinfo is None:
                         d = d.replace(tzinfo=timezone.utc)
                    start_date = d
                if end_str:
                    d = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                    if d.tzinfo is None:
                         d = d.replace(tzinfo=timezone.utc)
                    end_date = d

            # Logic: If start_date is set, must be after it. If end_date is set, must be before it.
            if start_date and now < start_date:
                continue
            if end_date and now > end_date:
                continue

            # Extract Media
            files = props.get(PROP_MEDIA, {}).get("files", [])
            media_url = None
            media_type = "text"
            local_filename = None

            if files:
                f = files[0]
                # Notion file objects have 'file' or 'external' keys
                if "file" in f:
                    media_url = f["file"]["url"]
                elif "external" in f:
                    media_url = f["external"]["url"]
                
                if media_url:
                    # Determine filename (use page ID + extension or sanitized name)
                    # Using page ID is safer for uniqueness
                    ext = os.path.splitext(urlparse(media_url).path)[1]
                    if not ext:
                        ext = ".jpg" # Default fallback
                    
                    local_filename = f"{page['id']}{ext}"
                    
                    # Download
                    await file_manager.download_file(media_url, local_filename)
                    active_filenames.add(local_filename)
                    
                    # Determine type
                    if ext.lower() in ['.mp4', '.mov', '.webm']:
                        media_type = "video"
                    else:
                        media_type = "image"

            # Extract Duration
            duration = props.get(PROP_DURATION, {}).get("number", 10) or 10
            
            # Extract Description
            desc_list = props.get(PROP_DESCRIPTION, {}).get("rich_text", [])
            description = "".join([t["plain_text"] for t in desc_list])

            # Skip if no media
            if not local_filename:
                continue

            slide = {
                "id": page["id"],
                "title": title,
                "description": description,
                "type": media_type,
                "src": f"/media/{local_filename}",
                "duration": duration
            }
            active_slides.append(slide)

        # Write to playlist.json
        with open(PLAYLIST_FILE, "w") as f:
            json.dump(active_slides, f, indent=2)
            
        logger.info(f"Sync complete. {len(active_slides)} active slides found.")
        
        # Cleanup
        file_manager.cleanup_files(active_filenames)

    except Exception as e:
        logger.error(f"Error during Notion sync: {e}")
