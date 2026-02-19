export interface FuelStop {
  truckstop_name: string;
  city: string;
  state: string;
  price_per_gallon: number;
  gallons_filled: number;
  cost: number;
  mile_marker: number;
  score: number;
}

export interface FuelSummary {
  total_cost: number;
  total_gallons: number;
  total_stops: number;
}

export interface Route {
  distance_miles: number;
  duration_minutes: number;
  polyline: string; // encoded polyline string
}

export interface ProgressionItem {
  mile: number;
  total_spent: number;
}

export interface RouteResponse {
  route: Route;
  fuel_summary: FuelSummary;
  stops: FuelStop[];
  per_mile_progression: ProgressionItem[];
}