"""
Mock flight data provider.

Generates realistic, varied, deterministic-ish sample flight options so the
whole app can be built, demoed, and tested without internet access or any
API key. Always includes a spread of option types: direct, 1-stop, cheap
with a long layover, a premium airline, a late-night flight, and one flight
on an airline commonly used to test the "blocked airline" filter.
"""
import random
from datetime import datetime, timedelta

from models import FlightOption, Layover
from providers.base import FlightProvider

AIRLINES = [
    ("Air India Express", "IX"),
    ("Emirates", "EK"),
    ("Air Arabia", "G9"),
    ("IndiGo", "6E"),
    ("Etihad Airways", "EY"),
    ("Qatar Airways", "QR"),
    ("SpiceJet", "SG"),  # used as an example "blocked airline" test candidate
    ("Salam Air", "OV"),
]

PREMIUM_AIRLINES = {"Emirates", "Qatar Airways", "Etihad Airways"}

BAGGAGE_BY_AIRLINE = {
    "Emirates": "30 kg checked baggage included",
    "Qatar Airways": "30 kg checked baggage included",
    "Etihad Airways": "25 kg checked baggage included",
    "Air India Express": "20 kg checked baggage included",
    "Air Arabia": "20 kg checked baggage (paid)",
    "IndiGo": "15 kg checked baggage included",
    "SpiceJet": "15 kg checked baggage included",
    "Salam Air": "Cabin baggage only, checked bag extra",
}

LAYOVER_AIRPORTS = ["DOH", "BOM", "DEL", "AUH", "BAH", "MCT"]

# Rough, static conversion rates from INR (the base currency all mock fares
# are generated in). Good enough to keep mock-mode numbers in a sane
# ballpark for any selected currency -- not for real conversions.
INR_CONVERSION_RATES = {
    "INR": 1.0,
    "AED": 1 / 23.0,
    "USD": 1 / 83.0,
    "EUR": 1 / 90.0,
}


def _base_fare(origin, destination, travel_class):
    seed = sum(ord(c) for c in (origin + destination))
    base = 8000 + (seed % 12) * 950
    multiplier = {"Economy": 1.0, "Premium Economy": 1.6, "Business": 3.2, "First": 5.0}
    return round(base * multiplier.get(travel_class, 1.0), -1)


class MockFlightProvider(FlightProvider):
    name = "Mock"

    def search_flights(self, origin, destination, date_, passengers, travel_class, filters, currency="INR"):
        rng = random.Random(f"{origin}-{destination}-{date_.isoformat()}-{travel_class}")
        base_fare = _base_fare(origin, destination, travel_class)
        rate = INR_CONVERSION_RATES.get(currency, 1.0)
        options = []

        templates = [
            # (airline_idx, stops, dep_hour, extra_fare, layover_minutes, tag)
            (0, 0, 9, 0, 0, "direct"),
            (3, 1, 14, -1200, 95, "one_stop_short"),
            (1, 0, 22, 4500, 0, "premium_direct"),
            (2, 1, 6, -2500, 430, "cheap_long_layover"),
            (4, 0, 23, 1800, 0, "late_night"),
            (6, 1, 12, -3000, 210, "blocked_example"),
        ]

        for airline_idx, stops, dep_hour, extra_fare, layover_minutes, tag in templates:
            airline, code = AIRLINES[airline_idx]
            jitter = rng.randint(-400, 400)
            fare = max(3000, base_fare + extra_fare + jitter) * rate
            dep_minute = rng.choice([0, 10, 20, 30, 45])
            departure = datetime.combine(date_, datetime.min.time()) + timedelta(
                hours=dep_hour, minutes=dep_minute
            )
            flight_minutes = 120 + rng.randint(-20, 90) + (layover_minutes if stops else 0)
            duration_minutes = max(60, flight_minutes)
            arrival = departure + timedelta(minutes=duration_minutes)

            layovers = []
            airport_change_required = False
            if stops:
                lay_airport = rng.choice(LAYOVER_AIRPORTS)
                airport_change_required = tag == "cheap_long_layover" and rng.random() < 0.4
                layovers.append(
                    Layover(airport=lay_airport, minutes=layover_minutes, airport_change=airport_change_required)
                )

            warnings = []
            if tag == "late_night" or departure.hour >= 23 or departure.hour < 5:
                warnings.append("Late-night departure/arrival")
            if airport_change_required:
                warnings.append("Airport change required during layover")
            if tag == "cheap_long_layover":
                warnings.append("Long layover duration")

            flight_number = f"{code}{rng.randint(100, 999)}"

            options.append(
                FlightOption(
                    provider=self.name,
                    airline=airline,
                    airline_code=code,
                    flight_number=flight_number,
                    origin=origin,
                    destination=destination,
                    departure_datetime=departure,
                    arrival_datetime=arrival,
                    duration_minutes=duration_minutes,
                    stops=stops,
                    layovers=layovers,
                    layover_minutes_total=sum(l.minutes for l in layovers),
                    airport_change_required=airport_change_required,
                    baggage_info=BAGGAGE_BY_AIRLINE.get(airline, "Baggage info to be verified before ticketing"),
                    refund_info="Non-refundable; date change fee applies (to be verified before ticketing)",
                    fare=round(float(fare), 2),
                    currency=currency,
                    booking_source="Mock Data",
                    warnings=warnings,
                )
            )

        return options
