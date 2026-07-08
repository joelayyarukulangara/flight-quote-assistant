"""
Generates valid UP/DOWN date pairs for package tour flight searches.

This is the core rule that stops the app from blindly combining every UP
date with every DOWN date. Package tours have a fixed length (e.g. 4 Days /
3 Nights), so DOWN dates are calculated from UP dates + nights, with an
optional +/- flex window. In "manual" mode the user supplies the DOWN date
range directly and we only reject pairs where DOWN < UP.
"""
from dataclasses import dataclass
from datetime import date, timedelta

from utils.date_utils import daterange


@dataclass
class DatePair:
    up_date: date
    down_date: date
    nights: int


def generate_date_pairs(
    up_start_date: date,
    up_end_date: date,
    duration_days: int,
    duration_nights: int,
    return_flex_days: int = 0,
    manual_down_start: date = None,
    manual_down_end: date = None,
    mode: str = "fixed",
):
    """Return a list of DatePair objects representing valid UP/DOWN combos.

    mode="fixed" or "custom_gap": DOWN date = UP date + duration_nights,
        expanded by +/- return_flex_days (clipped so DOWN never precedes UP).
    mode="manual": DOWN dates come from the user-entered manual range; only
        pairs where DOWN date > UP date are kept (same-day return also
        excluded to keep pairs valid, per "package" semantics).
    """
    pairs = []

    if up_start_date > up_end_date:
        raise ValueError("UP date range is invalid: start date is after end date.")

    up_dates = list(daterange(up_start_date, up_end_date))

    if mode == "manual":
        if not manual_down_start or not manual_down_end:
            raise ValueError("Manual return date range requires both start and end dates.")
        if manual_down_start > manual_down_end:
            raise ValueError("DOWN date range is invalid: start date is after end date.")
        down_dates = list(daterange(manual_down_start, manual_down_end))
        for up_d in up_dates:
            for down_d in down_dates:
                if down_d <= up_d:
                    continue  # reject impossible pairs where DOWN is before/same as UP
                nights = (down_d - up_d).days
                pairs.append(DatePair(up_date=up_d, down_date=down_d, nights=nights))
        return pairs

    # fixed / custom_gap mode
    if duration_nights is None or duration_nights < 0:
        raise ValueError("Invalid package duration: nights must be zero or more.")

    for up_d in up_dates:
        base_down = up_d + timedelta(days=duration_nights)
        for flex in range(-return_flex_days, return_flex_days + 1):
            down_d = base_down + timedelta(days=flex)
            if down_d <= up_d:
                continue  # reject impossible pair
            nights = (down_d - up_d).days
            pairs.append(DatePair(up_date=up_d, down_date=down_d, nights=nights))

    return pairs


def estimate_search_cost(date_pairs):
    """Estimate API calls: one call per unique UP date + one per unique DOWN date."""
    up_dates = {p.up_date for p in date_pairs}
    down_dates = {p.down_date for p in date_pairs}
    return {
        "up_dates": len(up_dates),
        "down_dates": len(down_dates),
        "date_pairs": len(date_pairs),
        "estimated_api_calls": len(up_dates) + len(down_dates),
    }
