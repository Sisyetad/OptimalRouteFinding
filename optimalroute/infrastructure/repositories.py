from typing import List
import polyline
import h3
from haversine import haversine, Unit
from domain.repositories.fuel_repository import IFuelRepository
from domain.entities.station import FuelStation
from infrastructure.models import FuelStationModel

class DjangoFuelRepository(IFuelRepository):
    H3_RESOLUTION = 7  # Edge length ~1.2km. Covers ~0.75 miles buffer efficiently.

    def get_stations_within_corridor(self, polyline_str: str, buffer_miles: float) -> List[FuelStation]:
        """
        Optimized implementation using H3 Geospatial Indexing.
        1. Decodes route
        2. Converts route points to H3 cells (Deduped)
        3. Queries DB for stations in those cells
        4. Fine-grained filtering using exact distances
        """
        # Decode the polyline (lat, lon)
        decoded_coords = polyline.decode(polyline_str)
        if not decoded_coords:
            return []
            
        # 1. Generate set of H3 indices covering the route
        route_h3_indices = set()
        
        # Sampling optimization: If route is dense, we don't need every point.
        # But for robustness, checking every point is safer and fast enough for thousands of points.
        for coord in decoded_coords:
            try:
                lat, lon = coord[:2]  # Only use first two values, ignore elevation if present
                if hasattr(h3, 'latlng_to_cell'):
                    h3_idx = h3.latlng_to_cell(lat, lon, self.H3_RESOLUTION)
                else:
                    h3_idx = h3.geo_to_h3(lat, lon, self.H3_RESOLUTION)
                route_h3_indices.add(h3_idx)
                # Optional: Add neighbors for wider buffer if resolution is too fine
                # For Res 8 (~1.2km edge), a singel cell covers the 0.75-mile buffer well enough 
                # if the route is centered. To be safe for stations near edge:
                # neighboring_cells = h3.k_ring(h3_idx, 1)
                # route_h3_indices.update(neighboring_cells)
            except Exception:
                continue
                
        if not route_h3_indices:
            return []
            
        # 2. Query DB: Fast index lookup
        # SELECT * FROM fuel_stations WHERE h3_index IN (...)
        qs = FuelStationModel.objects.filter(h3_index__in=list(route_h3_indices))
        
        # 3. Fine-grained filtering & Entity Mapping
        stations = []
        
        # Pre-calculation for "Distance from start" (route_mile_marker)
        # To avoid re-calculating this for every station, we map route points to cumulative distance.
        route_with_dist = []
        cum_dist = 0.0
        for i in range(len(decoded_coords)):
            if i > 0:
                step = haversine(decoded_coords[i-1], decoded_coords[i], unit=Unit.MILES)
                cum_dist += step
            route_with_dist.append((decoded_coords[i], cum_dist))

        for model in qs:
            station_coord = (model.latitude, model.longitude)
            
            # Simple minimal distance check against route points
            # (Optimization: could use spatial index on route points too, but iterating route is O(N))
            min_dist = float('inf')
            closest_marker = 0.0
            
            # Optimization: only check route points that are in the SAME or NEIGHBOR h3 cell?
            # For now, linear scan of route is acceptable if route < 5000 points.
            
            for r_point, r_dist in route_with_dist:
                d = haversine(station_coord, r_point, unit=Unit.MILES)
                if d < min_dist:
                    min_dist = d
                    closest_marker = r_dist
                    
                    # Optimization break: if we are extremely close, good enough
                    if min_dist < 0.1: 
                        break

            if min_dist <= buffer_miles:
                entity = FuelStation(
                    id=model.id,
                    truckstop_name=model.truckstop_name,
                    address=model.address,
                    city=model.city,
                    state=model.state,
                    rack_id=model.rack_id,
                    retail_price=float(model.retail_price),
                    latitude=model.latitude,
                    longitude=model.longitude,
                    h3_index=model.h3_index,
                    deviation_distance=float(min_dist),
                    route_mile_marker=float(closest_marker)
                )
                stations.append(entity)
        
        return stations

    def bulk_insert(self, stations: List[dict]):
        # Calculate H3 index for each station before insert
        models_to_create = []
        for s in stations:
            lat, lon = s['latitude'], s['longitude']
            try:
                if hasattr(h3, 'latlng_to_cell'):
                    h3_idx = h3.latlng_to_cell(lat, lon, self.H3_RESOLUTION)
                else:
                    h3_idx = h3.geo_to_h3(lat, lon, self.H3_RESOLUTION)
            except:
                h3_idx = ""
                
            models_to_create.append(
                FuelStationModel(
                    truckstop_name=s['truckstop_name'],
                    address=s['address'],
                    city=s['city'],
                    state=s['state'],
                    rack_id=s['rack_id'],
                    retail_price=s['retail_price'],
                    latitude=lat,
                    longitude=lon,
                    h3_index=h3_idx
                )
            )
        FuelStationModel.objects.bulk_create(models_to_create)

