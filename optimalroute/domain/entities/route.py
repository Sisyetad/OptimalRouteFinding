from dataclasses import dataclass
from typing import List

@dataclass
class Route:
    start_location: str
    end_location: str
    total_distance_miles: float
    total_duration_minutes: float
    polyline: str
    bounds: List[float] = None
