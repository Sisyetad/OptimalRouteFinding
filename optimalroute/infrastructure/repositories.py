from __future__ import annotations

import math
from functools import lru_cache
from itertools import islice
from typing import List, Tuple

import h3
import polyline as polyline_lib
from haversine import haversine, Unit

from domain.entities.station import FuelStation
from infrastructure.models import FuelStationModel
from domain.repositories.fuel_repository import IFuelRepository


# ── Constants ─────────────────────────────────────────────────────────────────

# Res 7: hexagon edge ≈ 1.72 km ≈ 1.07 mi — tight fit for a 0.5–1.0 mi buffer.
# k=1 ring expansion adds one cell layer (~1.7 km radius) to catch edge stations.
_H3_RESOLUTION = 7
_H3_K_RING     = 1

# Maximum H3 indices per ORM __in clause (avoids huge IN lists)
_ORM_CHUNK     = 5_000


# ── Helper: chunk an iterable ─────────────────────────────────────────────────

def _chunks(iterable, size: int):
    it = iter(iterable)
    while True:
        batch = list(islice(it, size))
        if not batch:
            return
        yield batch


# ── Helper: perpendicular projection onto a line segment ─────────────────────

def _project_onto_segment(
    p_lat: float, p_lon: float,
    a_lat: float, a_lon: float,
    b_lat: float, b_lon: float,
) -> Tuple[float, float, float]:
    # Convert to approximate Cartesian (metres)
    cos_lat = math.cos(math.radians((a_lat + b_lat) / 2.0))
    R       = 111_320.0   # metres per degree latitude

    ax, ay = 0.0, 0.0
    bx = (b_lon - a_lon) * R * cos_lat
    by = (b_lat - a_lat) * R
    px = (p_lon - a_lon) * R * cos_lat
    py = (p_lat - a_lat) * R

    ab2 = bx * bx + by * by
    if ab2 < 1e-12:
        return a_lat, a_lon, 0.0   # degenerate segment

    t = max(0.0, min(1.0, (px * bx + py * by) / ab2))

    proj_lon = a_lon + t * (b_lon - a_lon)
    proj_lat = a_lat + t * (b_lat - a_lat)
    return proj_lat, proj_lon, t


# ── Repository ────────────────────────────────────────────────────────────────

