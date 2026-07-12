"""
SearchAPI.io Google Flights provider.

Second live flight-data source, selectable in Settings alongside SerpAPI.
SearchAPI's google_flights engine returns a response shape very close to
SerpAPI's, but the two are separate services with separate API keys and
slightly different field conventions, so each gets its own adapter.
Normalizes results into internal FlightOption objects.
"""
import re
from datetime import datetime

import requests

from models import FlightOption, Layover
from providers.base import FlightProvider, FlightProviderError

SEARCHAPI_ENDPOINT = "https://www.searchapi.io/api/v1/search"


class SearchApiError(FlightProviderError):
    pass


def _redact_api_key(text: str, api_key: str) -> str:
    """Strip the API key from error text before it can reach a UI/log."""
    if not text or not api_key:
        return text
    redacted = text.replace(api_key, "[REDACTED]")
    redacted = re.sub(r"(?i)(api_key=)[^&\s]+", r"\1[REDACTED]", redacted)
    return redacted


class SearchApiFlightProvider(FlightProvider):
    name = "SearchAPI"

    def __init__(self, api_key: str):
        if not api_key:
            raise SearchApiError("SearchAPI API key is missing.")
        if re.search(r"\s", api_key) or len(api_key) > 128:
            raise SearchApiError(
                "The configured SearchAPI key doesn't look like a valid key "
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
            "flight_type": "one_way",
            "adults": passengers.adults,
            "children": passengers.children,
            "infants_on_lap": passengers.infants,
            "travel_class": self._map_travel_class(travel_class),
            "currency": currency,
            "api_key": self.api_key,
        }
        try:
            response = requests.get(SEARCHAPI_ENDPOINT, params=params, timeout=25)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            raise SearchApiError(f"SearchAPI request failed: {_redact_api_key(str(exc), self.api_key)}") from exc
        except ValueError as exc:
            raise SearchApiError(f"SearchAPI returned invalid JSON: {exc}") from exc

        if "error" in data:
            raise SearchApiError(f"SearchAPI error: {_redact_api_key(str(data['error']), self.api_key)}")

        results = []
        for bucket_key in ("best_flights", "other_flights"):
            for item in data.get(bucket_key, []) or []:
                option = self._normalize(item, origin, destination, currency)
                if option:
                    results.append(option)
        return results

    @staticmethod
    def _map_travel_class(travel_class: str) -> str:
        mapping = {
            "Economy": "economy",
            "Premium Economy": "premium_economy",
            "Business": "business",
            "First": "first",
        }
        return mapping.get(travel_class, "economy")

    def _normalize(self, item, origin, destination, currency="INR"):
        try:
            legs = item.get("flights", [])
            if not legs:
                return None

            price = item.get("price")
            if not price or float(price) <= 0:
                # Missing/zero price means this result can't actually be
                # booked at a known fare -- rejecting it keeps a phantom
                # "free" flight from corrupting the cheapest ranking.
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
                        minutes=int(lay.get("duration", 0)),
                        airport_change=bool(lay.get("overnight", False)),
                    )
                )

            stops = max(0, len(legs) - 1)
            duration_minutes = item.get("total_duration") or int((arrival - departure).total_seconds() // 60)

            airline = first_leg.get("airline", "Unknown Airline")
            flight_number = first_leg.get("flight_number", "")
            airline_code = flight_number[:2] if flight_number else ""

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
                fare=float(price),
                currency=currency,
                booking_source="SearchAPI / Google Flights",
                warnings=[],
            )
        except (KeyError, IndexError, TypeError, ValueError):
            return None

    @staticmethod
    def _parse_dt(value: str) -> datetime:
        return datetime.strptime(value, "%Y-%m-%d %H:%M")
