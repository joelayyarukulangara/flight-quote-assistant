"""Abstract flight provider interface.

Any real API integration (SerpAPI, SearchAPI, Amadeus, ...) implements this
interface and returns normalized FlightOption objects, so the rest of the
app never needs to know which provider produced the data.
"""
from abc import ABC, abstractmethod


class FlightProviderError(Exception):
    """Common base for any live provider's failure, so orchestration code
    (services/search_service.py) can handle every provider uniformly
    without importing each provider's specific exception type."""


class FlightProvider(ABC):
    name = "base"

    @abstractmethod
    def search_flights(self, origin, destination, date_, passengers, travel_class, filters, currency="INR"):
        """Return list[FlightOption] for a single origin/destination/date search.

        Args:
            origin: str airport/city code
            destination: str airport/city code
            date_: datetime.date
            passengers: models.PassengerInfo
            travel_class: str
            filters: models.SearchFilters
            currency: str currency code the returned FlightOption.fare values
                must be denominated in (e.g. "INR", "AED", "USD", "EUR").
                Implementations must set FlightOption.currency to match --
                callers display fares using the requested currency label
                without re-converting, so a mismatch here silently produces
                wildly wrong-looking prices.
        """
        raise NotImplementedError
