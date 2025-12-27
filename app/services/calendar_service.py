import httpx
import logging
from datetime import datetime, timezone
import icalendar
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

async def fetch_next_event(ical_url: str, filter_keyword: str = None) -> Tuple[Optional[str], Optional[datetime]]:
    """
    Fetches an iCal feed and returns the Title and Start Time of the next future event.
    Optionally filters events by a keyword in the summary.
    
    Returns:
        (title, start_time_utc) or (None, None)
    """
    if not ical_url:
        return None, None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(ical_url)
            response.raise_for_status()
            
            cal_data = response.text
            cal = icalendar.Calendar.from_ical(cal_data)
            
            now = datetime.now(timezone.utc)
            next_event = None
            min_diff = None

            for component in cal.walk():
                if component.name == "VEVENT":
                    summary = str(component.get('summary', ''))
                    
                    # Filter logic
                    if filter_keyword and filter_keyword.lower() not in summary.lower():
                        continue
                        
                    dtstart = component.get('dtstart')
                    if not dtstart:
                        continue
                        
                    start = dtstart.dt
                    
                    # Normalize to UTC
                    if hasattr(start, 'tzinfo') and start.tzinfo is not None:
                        start = start.astimezone(timezone.utc)
                    else:
                        # If naive, assume UTC or ignore? Naive usually implies floating time. 
                        # Let's assume UTC for simplicity or server local time.
                        # Ideally assume server timezone.
                        start = start.replace(tzinfo=timezone.utc)

                    # Check if in future
                    if start > now:
                        diff = (start - now).total_seconds()
                        if min_diff is None or diff < min_diff:
                            min_diff = diff
                            next_event = (summary, start)

            if next_event:
                logger.info(f"Found next calendar event: {next_event[0]} at {next_event[1]}")
                return next_event
            else:
                logger.info("No future events found in calendar matching criteria.")
                return None, None

    except Exception as e:
        logger.error(f"Error fetching calendar: {e}")
        return None, None
