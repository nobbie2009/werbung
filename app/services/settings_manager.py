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
    "countdown_mode": "manual", # manual, calendar
    "countdown_target": "", # ISO date string (used for manual)
    "calendar_url": "", # iCal URL
    "calendar_filter": "", # Keyword filter
    "countdown_title": "Countdown",
    "countdown_show_timer": True,
    "countdown_show_date": True,
    # Appearance
    "font_scale": 100 # Percentage
}

class SettingsManager:
    def __init__(self):
        self._ensure_file()
        self._calendar_state = {}

    def _ensure_file(self):
        if not SETTINGS_FILE.exists():
            self.save_settings(DEFAULT_SETTINGS)

    def update_calendar_cache(self, title: str, start_time: str):
        """Updates the in-memory calendar state."""
        self._calendar_state = {
            "countdown_title": title,
            "countdown_target": start_time
        }
        logger.info(f"Calendar state updated: {title} at {start_time}")

    def get_settings(self) -> Dict[str, Any]:
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                # Merge with defaults to ensure all keys exist
                settings = {**DEFAULT_SETTINGS, **data}
                
                # If mode is calendar and we have state, override
                if settings.get("countdown_mode") == "calendar" and self._calendar_state:
                    settings["countdown_title"] = self._calendar_state["countdown_title"]
                    settings["countdown_target"] = self._calendar_state["countdown_target"]
                    
                return settings
        except Exception as e:
            logger.error(f"Failed to read settings: {e}")
            return DEFAULT_SETTINGS

    def save_settings(self, new_settings: Dict[str, Any]):
        try:
            # Load current to merge if exists
            current = {}
            if SETTINGS_FILE.exists():
                # Read raw file, ignoring calendar overrides
                with open(SETTINGS_FILE, "r") as f:
                    current = json.load(f)
            
            # Merge defaults -> current -> new
            # We must be careful not to save the "overridden" calendar values into the file permanently
            # if the user didn't intend to change them.
            # actually, if the user configures "calendar" mode, the file will store "countdown_mode": "calendar"
            # and generic title/target. The OVERRIDE happens only on read.
            
            updated = {**DEFAULT_SETTINGS, **current, **new_settings}
            
            with open(SETTINGS_FILE, "w") as f:
                json.dump(updated, f, indent=2)
            logger.info("Settings saved")
            return updated
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            raise e

settings_manager = SettingsManager()
