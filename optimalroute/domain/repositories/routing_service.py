from abc import ABC, abstractmethod
from typing import Optional
from domain.entities.route import Route

class IRoutingService(ABC):
    @abstractmethod
    def get_route(self, start_pos: str, end_pos: str) -> Optional[Route]:
        """Fetch route details including polyline and distance."""
        pass
