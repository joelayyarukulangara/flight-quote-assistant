"""
SerpAPI Google Flights provider.

Normalizes SerpAPI's Google Flights engine response into internal
FlightOption objects. Never hardcodes an API key -- it is read from local
settings (see database.py / Settings tab). If the key is missing or the
request fails, callers should fall back to the mock provider (see
services/search_service.py).
"""
import re
from datetime import datetime

import requests

from models import FlightOption, Layover
from providers.base import FlightProvider

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


class SerpApiError(Exception):
    pass


def _redact_api_key(text: str, api_key: str) -> str:
    """Strip an API key from error text before it can reach a UI/log.

    requests' own exception messages (e.g. from raise_for_status()) include
    the full request URL, query string and all -- so the key must be
    scrubbed defensively rather than trusted not to appear.
    """
    if not text or not api_key:
        return text
    redacted = text.replace(api_key, "[REDACTED]")
    # Also catch the URL-encoded form, since it appears in request URLs.
    redacted = re.sub(r"(?i)(api_key=)[^&\s]+", r"\1[REDACTED]", redacted)
    return redacted


class SerpApiFlightProvider(FlightProvider):
    name = "Live API"

    def __init__(self, api_key: str):
        if not api_key:
            raise SerpApiError("SerpAPI API key is missing.")
        if re.search(r"\s", api_key) or len(api_key) > 128:
            # A real SerpAPI key is a short token with no whitespace. This
            # usually means something else (a pasted message, a URL, etc.)
            # ended up in the API key field by mistake -- fail fast with a
            # clear message instead of sending it to SerpAPI and leaking it
            # into a network request / error log.
            raise SerpApiError(
                "The configured SerpAPI key doesn't look like a valid key "
                "(it contains spaces or is unusually long). Check Settings "
                "-- it looks like something other than an API key may have "
                "been pasted into that field."
            )
        self.api_key = api_key

    def search_flights(self, origin, destination, date_, passengers, travel_class, filters, currency="INR"):
        params = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": date_.isoformat(),
            "type": "2",  # one-way
            "adults": passengers.adults,
            "children": passengers.children,
            "infants_in_seat": 0,
            "infants_on_lap": passengers.infants,
            "travel_class": self._map_travel_class(travel_class),
            "currency": currency,
            "api_key": self.api_key,
        }
        try:
            response = requests.get(SERPAPI_ENDPOINT, params=params, timeout=25)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            raise SerpApiError(f"SerpAPI request failed: {_redact_api_key(str(exc), self.api_key)}") from exc
        except ValueError as exc:
            raise SerpApiError(f"SerpAPI returned invalid JSON: {exc}") from exc

        if "error" in data:
            raise SerpApiError(f"SerpAPI error: {_redact_api_key(str(data['error']), self.api_key)}")

        results = []
        for bucket_key in ("best_flights", "other_flights"):
            for item in data.get(bucket_key, []) or []:
                option = self._normalize(item, origin, destination, currency)
                if option:
                    results.append(option)
        return results

    @staticmethod
    def _map_travel_class(travel_class: str) -> str:
        mapping = {"Economy": "1", "Premium Economy": "2", "Business": "3", "First": "4"}
        return mapping.get(travel_class, "1")

    def _normalize(self, item, origin, destination, currency="INR"):
        try:
            legs = item.get("flights", [])
            if not legs:
                return None

            price = item.get("price")
            if not price or float(price) <= 0:
                # A missing/zero price means this result can't actually be
                # booked at a known fare -- treating it as fare=0 would let
                # it masquerade as the "cheapest" option and corrupt ranking.
                return None
            first_leg = legs[0]
            last_leg = legs[-1]

            departure = self._parse_dt(first_leg["departure_airport"]["time"])
            arrival = self._parse_dt(last_leg["arrival_airport"]["time"])

            layovers = []
            for lay in item.get("layovers", []) or []:
                layovers.append(
                    Layover(
                        airport=lay.get("id", "?"),
                        minutes=lay.get("duration", 0),
                        airport_change=bool(lay.get("overnight", False)),
                    )
                )

            stops = max(0, len(legs) - 1)
            duration_minutes = item.get("total_duration") or int((arrival - departure).total_seconds() // 60)

            airline = first_leg.get("airline", "Unknown Airline")
            airline_code = first_leg.get("airline_logo", "")[:2].upper() if not first_leg.get("flight_number") else first_leg["flight_number"][:2]
            flight_number = first_leg.get("flight_number", "")

            fare = float(price)

            return FlightOption(
                provider=self.name,
                airline=airline,
                airline_code=airline_code,
                flight_number=flight_number,
                origin=origin,
                destination=destination,
                departure_datetime=departure,
                arrival_datetime=arrival,
                duration_minutes=duration_minutes,
                stops=stops,
                layovers=layovers,
                layover_minutes_total=sum(l.minutes for l in layovers),
                airport_change_required=any(l.airport_change for l in layovers),
                baggage_info=item.get("baggage", "To be verified before ticketing"),
                refund_info="To be verified before ticketing",
                fare=fare,
                currency=currency,
                booking_source="SerpAPI / Google Flights",
                warnings=[],
            )
        except (KeyError, IndexError, TypeError, ValueError):
            return None

    @staticmethod
    def _parse_dt(value: str) -> datetime:
        return datetime.strptime(value, "%Y-%m-%d %H:%M")
