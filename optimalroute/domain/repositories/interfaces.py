from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities.station import FuelStation
from domain.entities.route import Route

class IFuelStationRepository(ABC):
    @abstractmethod
    def find_nearby(self, latitude: float, longitude: float, radius_miles: float) -> List[FuelStation]:
        pass

    @abstractmethod
    def find_in_bounding_box(self, min_lat: float, min_lon: float, max_lat: float, max_lon: float) -> List[FuelStation]:
        pass
    
    @abstractmethod
    def bulk_insert(self, stations: List[FuelStation]):
        pass

class IRouteRepository(ABC):
    @abstractmethod
    def get_route(self, start: str, end: str) -> Optional[Route]:
        pass

    @abstractmethod
    def save_route(self, route: Route):
        pass
