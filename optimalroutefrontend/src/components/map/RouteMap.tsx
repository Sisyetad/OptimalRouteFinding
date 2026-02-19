"use client";
import { MapContainer, TileLayer, Polyline, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { useMemo } from "react";

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

interface RouteMapProps {
  polyline: [number, number][];
  stops: FuelStopUI[];
}

const defaultCenter: [number, number] = [39.8283, -98.5795]; // Center of USA

export function RouteMap({ polyline, stops }: RouteMapProps) {
  // Calculate map center
  const center = useMemo(() => {
    if (polyline && polyline.length > 0) return [polyline[0][1], polyline[0][0]] as [number, number];
    return defaultCenter;
  }, [polyline]);

  // Convert polyline to [lat, lng] for Leaflet
  const leafletPolyline = useMemo(() =>
    polyline.map(([lng, lat]) => [lat, lng] as [number, number]),
    [polyline]
  );

  return (
    <MapContainer
      center={center}
      zoom={5}
      scrollWheelZoom={true}
      className="w-full h-96 rounded-2xl shadow-lg"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {leafletPolyline.length > 0 && (
        <Polyline positions={leafletPolyline} color="#2563eb" weight={4} />
      )}
      {stops && stops.map((stop) =>
        stop.lat !== undefined && stop.lng !== undefined ? (
          <Marker
            key={stop.id}
            position={[stop.lat, stop.lng]}
            icon={L.icon({
              iconUrl: "https://unpkg.com/leaflet@1.9.3/dist/images/marker-icon.png",
              iconSize: [25, 41],
              iconAnchor: [12, 41],
              popupAnchor: [1, -34],
              shadowUrl: "https://unpkg.com/leaflet@1.9.3/dist/images/marker-shadow.png",
              shadowSize: [41, 41],
            })}
          >
            <Popup>
              <div>
                <b>{stop.city}</b><br />
                {stop.address}<br />
                Price: ${stop.price.toFixed(2)}<br />
                Gallons: {stop.gallons.toFixed(2)}<br />
                Cost: ${stop.cost.toFixed(2)}<br />
                {stop.details}
              </div>
            </Popup>
          </Marker>
        ) : null
      )}
    </MapContainer>
  );
}
