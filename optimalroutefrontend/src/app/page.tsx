"use client";
import { Button } from "@/components/ui/button";
import { RouteInputCard } from "@/components/route/RouteInputCard";
import { RouteResultsPanel } from "@/components/route/RouteResultsPanel";
import dynamic from "next/dynamic";

const RouteMap = dynamic(() => import("@/components/map/RouteMap").then(mod => mod.RouteMap), { ssr: false });

import { useState } from "react";
import { fetchRoute } from "@/services/api";
import { RouteResponse } from "@/types/route";

export default function Home() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<RouteResponse | null>(null);

  const handleSubmit = async (form: { start: string; end: string }) => {
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const res = await fetchRoute(form.start, form.end);
      setData(res);
    } catch (e: any) {
      setError(e.message || "Failed to fetch route");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center bg-gradient-to-br from-zinc-50 to-blue-50 dark:from-black dark:to-zinc-900 font-sans">
      <main className="flex flex-col items-center justify-center w-full max-w-2xl px-6 py-24 rounded-3xl shadow-xl bg-white/90 dark:bg-zinc-900/90">
        <div className="flex flex-col items-center gap-6 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            Smart Route & Fuel Cost Optimizer
          </h1>
          <p className="max-w-xl text-lg sm:text-xl text-zinc-600 dark:text-zinc-300">
            Instantly plan the most cost-effective route across the USA. Get optimal fuel stops, real-time prices, and total trip cost—powered by smart data and beautiful maps.
          </p>
          <Button size="lg" className="mt-4 px-8 py-4 text-lg font-semibold shadow-lg" asChild>
            <a href="#plan-route">Plan Route</a>
          </Button>
        </div>
      </main>
      <div className="w-full flex justify-center mt-8 mb-16">
        <RouteInputCard onSubmit={handleSubmit} loading={loading} />
      </div>

      {/* Results Split Layout */}
      <div className="w-full max-w-6xl flex flex-col md:flex-row gap-8 px-4 md:px-0 mb-16">
        <div className="md:w-2/5 w-full">
          {data && (
            <RouteResultsPanel
              summary={{
                totalDistance: data.route.distance_miles,
                totalStops: data.fuel_summary.total_stops,
                totalCost: data.fuel_summary.total_cost,
                mpg: 10,
              }}
              stops={data.stops.map((stop, idx) => ({
                id: idx.toString(),
                city: stop.city + ", " + stop.state,
                address: stop.truckstop_name,
                price: stop.price_per_gallon,
                gallons: stop.gallons_filled,
                cost: stop.cost,
                lat: undefined,
                lng: undefined,
                details: `Score: ${stop.score}, Mile Marker: ${stop.mile_marker}`,
              }))}
            />
          )}
        </div>
        <div className="md:w-3/5 w-full">
          {data && (
            <RouteMap
              polyline={decodePolyline(data.route.polyline)}
              stops={data.stops.map((stop, idx) => ({
                id: idx.toString(),
                city: stop.city + ", " + stop.state,
                address: stop.truckstop_name,
                price: stop.price_per_gallon,
                gallons: stop.gallons_filled,
                cost: stop.cost,
                lat: undefined,
                lng: undefined,
                details: `Score: ${stop.score}, Mile Marker: ${stop.mile_marker}`,
              }))}
            />
          )}
        </div>
      </div>
      {error && <div className="text-red-600 font-semibold">{error}</div>}
    </div>
  );
}


// Polyline decoding utility for Google/OSM encoded polylines
function decodePolyline(encoded: string): [number, number][] {
  let index = 0, lat = 0, lng = 0, coordinates: [number, number][] = [];
  const len = encoded.length;
  while (index < len) {
    let b, shift = 0, result = 0;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    const dlat = (result & 1) ? ~(result >> 1) : (result >> 1);
    lat += dlat;

    shift = 0;
    result = 0;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    const dlng = (result & 1) ? ~(result >> 1) : (result >> 1);
    lng += dlng;

    coordinates.push([lng / 1e5, lat / 1e5]);
  }
  return coordinates;
}
