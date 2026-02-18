from dataclasses import dataclass

@dataclass
class FuelStation:
    id: int
    truckstop_name: str
    address: str
    city: str
    state: str
    rack_id: int
    retail_price: float
    latitude: float
    longitude: float
    h3_index: str
    deviation_distance: float = 0.0
    route_mile_marker: float = 0.0

@dataclass
class FuelStopDecision:
    station: FuelStation
    mile_marker: float
    gallons_filled: float
    cost: float
    score: float
    price_per_gallon: float
