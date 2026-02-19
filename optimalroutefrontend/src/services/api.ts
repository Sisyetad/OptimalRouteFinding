import { RouteResponse } from "@/types/route";

export async function fetchRoute(
  start_location: string,
  end_location: string
): Promise<RouteResponse> {
  // Use your backend server URL directly (adjust if needed)
  const res = await fetch("http://localhost:8000/api/v1/plan-trip/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ start_location, end_location }),
  });
  if (!res.ok) throw new Error("Failed to fetch route");
  return res.json();
}
