import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

SETTINGS_FILE = Path("/app/data/settings.json")

DEFAULT_SETTINGS = {
    "theme": "dark",
    "background_color": "#000000",
    "text_color": "#ffffff",
    "screensaver_enabled": False,
    "screensaver_timeout": 300, # seconds
    "screensaver_type": "black", # black, image
    "custom_css": "",
    # Corporate Identity & Contact
    "logo_url": "",
    "contact_name": "",
    "contact_phone": "",
    "contact_homepage": "",
    # Countdown
    "countdown_enabled": False,
    "countdown_target": "", # ISO date string
    "countdown_enabled": False,
    "countdown_target": "", # ISO date string
    "countdown_title": "Countdown",
    # Appearance
    "font_scale": 100 # Percentage
}

class SettingsManager:
    def __init__(self):
        self._ensure_file()

    def _ensure_file(self):
        if not SETTINGS_FILE.exists():
            self.save_settings(DEFAULT_SETTINGS)

    def get_settings(self) -> Dict[str, Any]:
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                # Merge with defaults to ensure all keys exist
                return {**DEFAULT_SETTINGS, **data}
        except Exception as e:
            logger.error(f"Failed to read settings: {e}")
            return DEFAULT_SETTINGS

    def save_settings(self, new_settings: Dict[str, Any]):
        try:
            # Load current to merge if exists
            current = {}
            if SETTINGS_FILE.exists():
                current = self.get_settings()
            
            updated = {**current, **new_settings}
            
            with open(SETTINGS_FILE, "w") as f:
                json.dump(updated, f, indent=2)
            logger.info("Settings saved")
            return updated
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            raise e

settings_manager = SettingsManager()
