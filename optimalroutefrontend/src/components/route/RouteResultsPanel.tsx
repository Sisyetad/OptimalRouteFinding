"use client";
import { Card } from "@/components/ui/card";
import { useState } from "react";

interface FuelStopUI {
  id: string;
  city: string;
  address: string;
  price: number;
  gallons: number;
  cost: number;
  lat?: number;
  lng?: number;
  details?: string;
}

interface RouteSummaryUI {
  totalDistance: number;
  totalStops: number;
  totalCost: number;
  mpg: number;
}

interface RouteResultsPanelProps {
  summary: RouteSummaryUI;
  stops: FuelStopUI[];
}

export function RouteResultsPanel({ summary, stops }: RouteResultsPanelProps) {
  const [expanded, setExpanded] = useState<string | null>(null);
  if (!summary || !stops) {
    return (
      <Card className="w-full max-w-md p-6 rounded-2xl shadow-lg bg-white dark:bg-zinc-900 animate-pulse">
        <div className="h-8 bg-zinc-200 dark:bg-zinc-800 rounded w-1/2 mb-4"></div>
        <div className="h-4 bg-zinc-200 dark:bg-zinc-800 rounded w-1/3 mb-2"></div>
        <div className="h-4 bg-zinc-200 dark:bg-zinc-800 rounded w-1/4 mb-2"></div>
        <div className="h-4 bg-zinc-200 dark:bg-zinc-800 rounded w-1/2 mb-6"></div>
        <div className="h-6 bg-zinc-200 dark:bg-zinc-800 rounded w-full mb-2"></div>
        <div className="h-6 bg-zinc-200 dark:bg-zinc-800 rounded w-3/4 mb-2"></div>
        <div className="h-6 bg-zinc-200 dark:bg-zinc-800 rounded w-2/3"></div>
      </Card>
    );
  }
  return (
    <Card className="w-full max-w-md p-6 rounded-2xl shadow-lg bg-white dark:bg-zinc-900">
      <div className="mb-6">
        <h2 className="text-2xl font-bold mb-2">Route Summary</h2>
        <div className="flex flex-col gap-1 text-zinc-700 dark:text-zinc-200">
          <span>Total Distance: <b>{summary.totalDistance.toLocaleString()} mi</b></span>
          <span>Total Fuel Stops: <b>{summary.totalStops}</b></span>
          <span>Total Fuel Cost: <b className="text-green-600 dark:text-green-400 text-lg">${summary.totalCost.toFixed(2)}</b></span>
        </div>
      </div>
      <div>
        <h3 className="text-lg font-semibold mb-2">Fuel Stops</h3>
        <ul className="flex flex-col gap-3">
          {stops.map((stop) => (
            <li key={stop.id} className="border rounded-lg p-3 bg-zinc-50 dark:bg-zinc-800">
              <div className="flex justify-between items-center">
                <div>
                  <div className="font-medium">{stop.city}</div>
                  <div className="text-xs text-zinc-500">{stop.address}</div>
                </div>
                <button
                  className="text-blue-600 dark:text-blue-400 text-xs underline"
                  onClick={() => setExpanded(expanded === stop.id ? null : stop.id)}
                >
                  {expanded === stop.id ? "Hide" : "Details"}
                </button>
              </div>
              <div className="flex gap-4 mt-2 text-sm">
                <span>Price: <b>${stop.price.toFixed(2)}</b></span>
                <span>Gallons: <b>{stop.gallons.toFixed(2)}</b></span>
                <span>Cost: <b>${stop.cost.toFixed(2)}</b></span>
              </div>
              {expanded === stop.id && stop.details && (
                <div className="mt-2 text-xs text-zinc-600 dark:text-zinc-300 animate-fade-in">
                  {stop.details}
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>
    </Card>
  );
}
