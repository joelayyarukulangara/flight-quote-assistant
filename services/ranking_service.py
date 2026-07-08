"""
Ranking and selection logic for package flight combinations.

Applies hard-reject rules first (things that make a combination unusable),
then scores the survivors, then picks the best 4 combinations across four
categories: Cheapest, Best direct/lowest-stop, Best timing, Best value.
Duplicates across categories are resolved by picking the next-best option.

Scoring convention: LOWER score is better (it is effectively a "cost" made
of weighted penalties). This keeps every component additive and consistent.
"""
from utils.date_utils import is_late_night

CATEGORY_CHEAPEST = "Cheapest sensible package option"
CATEGORY_LOWEST_STOP = "Best direct / lowest stop package option"
CATEGORY_BEST_TIMING = "Best timing package option"
CATEGORY_BEST_VALUE = "Best value package option"


def hard_reject(combo, filters):
    """Return a rejection reason string, or None if the combination passes."""
    up, down = combo.up_flight, combo.down_flight

    for leg, label in ((up, "UP"), (down, "DOWN")):
        if filters.blocked_airlines and leg.airline in filters.blocked_airlines:
            return f"{label} flight uses blocked airline {leg.airline}"
        if leg.stops > filters.max_stops:
            return f"{label} flight has more stops than allowed"
        if leg.layovers:
            longest = max(l.minutes for l in leg.layovers)
            shortest = min(l.minutes for l in leg.layovers)
            if longest > filters.max_layover_minutes:
                return f"{label} flight layover exceeds max layover"
            if shortest < filters.min_layover_minutes:
                return f"{label} flight layover below minimum layover"
        if leg.airport_change_required and filters.avoid_airport_change:
            return f"{label} flight requires an airport change during layover"

    if filters.max_fare_per_person and combo.total_base_fare_per_person > filters.max_fare_per_person:
        return "Combination exceeds maximum fare per person"

    if down.departure_datetime <= up.departure_datetime:
        return "DOWN date/time is not after UP date/time"

    if combo.package_nights < 0:
        return "Invalid package duration"

    return None


def _timing_penalty(leg, filters):
    penalty = 0
    if filters.avoid_arrival_after_midnight and is_late_night(leg.arrival_datetime):
        penalty += 40
    if is_late_night(leg.departure_datetime):
        penalty += 15
    return penalty


def score_combination(combo, filters):
    up, down = combo.up_flight, combo.down_flight

    price_score = combo.total_base_fare_per_person / 1000.0
    duration_score = (up.duration_minutes + down.duration_minutes) / 30.0
    stops_score = (up.stops + down.stops) * 25
    layover_score = (up.layover_minutes_total + down.layover_minutes_total) / 15.0
    timing_score = _timing_penalty(up, filters) + _timing_penalty(down, filters)

    baggage_score = 0
    if filters.baggage_required == "Checked baggage required":
        for leg in (up, down):
            if "checked" not in leg.baggage_info.lower():
                baggage_score += 20

    airline_score = 0
    if filters.preferred_airlines:
        for leg in (up, down):
            if leg.airline not in filters.preferred_airlines:
                airline_score += 10
    if filters.same_airline_both_ways_preferred and up.airline != down.airline:
        airline_score += 15

    total = (
        price_score
        + duration_score
        + stops_score
        + layover_score
        + timing_score
        + baggage_score
        + airline_score
    )
    return round(total, 2)


def build_warnings(combo):
    warnings = []
    for label, leg in (("UP", combo.up_flight), ("DOWN", combo.down_flight)):
        if is_late_night(leg.departure_datetime) or is_late_night(leg.arrival_datetime):
            warnings.append(f"{label} flight involves a late-night departure/arrival")
        if leg.airport_change_required:
            warnings.append(f"{label} flight requires an airport change during layover")
        if leg.layovers and max(l.minutes for l in leg.layovers) >= 360:
            warnings.append(f"{label} flight has a long layover")
        if "verified" in leg.baggage_info.lower() or "to be verified" in leg.baggage_info.lower():
            warnings.append(f"{label} flight baggage allowance to be verified before ticketing")
        warnings.extend(leg.warnings)
    # de-duplicate, preserve order
    seen = set()
    deduped = []
    for w in warnings:
        if w not in seen:
            seen.add(w)
            deduped.append(w)
    return deduped


def select_best_four(combinations, filters):
    """Filter, score, and select up to 4 categorized best combinations."""
    survivors = []
    for combo in combinations:
        reason = hard_reject(combo, filters)
        if reason:
            continue
        combo.score = score_combination(combo, filters)
        combo.warnings = build_warnings(combo)
        survivors.append(combo)

    if not survivors:
        return []

    chosen = []
    used_ids = set()

    def combo_id(c):
        return (c.up_flight.flight_number, c.up_flight.departure_datetime.isoformat(),
                c.down_flight.flight_number, c.down_flight.departure_datetime.isoformat())

    def pick(sorted_list, category):
        for c in sorted_list:
            cid = combo_id(c)
            if cid not in used_ids:
                used_ids.add(cid)
                c.category = category
                chosen.append(c)
                return
        # nothing left to pick

    by_price = sorted(survivors, key=lambda c: c.total_base_fare_per_person)
    by_stops = sorted(survivors, key=lambda c: (c.up_flight.stops + c.down_flight.stops, c.score))
    by_timing = sorted(
        survivors,
        key=lambda c: (_timing_penalty(c.up_flight, filters) + _timing_penalty(c.down_flight, filters), c.score),
    )
    by_value = sorted(survivors, key=lambda c: c.score)

    pick(by_price, CATEGORY_CHEAPEST)
    pick(by_stops, CATEGORY_LOWEST_STOP)
    pick(by_timing, CATEGORY_BEST_TIMING)
    pick(by_value, CATEGORY_BEST_VALUE)

    return chosen[:4]
