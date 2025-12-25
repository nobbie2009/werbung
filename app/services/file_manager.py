import os
import httpx
import logging
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

MEDIA_DIR = Path("/app/data/media")

def ensure_media_dir():
    if not MEDIA_DIR.exists():
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)

async def download_file(url: str, filename: str) -> str:
    """
    Downloads a file from a URL to the local media directory.
    Returns the local file path (relative to /app/data/media).
    """
    ensure_media_dir()
    filepath = MEDIA_DIR / filename
    
    # Simple check: if file exists, we assume it's good (for MVP).
    # In a production app, we might check hashes or file headers.
    if filepath.exists():
        logger.info(f"File {filename} already exists. Skipping download.")
        return filename

    logger.info(f"Downloading {filename} from {url}...")
    try:
        async with httpx.AsyncClient() as client:
            response = client.get(url, follow_redirects=True)
            response.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(response.content)
        logger.info(f"Successfully downloaded {filename}")
        return filename
    except Exception as e:
        logger.error(f"Failed to download {filename}: {e}")
        return None

def cleanup_files(active_filenames: set):
    """
    Removes files in the media directory that are not in the active_filenames set.
    """
    ensure_media_dir()
    for file in MEDIA_DIR.iterdir():
        if file.is_file() and file.name not in active_filenames:
            try:
                os.remove(file)
                logger.info(f"Removed orphaned file: {file.name}")
            except Exception as e:
                logger.error(f"Error removing file {file.name}: {e}")
