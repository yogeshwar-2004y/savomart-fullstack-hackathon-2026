import type { Marker as LeafletMarker } from "leaflet";
import { useEffect } from "react";
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";

type Props = { latitude: number; longitude: number; onChange: (latitude: number, longitude: number) => void; editable?: boolean };

export function PropertyPinMap({ latitude, longitude, onChange, editable = true }: Props) {
  return <div className="operational-map-shell property-map-shell"><MapContainer className="property-pin-map" center={[latitude, longitude]} zoom={16} scrollWheelZoom>
    <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
    <Marker position={[latitude, longitude]} draggable={editable} eventHandlers={{ dragend: (event) => { const point = (event.target as LeafletMarker).getLatLng(); onChange(point.lat, point.lng); } }} />
    {editable ? <MapClick onChange={onChange} /> : null}
    <ResizeMap />
  </MapContainer><div className="map-overlay-legend compact"><span><i className="overlay-point" />Property pin{editable ? " (drag to correct)" : ""}</span></div></div>;
}

function MapClick({ onChange }: { onChange: Props["onChange"] }) {
  useMapEvents({ click: (event) => onChange(event.latlng.lat, event.latlng.lng) });
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
