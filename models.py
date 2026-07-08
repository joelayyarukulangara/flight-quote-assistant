"""Data models for Flight Quote Assistant. Plain dataclasses (no external deps)."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import Optional


@dataclass
class PassengerInfo:
    adults: int = 1
    children: int = 0
    infants: int = 0

    @property
    def total(self) -> int:
        return self.adults + self.children + self.infants


@dataclass
class PackageDuration:
    mode: str = "fixed"  # fixed | custom_gap | manual_range
    label: str = "4 Days / 3 Nights"
    days: int = 4
    nights: int = 3
    min_nights: Optional[int] = None
    max_nights: Optional[int] = None
    return_flex_days: int = 1
    auto_calculate_down_dates: bool = True
    return_calc_rule: str = "Return based on UP departure date + nights"
    manual_down_start: Optional[date] = None
    manual_down_end: Optional[date] = None


@dataclass
class SearchFilters:
    max_stops: int = 1
    max_layover_minutes: int = 360
    min_layover_minutes: int = 75
    avoid_airport_change: bool = True
    avoid_arrival_after_midnight: bool = True
    avoid_overnight_layover: bool = False
    prefer_same_day_arrival: bool = False
    baggage_required: str = "Checked baggage required"
    preferred_airlines: list = field(default_factory=list)
    blocked_airlines: list = field(default_factory=list)
    same_airline_both_ways_preferred: bool = False
    max_fare_per_person: Optional[float] = None
    sort_preference: str = "Best value"


@dataclass
class RouteQuery:
    origin: str
    destination: str
    date_from: date
    date_to: date
    preferred_departure_time: str = "Any"
    preferred_arrival_time: str = "Any"
    allow_nearby_origin: bool = False
    allow_nearby_destination: bool = False


@dataclass
class FlightSearchRequest:
    customer_name: str
    package_name: str
    passengers: PassengerInfo
    travel_class: str
    currency: str
    up_route: RouteQuery
    down_route: RouteQuery
    duration: PackageDuration
    filters: SearchFilters
    markup_type: str = "No markup"
    markup_value: float = 0.0
    rounding: Optional[int] = None


@dataclass
class Layover:
    airport: str
    minutes: int
    airport_change: bool = False


@dataclass
class FlightOption:
    provider: str
    airline: str
    airline_code: str
    flight_number: str
    origin: str
    destination: str
    departure_datetime: datetime
    arrival_datetime: datetime
    duration_minutes: int
    stops: int
    layovers: list  # list[Layover]
    layover_minutes_total: int
    airport_change_required: bool
    baggage_info: str
    refund_info: str
    fare: float
    currency: str
    booking_source: str = ""
    warnings: list = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d["departure_datetime"] = self.departure_datetime.isoformat()
        d["arrival_datetime"] = self.arrival_datetime.isoformat()
        return d


@dataclass
class PackageFlightCombination:
    up_flight: FlightOption
    down_flight: FlightOption
    package_days: int
    package_nights: int
    total_base_fare_per_person: float
    markup_amount: float
    final_quote_per_person: float
    total_group_fare: float
    score: float
    category: str
    warnings: list = field(default_factory=list)
    price_checked_at: Optional[datetime] = None
    source: str = "Mock"  # Live API / Cached / Mock data

    def to_dict(self):
        return {
            "up_flight": self.up_flight.to_dict(),
            "down_flight": self.down_flight.to_dict(),
            "package_days": self.package_days,
            "package_nights": self.package_nights,
            "total_base_fare_per_person": self.total_base_fare_per_person,
            "markup_amount": self.markup_amount,
            "final_quote_per_person": self.final_quote_per_person,
            "total_group_fare": self.total_group_fare,
            "score": self.score,
            "category": self.category,
            "warnings": self.warnings,
            "price_checked_at": self.price_checked_at.isoformat() if self.price_checked_at else None,
            "source": self.source,
        }


@dataclass
class QuoteResult:
    request: FlightSearchRequest
    combinations: list  # list[PackageFlightCombination]
    generated_at: datetime
    fare_warning: str = ""