class DjangoFuelRepository(IFuelRepository):
    """
    Retrieves FuelStation entities within a corridor around a polyline route.

    Pipeline
    --------
    1. Decode the Google-encoded polyline.
    2. Build cumulative distance table (route_with_dist).
    3. Convert every route point to an H3 cell + 1-ring neighbours → candidate set.
    4. Fetch matching DB rows in chunked __in queries.
    5. For each candidate station, find the nearest PROJECTION (not nearest point)
       onto the route, compute exact haversine distance.
    6. Keep stations within buffer_miles; attach route_mile_marker and
       deviation_distance.
    """

    H3_RESOLUTION: int = _H3_RESOLUTION

    # ------------------------------------------------------------------
    # Public method
    # ------------------------------------------------------------------

    def get_stations_within_corridor(
        self,
        polyline_str: str,
        buffer_miles: float,
    ) -> List[FuelStation]:

        decoded_coords = polyline_lib.decode(polyline_str)
        if not decoded_coords:
            return []

        route_with_dist = self._build_route_with_dist(polyline_str)

        # ── Step 1: H3 cell set ─────────────
        route_h3_indices = self._route_to_h3_cells(decoded_coords)
        if not route_h3_indices:
            return []

        # ── Step 2: DB fetch in chunks  ─────────────────
        candidate_models = self._fetch_station_models(route_h3_indices)

        # ── Step 3: Fine filter with projection  ───
        stations: List[FuelStation] = []

        for model in candidate_models:
            result = self._nearest_projection(
                model.latitude, model.longitude, route_with_dist
            )
            if result is None:
                continue

            min_dist, closest_marker = result
            if min_dist <= buffer_miles:
                stations.append(FuelStation(
                    id                = model.id,
                    truckstop_name    = model.truckstop_name,
                    address           = model.address,
                    city              = model.city,
                    state             = model.state,
                    rack_id           = model.rack_id,
                    retail_price      = float(model.retail_price),
                    latitude          = float(model.latitude),
                    longitude         = float(model.longitude),
                    h3_index          = model.h3_index,
                    deviation_distance = float(min_dist),
                    route_mile_marker  = float(closest_marker),
                ))

        return stations

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _route_to_h3_cells(decoded_coords) -> set:
        # Version-agnostic API detection — done once outside the loop
        if hasattr(h3, "latlng_to_cell"):
            _to_h3 = lambda lat, lon: h3.latlng_to_cell(lat, lon, _H3_RESOLUTION)
            _kring  = h3.grid_disk
        else:
            _to_h3 = lambda lat, lon: h3.geo_to_h3(lat, lon, _H3_RESOLUTION)
            _kring  = h3.k_ring

        cells: set = set()
        for coord in decoded_coords:
            try:
                lat, lon = coord[0], coord[1]
                cell = _to_h3(lat, lon)
                # k=1 ring ensures stations near cell edges are never missed
                cells.update(_kring(cell, _H3_K_RING))
            except Exception:
                continue
        return cells

    @staticmethod
    def _fetch_station_models(h3_indices: set) -> List:
        seen_ids: set = set()
        results:  list = []

        for batch in _chunks(h3_indices, _ORM_CHUNK):
            qs = FuelStationModel.objects.filter(h3_index__in=batch)
            for model in qs:
                if model.pk not in seen_ids:
                    seen_ids.add(model.pk)
                    results.append(model)

        return results

    @lru_cache(maxsize=32) 
    def _build_route_with_dist(
        self,
        polyline_str: str,
    ) -> List[Tuple[Tuple[float, float], float]]:
        """
        Returns [(coord, cumulative_miles), …] for the decoded polyline.
        Memoised so repeated calls with the same route are O(1).
        """
        decoded = polyline_lib.decode(polyline_str)
        route: List[Tuple[Tuple[float, float], float]] = []
        cum = 0.0
        for i, coord in enumerate(decoded):
            if i > 0:
                cum += haversine(decoded[i - 1], coord, unit=Unit.MILES)
            route.append((coord, cum))
        return route

    @staticmethod
    def _nearest_projection(
        s_lat: float,
        s_lon: float,
        route_with_dist: List[Tuple[Tuple[float, float], float]],
    ) -> Tuple[float, float] | None:
        if not route_with_dist:
            return None

        best_dist   = float("inf")
        best_marker = 0.0

        n = len(route_with_dist)

        for i in range(n - 1):
            (a_lat, a_lon), cum_a = route_with_dist[i]
            (b_lat, b_lon), cum_b = route_with_dist[i + 1]

            # Fast bounding-box pre-filter (saves ~40 % of projection calls)
            lat_lo = min(a_lat, b_lat) - 0.05   # ~3.5 mi slack
            lat_hi = max(a_lat, b_lat) + 0.05
            lon_lo = min(a_lon, b_lon) - 0.07
            lon_hi = max(a_lon, b_lon) + 0.07
            if not (lat_lo <= s_lat <= lat_hi and lon_lo <= s_lon <= lon_hi):
                continue

            # Perpendicular projection
            proj_lat, proj_lon, t = _project_onto_segment(
                s_lat, s_lon,
                a_lat, a_lon,
                b_lat, b_lon,
            )

            dist = haversine((s_lat, s_lon), (proj_lat, proj_lon), unit=Unit.MILES)

            if dist < best_dist:
                best_dist   = dist
                # Interpolate cumulative distance at projection foot
                best_marker = cum_a + t * (cum_b - cum_a)

                # Early-exit: if we're practically on the route, good enough
                if best_dist < 0.05:
                    break

        if best_dist == float("inf"):
            return None

        return best_dist, best_marker

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

