import L from "leaflet";
import { useEffect } from "react";
import { CircleMarker, GeoJSON, MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";
import type { GeoJSONGeometry } from "../services/m1";
import type { MappedLaneSuggestion } from "../services/m3";

type Shape = { geometry: GeoJSONGeometry; color: string; label?: string };

export function CatchmentMap({
  shapes,
  point,
  onPointChange,
  lanes = [],
  surveyPoints = [],
}: {
  shapes: Shape[];
  point?: { latitude: number; longitude: number };
  onPointChange?: (latitude: number, longitude: number) => void;
  lanes?: Array<MappedLaneSuggestion & { included: boolean }>;
  surveyPoints?: Array<{ latitude: number; longitude: number; flagged: boolean }>;
}) {
  return (
    <div className="operational-map-shell">
      <MapContainer className="catchment-map" center={[12.98, 80.22]} zoom={14} scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {shapes.map((shape, index) => (
          <GeoJSON
            key={`${shape.label}-${index}`}
            data={shape.geometry as GeoJSON.GeoJsonObject}
            style={{ color: shape.color || "#782B90", fillOpacity: 0.14, weight: 3 }}
          />
        ))}
        {lanes.map((lane) => (
          <GeoJSON
            key={lane.id}
            data={lane.geometry as GeoJSON.GeoJsonObject}
            style={{
              color: lane.included ? "#782B90" : "#a19da6",
              weight: lane.included ? 5 : 2.5,
              opacity: lane.included ? 0.95 : 0.45,
            }}
          />
        ))}
        {surveyPoints.map((item, index) => (
          <CircleMarker
            key={`${item.latitude}-${item.longitude}-${index}`}
            center={[item.latitude, item.longitude]}
            radius={6}
            pathOptions={{
              color: "#fff",
              weight: 2,
              fillColor: item.flagged ? "#b42318" : "#16835f",
              fillOpacity: 1,
            }}
          />
        ))}
        {point ? (
          <Marker
            position={[point.latitude, point.longitude]}
            draggable={!!onPointChange}
            eventHandlers={{
              dragend: (event) => {
                const next = (event.target as L.Marker).getLatLng();
                onPointChange?.(next.lat, next.lng);
              },
            }}
          />
        ) : null}
        {onPointChange ? <MapPoint onChange={onPointChange} /> : null}
        <Fit shapes={shapes} />
        <ResizeMap />
      </MapContainer>
      <div className="map-overlay-legend compact" aria-label="Catchment map legend">
        <span><i className="overlay-boundary" /> Target Catchment</span>
        <span><i className="overlay-zone" /> Survey Zone</span>
        {lanes.length ? <span><i className="overlay-lane" /> Mapped Lane</span> : null}
        {surveyPoints.length ? <span><i className="overlay-survey" /> Field Observation</span> : null}
        {point ? <span><i className="overlay-point" /> Location Pin</span> : null}
      </div>
    </div>
  );
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

function ResizeMap() {
  const map = useMap();
  useEffect(() => {
    const observer = new ResizeObserver(() => map.invalidateSize({ animate: false }));
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);
  return null;
}
