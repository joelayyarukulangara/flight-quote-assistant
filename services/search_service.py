"""
Search orchestration service.

Flow: read the FlightSearchRequest -> generate valid UP/DOWN date pairs ->
estimate API usage -> search UP flights and DOWN flights per unique date
(using cache where possible) -> combine flights that belong to a valid date
pair -> apply filters/time preferences -> rank -> return best 4 package
combinations wrapped in a QuoteResult.
"""
import json
from datetime import datetime

import database
from config import DEFAULT_SETTINGS
from models import PackageFlightCombination, QuoteResult, FlightOption, Layover
from providers.mock_provider import MockFlightProvider
from providers.serpapi_provider import SerpApiFlightProvider, SerpApiError
from services.date_pair_service import generate_date_pairs, estimate_search_cost
from services.ranking_service import select_best_four
from utils.date_utils import matches_time_preference, now_str
from config import FARE_WARNING_TEXT


class SearchError(Exception):
    pass


def get_active_provider():
    """Return (provider_instance, source_label, warning_or_None)."""
    mock_enabled = database.get_setting("enable_mock_mode", "true") == "true"
    api_key = database.get_setting("serpapi_api_key", "")

    if mock_enabled or not api_key:
        warning = None if mock_enabled else "SerpAPI key missing; using mock data."
        return MockFlightProvider(), "Mock", warning

    try:
        return SerpApiFlightProvider(api_key), "Live API", None
    except SerpApiError as exc:
        return MockFlightProvider(), "Mock", f"{exc} Falling back to mock data."


def _cache_key(provider_name, origin, destination, date_, passengers, travel_class, filters, currency):
    parts = [
        provider_name, origin, destination, date_.isoformat(),
        str(passengers.adults), str(passengers.children), str(passengers.infants),
        travel_class, filters.baggage_required, str(filters.max_stops), currency,
    ]
    return "|".join(parts)


def _flight_from_dict(d):
    layovers = [Layover(**l) for l in d.get("layovers", [])]
    return FlightOption(
        provider=d["provider"], airline=d["airline"], airline_code=d["airline_code"],
        flight_number=d["flight_number"], origin=d["origin"], destination=d["destination"],
        departure_datetime=datetime.fromisoformat(d["departure_datetime"]),
        arrival_datetime=datetime.fromisoformat(d["arrival_datetime"]),
        duration_minutes=d["duration_minutes"], stops=d["stops"], layovers=layovers,
        layover_minutes_total=d["layover_minutes_total"],
        airport_change_required=d["airport_change_required"], baggage_info=d["baggage_info"],
        refund_info=d["refund_info"], fare=d["fare"], currency=d["currency"],
        booking_source=d.get("booking_source", ""), warnings=d.get("warnings", []),
    )


def search_flights_for_date(provider, provider_label, origin, destination, date_, passengers,
                             travel_class, filters, currency="INR", force_refresh=False):
    """Search one leg for one date, using cache unless force_refresh is set.

    Returns (list[FlightOption], source_label, fallback_warning_or_None). The
    warning is set whenever a live provider call fails and this falls back
    to mock data, so callers can surface *why* a leg is showing mock fares
    instead of silently mixing them into a "Live API" result.
    """
    cache_minutes = int(database.get_setting("cache_duration_minutes", DEFAULT_SETTINGS["cache_duration_minutes"]))
    key = _cache_key(provider.name, origin, destination, date_, passengers, travel_class, filters, currency)

    if not force_refresh:
        cached = database.get_cached(key, cache_minutes)
        if cached:
            return [_flight_from_dict(d) for d in cached["payload"]], "Cached", None

    fallback_warning = None
    try:
        options = provider.search_flights(origin, destination, date_, passengers, travel_class, filters, currency)
    except SerpApiError as exc:
        mock = MockFlightProvider()
        options = mock.search_flights(origin, destination, date_, passengers, travel_class, filters, currency)
        provider_label = "Mock"
        fallback_warning = (
            f"Live search failed for {origin}->{destination} on {date_.isoformat()} "
            f"({exc}); showing mock data for this leg instead. Check that '{origin}' and "
            f"'{destination}' are valid airport/city codes."
        )

    database.set_cached(key, [o.to_dict() for o in options], source=provider_label)
    return options, provider_label, fallback_warning


def estimate_request_cost(request):
    duration = request.duration
    pairs = generate_date_pairs(
        up_start_date=request.up_route.date_from,
        up_end_date=request.up_route.date_to,
        duration_days=duration.days,
        duration_nights=duration.nights,
        return_flex_days=duration.return_flex_days,
        manual_down_start=duration.manual_down_start,
        manual_down_end=duration.manual_down_end,
        mode=duration.mode,
    )
    return pairs, estimate_search_cost(pairs)


