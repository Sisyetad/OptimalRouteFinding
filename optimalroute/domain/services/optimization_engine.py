import heapq
from typing import List, Tuple, Dict, Optional

from domain.entities.station import FuelStation, FuelStopDecision


class FuelOptimizationEngine:
    """
    Plans least-cost fuel stops for a long-haul truck using Dijkstra over a
    DAG of fuel stations ordered by route mile marker.

    State:  node index in all_nodes (Start=0, stations 1..K, End=K+1)
    Weight: fuel cost to drive from node u to node v at u's retail price

    Geometry model
    --------------
    Each FuelStation carries:
      route_mile_marker  – cumulative distance along the route to the nearest
                           route point (computed by the repository layer).
      deviation_distance – one-way off-route detour to reach the station.

    When the truck travels u → v:
      • It departs from u (already on-site, deviation already paid).
      • Drives back to the route  (u.deviation_distance).
      • Drives the on-route segment (v.route_mile_marker - u.route_mile_marker).
      • Diverts to v  (v.deviation_distance).

    Total driven: route_diff + u.deviation + v.deviation

    Exception: Start node (id=-1) has deviation=0 so the formula is symmetric
    for the very first edge; the truck starts ON the route.
    """

    def __init__(self, vehicle_range: float = 500.0, mpg: float = 10.0):
        self.vehicle_range = vehicle_range
        self.mpg = mpg
        # Weights for the human-readable station score (0–10)
        self.price_weight = 0.6       # fraction of score driven by price
        self.deviation_weight = 0.4   # fraction driven by how far off-route

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan_trip(
        self,
        route_distance: float,
        stations: List[FuelStation],
    ) -> Tuple[
        List[FuelStopDecision],   # ordered fuel stops
        float,                    # total fuel cost (£/$ at input currency)
        List[Dict],               # per-mile cost progression tracker
        float,                    # total gallons consumed
        List[Dict],               # step-by-step refuel path
    ]:
        """
        Plans fuel stops to minimise total fuel cost.

        Returns
        -------
        stops         : FuelStopDecision for every node where fuel is bought
                        (includes the start node).
        total_cost    : Dijkstra optimal cost (float, rounded to 2dp).
        tracker       : [{"mile": int, "total_spent": float}, …] one entry per
                        integer mile along the route.
        total_gallons : total fuel consumed (float, rounded to 2dp).
        refuel_path   : human-readable node sequence with refuel flags.
        """
        if not stations:
            return [], -1.0, [], 0.0, []

        sorted_stations = sorted(stations, key=lambda s: s.route_mile_marker)

        # ── Start node price ──────────────────────────────────────────
        # Use the cheapest station within 15 route-miles of the start so the
        # driver can price-shop before departing.  Fall back to fleet average.
        start_price = self._start_price(sorted_stations)

        # ── Build node list ───────────────────────────────────────────
        start_node = self._make_virtual_node(-1,  "Start", 0.0,            start_price)
        end_node   = self._make_virtual_node(-2,  "End",   route_distance, 0.0)
        all_nodes  = [start_node] + sorted_stations + [end_node]
        end_idx    = len(all_nodes) - 1

        # ── Dijkstra ──────────────────────────────────────────────────
        #   min_costs[i] = (best_cost_to_reach_i, parent_index | None)
        INF = float("inf")
        min_costs: Dict[int, Tuple[float, Optional[int]]] = {0: (0.0, None)}
        pq = [(0.0, 0)]   # (cost, node_index)

        while pq:
            current_cost, u_idx = heapq.heappop(pq)

            # Skip stale heap entries
            if current_cost > min_costs[u_idx][0]:
                continue

            # No outgoing edges from the end node
            if u_idx == end_idx:
                break  # ← we've settled the destination; stop early

            u_node = all_nodes[u_idx]

            for v_idx in range(u_idx + 1, end_idx + 1):
                v_node = all_nodes[v_idx]

                # ── Segment distance ────────────────────
                # u.deviation was already "paid" when arriving at u.
                # Leaving u costs: back-to-route (u.dev) + on-route + v.dev
                route_diff       = v_node.route_mile_marker - u_node.route_mile_marker
                segment_distance = (
                    route_diff
                    + u_node.deviation_distance   # depart u back to route
                    + v_node.deviation_distance   # arrive at v off-route
                )

                # ── Feasibility ─────────────────────────
                # Conservative early-exit: if even the bare route gap exceeds
                # range, every subsequent v is also too far (list is sorted).
                if route_diff > self.vehicle_range:
                    break

                # Full distance check including deviations
                if segment_distance > self.vehicle_range:
                    continue

                # ── Edge weight ────────────────────────────────────────
                gallons   = segment_distance / self.mpg
                edge_cost = gallons * u_node.retail_price
                new_cost  = current_cost + edge_cost

                if new_cost < min_costs.get(v_idx, (INF, None))[0]:
                    min_costs[v_idx] = (new_cost, u_idx)
                    heapq.heappush(pq, (new_cost, v_idx))

        # ── Reachability check ────────────────────────────────────────
        if end_idx not in min_costs:
            return [], -1.0, [], 0.0, []

        # ── Reconstruct path ──────────────────────────────────────────
        path_indices = self._reconstruct_path(min_costs, end_idx)

        # ── Build result objects ──────────────────────────────────────
        avg_price    = sum(s.retail_price for s in stations) / len(stations)
        fuel_stops   = []
        total_gallons = 0.0

        for i in range(len(path_indices) - 1):
            u_idx  = path_indices[i]
            v_idx  = path_indices[i + 1]
            u_node = all_nodes[u_idx]
            v_node = all_nodes[v_idx]

            route_diff   = v_node.route_mile_marker - u_node.route_mile_marker
            dist         = (
                route_diff
                + u_node.deviation_distance
                + v_node.deviation_distance
            )
            gallons      = dist / self.mpg
            total_gallons += gallons
            cost         = gallons * u_node.retail_price

            if u_node.retail_price > 0:
                score = self._calculate_score(u_node, avg_price)
                fuel_stops.append(FuelStopDecision(
                    station        = u_node,
                    mile_marker    = u_node.route_mile_marker,
                    gallons_filled = round(gallons, 2),
                    cost           = round(cost, 2),
                    price_per_gallon = u_node.retail_price,
                    score          = score,
                ))

        final_cost = min_costs[end_idx][0]
        tracker    = self._generate_tracker(path_indices, all_nodes)
        refuel_path = self._build_refuel_path(path_indices, all_nodes)

        return (
            fuel_stops,
            round(final_cost, 2),
            tracker,
            round(total_gallons, 2),
            refuel_path,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_virtual_node(
        node_id: int,
        name: str,
        mile: float,
        price: float,
    ) -> FuelStation:
        return FuelStation(
            id=node_id, truckstop_name=name, address="", city="", state="",
            rack_id=0, retail_price=price, latitude=0.0, longitude=0.0,
            deviation_distance=0.0, route_mile_marker=mile, h3_index="",
        )

    @staticmethod
    def _start_price(sorted_stations: List[FuelStation]) -> float:
        local = [s for s in sorted_stations if s.route_mile_marker <= 15.0]
        if local:
            return min(s.retail_price for s in local)
        if sorted_stations:
            return sum(s.retail_price for s in sorted_stations) / len(sorted_stations)
        return 3.5

    @staticmethod
    def _reconstruct_path(
        min_costs: Dict[int, Tuple[float, Optional[int]]],
        end_idx: int,
    ) -> List[int]:
        path: List[int] = []
        curr: Optional[int] = end_idx
        while curr is not None:
            path.append(curr)
            curr = min_costs[curr][1]
        path.reverse()
        return path

    def _calculate_score(self, station: FuelStation, avg_price: float) -> float:
        if avg_price <= 0:
            return 5.0

        # 0 = at avg price, positive = cheaper than avg, negative = dearer
        price_score = 1.0 - (station.retail_price / avg_price)   # −∞ … 1
        price_score = max(-1.0, min(1.0, price_score))            # clamp

        # deviation: 0 miles → 1.0, vehicle_range miles → 0.0
        dev_norm = station.deviation_distance / max(self.vehicle_range, 1.0)
        dev_score = 1.0 - min(dev_norm, 1.0)

        raw = (self.price_weight * price_score + self.deviation_weight * dev_score)
        # raw ∈ [-0.6, 1.0]; shift and scale to [0, 10]
        score = (raw + self.price_weight) / (1.0 + self.price_weight) * 10.0
        return round(max(0.0, min(10.0, score)), 2)

    def _generate_tracker(
        self,
        path_indices: List[int],
        all_nodes: List[FuelStation],
    ) -> List[Dict]:
        tracker: List[Dict] = []
        cumulative_spent = 0.0

        for i in range(len(path_indices) - 1):
            u_idx  = path_indices[i]
            v_idx  = path_indices[i + 1]
            u_node = all_nodes[u_idx]
            v_node = all_nodes[v_idx]

            start_m = round(u_node.route_mile_marker)
            end_m   = round(v_node.route_mile_marker)

            dist_real = (
                (v_node.route_mile_marker - u_node.route_mile_marker)
                + u_node.deviation_distance
                + v_node.deviation_distance
            )

            segment_cost  = (dist_real / self.mpg) * u_node.retail_price
            cost_per_mile = segment_cost / max(dist_real, 1e-9)

            if start_m >= end_m:
                cumulative_spent += segment_cost
                tracker.append({
                    "mile":        start_m,
                    "total_spent": round(cumulative_spent, 2),
                })
                continue

            miles_in_segment = end_m - start_m
            per_integer_mile = segment_cost / miles_in_segment

            for m in range(start_m + 1, end_m + 1):
                cumulative_spent += per_integer_mile
                tracker.append({
                    "mile":        m,
                    "total_spent": round(cumulative_spent, 2),
                })

        return tracker

    def _build_refuel_path(
        self,
        path_indices: List[int],
        all_nodes: List[FuelStation],
    ) -> List[Dict]:
        end_idx = len(all_nodes) - 1
        route   = []
        for idx in path_indices:
            node = all_nodes[idx]
            route.append({
                "node_type":   "start"   if node.id == -1
                               else "end" if node.id == -2
                               else "station",
                "name":        node.truckstop_name,
                "mile_marker": round(node.route_mile_marker, 2),
                "price":       node.retail_price,
                "refuel":      node.id not in (-1, -2) or node.id == -1,
                # ^ refuel at every stop including the start depot;
                #   end node never needs refuelling.
            })

        if route and route[-1]["node_type"] == "end":
            route[-1]["refuel"] = False
        return route