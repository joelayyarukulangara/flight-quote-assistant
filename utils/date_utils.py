"""Date helper utilities."""
from datetime import date, datetime, timedelta


def daterange(start: date, end: date):
    """Yield each date from start to end inclusive."""
    days = (end - start).days
    for i in range(days + 1):
        yield start + timedelta(days=i)


def parse_date(value):
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def format_date(d: date) -> str:
    return d.strftime("%d %b %Y")


def format_datetime(dt: datetime) -> str:
    return dt.strftime("%d %b %Y, %I:%M %p")


def now_str() -> str:
    return datetime.now().strftime("%d %b %Y, %I:%M %p")


def time_of_day_bucket(dt: datetime) -> str:
    """Classify a datetime's time into Morning/Afternoon/Evening/Night."""
    h = dt.hour
    if 5 <= h < 12:
        return "Morning"
    if 12 <= h < 17:
        return "Afternoon"
    if 17 <= h < 21:
        return "Evening"
    return "Night"


def is_late_night(dt: datetime) -> bool:
    """Late night = 23:00 - 05:00."""
    return dt.hour >= 23 or dt.hour < 5


def matches_time_preference(dt: datetime, preference: str) -> bool:
    if preference == "Any" or not preference:
        return True
    if preference == "Avoid late night":
        return not is_late_night(dt)
    return time_of_day_bucket(dt) == preference
