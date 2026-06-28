import requests
from typing import Optional
from domain.entities.route import Route
from domain.repositories.routing_service import IRoutingService
from domain.error.exceptions import (
    RouteError,
    RouteTooLongError,
    LocationNotRoutableError,
    GeocodingError,
)
from config.utils.redis_cache_helper import RedisCacheHelper

cache_helper = RedisCacheHelper()
    
class OpenRouteServiceClient(IRoutingService):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openrouteservice.org"
        self.CACHE_TIMEOUT = 86400  # 24 hours

    def get_route(self, start_pos: str, end_pos: str) -> Optional[Route]:
        # Check cache for route
        cache_key = f"{start_pos}_{end_pos}".replace(" ", "_").lower()
        cached_route = cache_helper.get("route", cache_key)

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
        
        if not start_coords:
            raise GeocodingError(
                f"Could not geocode start location: '{start_pos}'. "
                "Please use a valid city name (e.g., 'Dallas, Texas') "
                "or coordinates (e.g., '32.7767, -96.7970')"
            )
        if not end_coords:
            raise GeocodingError(
                f"Could not geocode end location: '{end_pos}'. "
                "Please use a valid city name (e.g., 'Houston, Texas') "
                "or coordinates (e.g., '29.7604, -95.3698')"
            )
            
        # Get directions
        directions_url = f"{self.base_url}/v2/directions/driving-car"
        
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        
        body = {
            "coordinates": [[start_coords[1], start_coords[0]], [end_coords[1], end_coords[0]]],
            "preference": "recommended",
            "options": {
                "avoid_features": ["highways"]
            }
        }

        try:
            response = requests.post(directions_url, json=body, headers=headers, timeout=30)
            data = response.json()
            
            # Check for API errors
            if response.status_code != 200:
                error_info = data.get('error', {})
                error_code = error_info.get('code')
                error_msg = error_info.get('message', 'Unknown error')
                
                # Handle specific error codes
                if error_code == 2004:
                    raise RouteTooLongError(
                        f"Route distance exceeds maximum limit of 6,000 km (~3,730 miles). "
                        f"Please use locations closer together."
                    )
                elif error_code == 2010:
                    raise LocationNotRoutableError(
                        f"One or both locations are not on a routable road. "
                        f"Please use coordinates or addresses that are in cities or on highways. "
                        f"Original error: {error_msg}"
                    )
                else:
                    raise RouteError(
                        f"OpenRouteService API Error (Code {error_code}): {error_msg}"
                    )
            
            routes = data.get("routes", [])
            if not routes:
                raise RouteError("No route found between the specified locations.")
                
            route_data = routes[0]
            summary = route_data.get("summary", {})
            distance = summary.get("distance", 0) / 1609.34  # meters to miles
            duration = summary.get("duration", 0) / 60  # seconds to minutes
            
            geometry = route_data.get("geometry")
            if not geometry:
                raise RouteError("Route found but no geometry data returned.")
            
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
            cache_helper.set("route", cache_key, cache_data, ttl=self.CACHE_TIMEOUT)
            
            return route_obj
            
        except (RouteError, GeocodingError) as e:
            raise
        except requests.exceptions.Timeout:
            raise RouteError(
                "Request timeout: OpenRouteService API took too long to respond. "
                "Please try again in a few moments."
            )
        except requests.exceptions.ConnectionError:
            raise RouteError(
                "Connection error: Unable to reach OpenRouteService API. "
                "Please check your internet connection."
            )
        except Exception as e:
            raise RouteError(f"Unexpected error while fetching route: {str(e)}")

    def _geocode(self, location: str) -> Optional[tuple]:
        # Check cache
        cache_key = f"{location}".replace(" ", "_").lower()
        cached_coords = cache_helper.get("geocode", cache_key)
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
                    cache_helper.set("geocode", cache_key, coords, ttl=self.CACHE_TIMEOUT)
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
                cache_helper.set("geocode", cache_key, result, ttl=self.CACHE_TIMEOUT)
                return result
            return None
        except Exception as e:
            print(f"Geocoding error: {e}")
            return None
