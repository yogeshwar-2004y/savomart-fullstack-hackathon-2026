import L from "leaflet";
import { useEffect } from "react";
import { GeoJSON, MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";
import type { GeoJSONGeometry } from "../services/m1";

type Shape = { geometry: GeoJSONGeometry; color: string; label?: string };

export function CatchmentMap({
  shapes, point, onPointChange
}: {
  shapes: Shape[];
  point?: { latitude: number; longitude: number };
  onPointChange?: (latitude: number, longitude: number) => void;
}) {
  return <MapContainer className="catchment-map" center={[12.98, 80.22]} zoom={14} scrollWheelZoom>
    <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
    {shapes.map((shape, index) => <GeoJSON key={`${shape.label}-${index}`} data={shape.geometry as GeoJSON.GeoJsonObject} style={{ color: shape.color, fillOpacity: .12, weight: 3 }} />)}
    {point ? <Marker position={[point.latitude, point.longitude]} draggable={!!onPointChange} eventHandlers={{ dragend: (event) => { const next = (event.target as L.Marker).getLatLng(); onPointChange?.(next.lat, next.lng); } }} /> : null}
    {onPointChange ? <MapPoint onChange={onPointChange} /> : null}
    <Fit shapes={shapes} />
  </MapContainer>;
}

function MapPoint({ onChange }: { onChange: (latitude: number, longitude: number) => void }) {
  useMapEvents({ click: (event) => onChange(event.latlng.lat, event.latlng.lng) });
  return null;
}

function Fit({ shapes }: { shapes: Shape[] }) {
  const map = useMap();
  useEffect(() => {
    if (!shapes.length) return;
    const group = L.featureGroup(shapes.map((shape) => L.geoJSON(shape.geometry as GeoJSON.GeoJsonObject)));
    const bounds = group.getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [20, 20], maxZoom: 16 });
  }, [map, shapes]);
  return null;
}
