"""Abstract flight provider interface.

Any real API integration (SerpAPI, SearchAPI, Amadeus, ...) implements this
interface and returns normalized FlightOption objects, so the rest of the
app never needs to know which provider produced the data.
"""
from abc import ABC, abstractmethod


class FlightProvider(ABC):
    name = "base"

    @abstractmethod
    def search_flights(self, origin, destination, date_, passengers, travel_class, filters):
        """Return list[FlightOption] for a single origin/destination/date search.

        Args:
            origin: str airport/city code
            destination: str airport/city code
            date_: datetime.date
            passengers: models.PassengerInfo
            travel_class: str
            filters: models.SearchFilters
        """
        raise NotImplementedError
