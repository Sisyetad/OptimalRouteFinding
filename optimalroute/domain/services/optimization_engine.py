import heapq
from typing import List, Tuple, Dict
from domain.entities.station import FuelStation, FuelStopDecision

class FuelOptimizationEngine:
    def __init__(self, vehicle_range: float = 500.0, mpg: float = 10.0):
        self.vehicle_range = vehicle_range
        self.mpg = mpg
        # Weights for the scoring mechanism
        self.price_weight = 10.0
        self.deviation_weight = 2.0
        self.detour_penalty = 5.0

    def plan_trip(self, route_distance: float, stations: List[FuelStation]) -> Tuple[List[FuelStopDecision], float, List[Dict], float]:
        """
        Plans fuel stops using a Dijkstra-based Shortest Path algorithm to minimize total fuel cost.
        Returns: (stops, total_cost, per_mile_progression, total_gallons)
        """
        # Sort stations by mile marker 
        sorted_stations = sorted(stations, key=lambda s: s.route_mile_marker)

        # Determine price at start: Cheapest station within 15 miles, else average
        start_buffer = 15.0
        local_stations = [s for s in sorted_stations if s.route_mile_marker <= start_buffer]
        
        if local_stations:
            start_price = min(s.retail_price for s in local_stations)
        elif stations:
            start_price = sum(s.retail_price for s in stations) / len(stations)
        else:
            start_price = 3.5

        # 1. Setup Nodes: Start (0) -> Stations -> End (route_distance)
        start_node = FuelStation(
            id=-1, truckstop_name="Start", address="", city="", state="", 
            rack_id=0, retail_price=start_price, latitude=0, longitude=0, 
            deviation_distance=0, route_mile_marker=0, h3_index=""
        )
        end_node = FuelStation(
            id=-2, truckstop_name="End", address="", city="", state="", 
            rack_id=0, retail_price=0.0, latitude=0, longitude=0, 
            deviation_distance=0, route_mile_marker=route_distance, h3_index=""
        )
        all_nodes = [start_node] + sorted_stations + [end_node]
        
        # 2. Dijkstra's Algorithm
        # min_costs[node_index] = (min_cost_to_reach_node, parent_node_index)
        min_costs = {0: (0.0, None)}
        
        # Priority Queue: (current_accumulated_cost, node_index)
        pq = [(0.0, 0)]
        
        while pq:
            current_cost, u_idx = heapq.heappop(pq)
            
            if current_cost > min_costs[u_idx][0]:
                continue
            
            if u_idx == len(all_nodes) - 1: # Reached End
                continue

            u_node = all_nodes[u_idx]
            
            # Explore neighbors (forward only to avoid cycles in this DAG formulation)
            for v_idx in range(u_idx + 1, len(all_nodes)):
                v_node = all_nodes[v_idx]
                
                # Check feasibility
                # Distance includes deviation to and from stations
                # We simplified: route_diff + v.deviation + u.deviation
                # (Assuming deviation adds linearly to the route distance segment)
                
                route_dist = v_node.route_mile_marker - u_node.route_mile_marker
                
                # Distance we drive = Route Distance + Deviation to get TO V + Deviation to get BACK to route from U
                # (Assuming deviation means one-way distance from polyline)
                segment_drive_dist = route_dist + v_node.deviation_distance + u_node.deviation_distance
                
                if segment_drive_dist > self.vehicle_range:
                    if route_dist > self.vehicle_range: # Heuristic break for sorted list
                        break
                    continue
                
                # Cost Calculation
                # We assume we pay for ALL fuel consumed, including initial fuel
                gallons_needed = segment_drive_dist / self.mpg
                fuel_cost = gallons_needed * u_node.retail_price
                
                new_total_cost = current_cost + fuel_cost
                
                if v_idx not in min_costs or new_total_cost < min_costs[v_idx][0]:
                    min_costs[v_idx] = (new_total_cost, u_idx)
                    heapq.heappush(pq, (new_total_cost, v_idx))

        # 3. Reconstruct Path
        end_idx = len(all_nodes) - 1
        if end_idx not in min_costs:
            # If unreachable even for Dijkstra
            return [], -1.0, [], 0.0 
            
        path_indices = []
        curr = end_idx
        while curr is not None:
            path_indices.append(curr)
            curr = min_costs[curr][1]
        
        path_indices.reverse() # Now Start -> S1 -> S2 -> End
        
        # 4. Build Result Objects
        fuel_stops = []
        total_gallons = 0.0
        
        # Recalculate avg_price for scoring purposes (using all available stations)
        avg_price = sum(s.retail_price for s in stations) / len(stations) if stations else 3.5
        
        for i in range(len(path_indices) - 1):
            u_idx = path_indices[i]
            v_idx = path_indices[i+1]
            
            u_node = all_nodes[u_idx]
            v_node = all_nodes[v_idx]
            
            dist = (v_node.route_mile_marker - u_node.route_mile_marker) + \
                   v_node.deviation_distance + u_node.deviation_distance
                   
            gallons_needed = dist / self.mpg
            total_gallons += gallons_needed
            
            if u_idx != 0: # If it's a station stop (not start)
                cost = gallons_needed * u_node.retail_price
                score = self._calculate_score(u_node, avg_price)
                
                stop = FuelStopDecision(
                    station=u_node,
                    mile_marker=u_node.route_mile_marker,
                    gallons_filled=round(gallons_needed, 2),
                    cost=round(cost, 2),
                    price_per_gallon=u_node.retail_price,
                    score=score
                )
                fuel_stops.append(stop)

        final_cost = min_costs[end_idx][0]
        
        # 5. Generate Tracker
        tracker = self._generate_tracker(path_indices, all_nodes, min_costs)

        return fuel_stops, round(final_cost, 2), tracker, round(total_gallons, 2)

    def _calculate_score(self, station: FuelStation, avg_price: float) -> float:
        norm_price = station.retail_price / avg_price if avg_price else 1.0
        
        penalty = (self.price_weight * norm_price) + \
                  (self.deviation_weight * station.deviation_distance)
                  
        return round(10.0 / (1.0 + penalty * 0.1), 2)

    def _generate_tracker(self, path_indices: List[int], all_nodes: List[FuelStation], min_costs: Dict) -> List[Dict]:
        tracker = []
        cumulative_spent = 0.0
        
        for i in range(len(path_indices) - 1):
            u_idx = path_indices[i]
            v_idx = path_indices[i+1]
            u_node = all_nodes[u_idx]
            v_node = all_nodes[v_idx]
            
            start_m = int(u_node.route_mile_marker)
            end_m = int(v_node.route_mile_marker)
            
            # Distance U->V
            dist_miles = end_m - start_m
            
            # Cost for this segment
            # We assume cost was allocated at U for the trip to V.
            # So as we drive from U to V, we are "consuming" that cost.
            # But the requirement says "accumulate fuel burn".
            # Usually implies "Money spent so far".
            # Money is spent linearly as we burn fuel? Or spent in lump sums at pumps?
            # "progressive fuel spending" usually means accrued cost of fuel burned.
            
            segment_cost = 0.0
            
            # Distance drive (approx)
            dist_real = (v_node.route_mile_marker - u_node.route_mile_marker) + \
                    v_node.deviation_distance + u_node.deviation_distance
            
            # Start node (u_idx=0) now has a price (avg_price), so we calculate cost for it too.
            # Only skip if price is 0 (which shouldn't happen with our fix, unless no stations found)
            segment_cost = (dist_real / self.mpg) * u_node.retail_price
            
            cost_per_mile = segment_cost / dist_miles if dist_miles > 0 else 0
            
            for m in range(start_m + 1, end_m + 1):
                cumulative_spent += cost_per_mile
                tracker.append({
                    "mile": m,
                    "total_spent": round(cumulative_spent, 2)
                })
                
        return tracker