def _matches_route_preferences(flight, route_query):
    if not matches_time_preference(flight.departure_datetime, route_query.preferred_departure_time):
        return False
    if not matches_time_preference(flight.arrival_datetime, route_query.preferred_arrival_time):
        return False
    return True


def run_search(request, force_refresh=False, progress_callback=None):
    """Execute the full search flow and return a QuoteResult."""
    date_pairs, cost = estimate_request_cost(request)
    if not date_pairs:
        raise SearchError(
            "No valid UP/DOWN date pairs could be generated. Check your date ranges and "
            "package duration (DOWN date must fall after UP date)."
        )

    provider, provider_label, provider_warning = get_active_provider()
    fallback_warnings = []

    up_dates = sorted({p.up_date for p in date_pairs})
    down_dates = sorted({p.down_date for p in date_pairs})

    up_flights_by_date = {}
    for d in up_dates:
        flights, source, fallback_warning = search_flights_for_date(
            provider, provider_label, request.up_route.origin, request.up_route.destination,
            d, request.passengers, request.travel_class, request.filters,
            currency=request.currency, force_refresh=force_refresh,
        )
        if fallback_warning:
            fallback_warnings.append(fallback_warning)
        flights = [f for f in flights if _matches_route_preferences(f, request.up_route)]
        up_flights_by_date[d] = (flights, source)
        if progress_callback:
            progress_callback(f"Searched UP flights for {d.isoformat()}")

    down_flights_by_date = {}
    for d in down_dates:
        flights, source, fallback_warning = search_flights_for_date(
            provider, provider_label, request.down_route.origin, request.down_route.destination,
            d, request.passengers, request.travel_class, request.filters,
            currency=request.currency, force_refresh=force_refresh,
        )
        if fallback_warning:
            fallback_warnings.append(fallback_warning)
        flights = [f for f in flights if _matches_route_preferences(f, request.down_route)]
        down_flights_by_date[d] = (flights, source)
        if progress_callback:
            progress_callback(f"Searched DOWN flights for {d.isoformat()}")

    combinations = []
    checked_at = datetime.now()
    for pair in date_pairs:
        up_flights, up_source = up_flights_by_date.get(pair.up_date, ([], provider_label))
        down_flights, down_source = down_flights_by_date.get(pair.down_date, ([], provider_label))
        for up_f in up_flights:
            for down_f in down_flights:
                base_fare_per_person = up_f.fare + down_f.fare
                markup_amount = _compute_markup(base_fare_per_person, request.markup_type, request.markup_value)
                final_fare = base_fare_per_person + markup_amount
                if request.rounding:
                    final_fare = _round_to(final_fare, request.rounding)
                total_group = final_fare * request.passengers.total
                combo_source = "Mock" if "Mock" in (up_source, down_source) else (
                    "Cached" if "Cached" in (up_source, down_source) else "Live API"
                )
                combinations.append(
                    PackageFlightCombination(
                        up_flight=up_f,
                        down_flight=down_f,
                        package_days=pair.nights + 1,
                        package_nights=pair.nights,
                        total_base_fare_per_person=base_fare_per_person,
                        markup_amount=markup_amount,
                        final_quote_per_person=final_fare,
                        total_group_fare=total_group,
                        score=0.0,
                        category="",
                        price_checked_at=checked_at,
                        source=combo_source,
                    )
                )

    best_four = select_best_four(combinations, request.filters)

    if not best_four:
        raise SearchError(_no_results_message())

    result = QuoteResult(
        request=request,
        combinations=best_four,
        generated_at=checked_at,
        fare_warning=FARE_WARNING_TEXT.format(timestamp=now_str()),
    )
    if provider_warning:
        result.fare_warning = provider_warning + " " + result.fare_warning
    if fallback_warnings:
        unique_warnings = list(dict.fromkeys(fallback_warnings))
        result.fare_warning = " | ".join(unique_warnings) + " " + result.fare_warning
    return result


def _compute_markup(base_fare, markup_type, markup_value):
    if markup_type == "Fixed amount per person":
        return float(markup_value)
    if markup_type == "Percentage":
        return round(base_fare * (float(markup_value) / 100.0), 2)
    return 0.0


def _round_to(value, nearest):
    return round(value / nearest) * nearest


def _no_results_message():
    return (
        "No flight combinations matched your filters. Suggestions:\n"
        "- Increase the maximum layover limit\n"
        "- Allow 1 stop instead of direct only\n"
        "- Widen the date range\n"
        "- Allow nearby airports\n"
        "- Remove blocked airline restrictions\n"
        "- Reduce baggage restrictions\n"
        "- Increase the maximum fare per person"
    )
