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
PROPERTY_DESCRIPTION = "Description"
PROPERTY_MEDIA = "Media"
PROPERTY_START = "Start" # Support legacy
PROPERTY_DATE = "Date" # Standard Notion name
PROPERTY_END = "End"
PROPERTY_DURATION = "Duration"
PROPERTY_ACTIVE = "Active"
PROPERTY_LAYOUT = "Layout" # New
PROPERTY_ORDER = "Order" # Sort order
PROPERTY_UNSPLASH = "Unsplash" # Unsplash URL or ID

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
        logger.info(f"Notion returned {len(results)} results.")
        
        active_slides = []
        active_filenames = set()
        
        now = datetime.now(timezone.utc)
        logger.info(f"Current UTC time: {now}")

        for page in results:
            props = page.get("properties", {})
            
            # Extract basic info
            title_list = props.get(PROP_NAME, {}).get("title", [])
            title = title_list[0]["plain_text"] if title_list else "Untitled"
            
            # Check Active Checkbox
            is_active_checkbox = props.get(PROPERTY_ACTIVE, {}).get("checkbox", True)
            if not is_active_checkbox:
                logger.info(f"Skipping '{title}': Active checkbox is unchecked.")
                continue

            # Check Dates (Support 'Date' or 'Start')
            date_prop = props.get(PROPERTY_DATE, {}).get("date") or props.get(PROPERTY_START, {}).get("date")
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
                logger.info(f"Skipping '{title}': Starts in future ({start_date}).")
                continue
            if end_date and now > end_date:
                logger.info(f"Skipping '{title}': Ended in past ({end_date}).")
                continue

            # Extract Media
            files = props.get(PROPERTY_MEDIA, {}).get("files", [])
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
            
            # Unsplash Fallback
            if not media_url:
                unsplash_val = props.get(PROPERTY_UNSPLASH, {}).get("url") or props.get(PROPERTY_UNSPLASH, {}).get("rich_text", [])
                unsplash_url = None
                if isinstance(unsplash_val, list) and len(unsplash_val) > 0:
                    unsplash_url = unsplash_val[0].get("plain_text")
                elif isinstance(unsplash_val, str):
                    unsplash_url = unsplash_val
                
                if unsplash_url:
                    logger.info(f"Processing Unsplash Property: {unsplash_url}")
                    # Extract ID from https://unsplash.com/photos/xxxx or just xxxx
                    try:
                        parsed = urlparse(unsplash_url)
                        if "unsplash.com" in parsed.netloc and "/photos/" in parsed.path:
                             photo_id = parsed.path.split("/photos/")[-1]
                             download_url = f"https://unsplash.com/photos/{photo_id}/download"
                             local_filename = f"unsplash_{photo_id}.jpg"
                             
                             logger.info(f"Unsplash ID: {photo_id} | Download URL: {download_url}")

                             result = await file_manager.download_file(download_url, local_filename)
                             if result:
                                 active_filenames.add(local_filename)
                                 media_type = "image"
                             else:
                                 logger.error(f"Failed to download Unsplash image: {download_url}")
                                 local_filename = None # Fallback to text
                        else:
                             logger.warning(f"Invalid Unsplash URL format: {unsplash_url}. Expected format with '/photos/ID'.")
                    except Exception as e:
                        logger.error(f"Error processing Unsplash url: {e}")
                        local_filename = None

            # Extract Duration
            duration = props.get(PROPERTY_DURATION, {}).get("number", 10) or 10
            
            # Extract Description
            desc_list = props.get(PROPERTY_DESCRIPTION, {}).get("rich_text", [])
            description = "".join([t["plain_text"] for t in desc_list])

            # Extract Layout
            layout_select = props.get(PROPERTY_LAYOUT, {}).get("select")
            layout = layout_select["name"] if layout_select else "Standard"

            # Extract Order
            order = props.get(PROPERTY_ORDER, {}).get("number", 999) or 999

            slide = {
                "id": page["id"],
                "title": title,
                "description": description,
                "type": media_type,
                "src": f"/media/{local_filename}" if local_filename else None,
                "duration": duration,
                "layout": layout,
                "order": order
            }
            active_slides.append(slide)

        # Sort by Order
        active_slides.sort(key=lambda x: x["order"])

        # Write to playlist.json
        with open(PLAYLIST_FILE, "w") as f:
            json.dump(active_slides, f, indent=2)
            
        logger.info(f"Sync complete. {len(active_slides)} active slides found.")
        
        # Cleanup
        file_manager.cleanup_files(active_filenames)

    except Exception as e:
        logger.error(f"Error during Notion sync: {e}")
