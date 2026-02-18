from abc import ABC, abstractmethod
from typing import List
from domain.entities.station import FuelStation

class IFuelRepository(ABC):
    @abstractmethod
    def get_stations_within_corridor(self, polyline_str: str, buffer_miles: float) -> List[FuelStation]:
        """Convert polyline to geometry and find stations within buffer."""
        pass
        
    @abstractmethod
    def bulk_insert(self, stations: List[dict]):
        """Bulk insert raw station data."""
        pass
