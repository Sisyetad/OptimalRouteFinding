import requests
import json
from typing import Optional
from django.core.cache import cache
from domain.entities.route import Route
from domain.repositories.routing_service import IRoutingService

class OpenRouteServiceClient(IRoutingService):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openrouteservice.org"
        self.CACHE_TIMEOUT = 86400  # 24 hours

    def get_route(self, start_pos: str, end_pos: str) -> Optional[Route]:
        # Check cache for route
        cache_key = f"route_{start_pos}_{end_pos}".replace(" ", "_").lower()
        cached_route = cache.get(cache_key)
        
        if cached_route:
            # Reconstruct Route object from cached dictionary
            return Route(
                start_location=cached_route['start_location'],
                end_location=cached_route['end_location'],
                total_distance_miles=cached_route['total_distance_miles'],
                total_duration_minutes=cached_route['total_duration_minutes'],
                polyline=cached_route['polyline']
            )

        # Geocode first
        start_coords = self._geocode(start_pos)
        end_coords = self._geocode(end_pos)
        
        if not start_coords or not end_coords:
            raise ValueError("Could not geocode locations")
            
        # Get directions
        directions_url = f"{self.base_url}/v2/directions/driving-car"
        
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        
        body = {
            "coordinates": [[start_coords[1], start_coords[0]], [end_coords[1], end_coords[0]]],
            "format": "json"
        }
        
        try:
            response = requests.post(directions_url, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            routes = data.get("routes", [])
            if not routes:
                return None
                
            route_data = routes[0]
            summary = route_data.get("summary", {})
            distance = summary.get("distance", 0) / 1609.34  # meters to miles
            duration = summary.get("duration", 0) / 60  # seconds to minutes
            
            geometry = route_data.get("geometry")
            # ORS returns encoded polyline
            
            route_obj = Route(
                start_location=start_pos,
                end_location=end_pos,
                total_distance_miles=round(distance, 2),
                total_duration_minutes=round(duration, 2),
                polyline=geometry
            )
            
            # Cache the result
            cache_data = {
                'start_location': start_pos,
                'end_location': end_pos,
                'total_distance_miles': route_obj.total_distance_miles,
                'total_duration_minutes': route_obj.total_duration_minutes,
                'polyline': route_obj.polyline
            }
            cache.set(cache_key, cache_data, timeout=self.CACHE_TIMEOUT)
            
            return route_obj
            
        except Exception as e:
            print(f"Error fetching route: {e}")
            raise

    def _geocode(self, location: str) -> Optional[tuple]:
        # Check cache
        cache_key = f"geo_{location}".replace(" ", "_").lower()
        cached_coords = cache.get(cache_key)
        if cached_coords:
            return cached_coords

        # Check if already coords (must be two numeric parts)
        if "," in location:
            parts = location.split(",")
            if len(parts) == 2:
                try:
                    lat = float(parts[0].strip())
                    lon = float(parts[1].strip())
                    coords = (lat, lon)
                    cache.set(cache_key, coords, timeout=self.CACHE_TIMEOUT)
                    return coords
                except ValueError:
                    pass  # Not numeric, fall through to geocoding

        # Use ORS Geocoding for all other cases
        geocode_url = f"{self.base_url}/geocode/search"
        params = {
            "api_key": self.api_key,
            "text": location,
            "size": 1
        }
        try:
            resp = requests.get(geocode_url, params=params)
            resp.raise_for_status()
            data = resp.json()
            if data.get('features'):
                coords = data['features'][0]['geometry']['coordinates']
                result = (coords[1], coords[0])  # lat, lon
                cache.set(cache_key, result, timeout=self.CACHE_TIMEOUT)
                return result
            return None
        except Exception as e:
            print(f"Geocoding error: {e}")
            return None
