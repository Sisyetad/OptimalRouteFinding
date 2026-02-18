from typing import Dict, Any
from domain.repositories.fuel_repository import IFuelRepository
from domain.repositories.routing_service import IRoutingService
from domain.services.optimization_engine import FuelOptimizationEngine
from domain.entities.route import Route

class PlanTripUseCase:
    def __init__(
        self,
        routing_service: IRoutingService,
        fuel_repo: IFuelRepository,
        optimizer: FuelOptimizationEngine
    ):
        self.routing_service = routing_service
        self.fuel_repo = fuel_repo
        self.optimizer = optimizer

    def execute(self, start_location: str, end_location: str) -> Dict[str, Any]:
        route = self.routing_service.get_route(start_location, end_location)
        if not route:
            raise ValueError("Could not find route from reliable source.")

        stations = self.fuel_repo.get_stations_within_corridor(
            route.polyline, buffer_miles=10.0
        )
        
        # 3. Optimize Fuel Stops with new Dijkstra-based engine
        stops, total_cost, tracker, total_gallons = self.optimizer.plan_trip(
            route.total_distance_miles, stations
        )
        
        # 4. Format Response
        return {
            "route": {
                "distance_miles": route.total_distance_miles,
                "duration_minutes": route.total_duration_minutes,
                "polyline": route.polyline
            },
            "fuel_summary": {
                "total_cost": total_cost,
                "total_gallons": total_gallons,
                "total_stops": len(stops)
            },
            "stops": [
                {
                    "truckstop_name": s.station.truckstop_name,
                    "city": s.station.city,
                    "state": s.station.state,
                    "price_per_gallon": s.station.retail_price,
                    "gallons_filled": round(s.gallons_filled, 2),
                    "cost": round(s.cost, 2),
                    "mile_marker": round(s.mile_marker, 2),
                    "score": s.score
                }
                for s in stops
            ],
            "per_mile_progression": tracker
        }
