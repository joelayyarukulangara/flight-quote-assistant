"""
Central configuration and local settings persistence for Flight Quote Assistant.

Settings are stored in a local SQLite table (see database.py) so the app
works fully offline and never requires hardcoded API keys.
"""
import os
import sys

APP_NAME = "Flight Quote Assistant"
APP_VERSION = "1.0.0"

if getattr(sys, "frozen", False):
    # Running as a PyInstaller-built EXE: use the folder the EXE lives in,
    # not sys._MEIPASS (a temp extraction dir that is wiped on exit), so
    # the local database persists between runs.
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "flight_quote_assistant.db")

CURRENCIES = ["INR", "AED", "USD", "EUR"]
TRAVEL_CLASSES = ["Economy", "Premium Economy", "Business", "First"]

TIME_PREFERENCES = ["Any", "Morning", "Afternoon", "Evening", "Night", "Avoid late night"]

DURATION_PRESETS = [
    ("2 Days / 1 Night", 2, 1),
    ("3 Days / 2 Nights", 3, 2),
    ("4 Days / 3 Nights", 4, 3),
    ("5 Days / 4 Nights", 5, 4),
    ("6 Days / 5 Nights", 6, 5),
    ("7 Days / 6 Nights", 7, 6),
    ("8 Days / 7 Nights", 8, 7),
    ("Custom", None, None),
]

RETURN_FLEX_OPTIONS = {
    "Exact date only": 0,
    "±1 day": 1,
    "±2 days": 2,
}

MAX_STOPS_OPTIONS = {
    "Direct only": 0,
    "Max 1 stop": 1,
    "Max 2 stops": 2,
    "Any": 99,
}

MAX_LAYOVER_OPTIONS = {
    "2 hours": 120,
    "4 hours": 240,
    "6 hours": 360,
    "8 hours": 480,
    "12 hours": 720,
    "Custom": None,
}

MIN_LAYOVER_OPTIONS = {
    "45 minutes": 45,
    "1 hour": 60,
    "1 hour 15 minutes": 75,
    "1 hour 30 minutes": 90,
    "2 hours": 120,
}

BAGGAGE_OPTIONS = [
    "Cabin only",
    "15 kg",
    "20 kg",
    "25 kg",
    "30 kg",
    "2 pieces",
    "Checked baggage required",
]

SORT_PREFERENCES = [
    "Best value",
    "Cheapest first",
    "Shortest duration",
    "Direct flights first",
    "Best timing",
]

MARKUP_TYPES = ["No markup", "Fixed amount per person", "Percentage"]

ROUNDING_OPTIONS = {
    "No rounding": None,
    "Round to nearest 50": 50,
    "Round to nearest 100": 100,
    "Round to nearest 500": 500,
}

RETURN_CALC_RULES = [
    "Return based on UP departure date + nights",
    "Return based on UP arrival date + nights",
    "Allow same-day late-night return",
    "Allow next-day early-morning return",
]

AI_MODELS = {
    "nano / cheapest": "gpt-4.1-nano",
    "mini / better": "gpt-4.1-mini",
}

AI_LANGUAGES = ["English", "Malayalam", "Hindi", "Arabic"]

DEFAULT_SETTINGS = {
    "serpapi_api_key": "",
    "openai_api_key": "",
    "default_currency": "INR",
    "default_markup_type": "No markup",
    "default_markup_value": "0",
    "cache_duration_minutes": "60",
    "default_max_stops": "Max 1 stop",
    "default_max_layover": "6 hours",
    "default_min_layover": "1 hour 15 minutes",
    "default_baggage": "Checked baggage required",
    "return_calc_rule": RETURN_CALC_RULES[0],
    "enable_mock_mode": "true",
    "enable_ai_summary": "false",
    "ai_model": "nano / cheapest",
    "ai_language": "English",
    "company_name": "Your Travel Company",
}

API_CALL_WARNING_THRESHOLD = 20

FARE_WARNING_TEXT = (
    "Fare checked on {timestamp}. Fare is subject to availability and may "
    "change until ticketing. Baggage, refund, cancellation, and date-change "
    "rules must be verified before final booking."
)
