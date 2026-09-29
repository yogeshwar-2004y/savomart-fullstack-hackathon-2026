import type { Marker as LeafletMarker } from "leaflet";
import { MapContainer, Marker, TileLayer, useMapEvents } from "react-leaflet";

type Props = { latitude: number; longitude: number; onChange: (latitude: number, longitude: number) => void; editable?: boolean };

export function PropertyPinMap({ latitude, longitude, onChange, editable = true }: Props) {
  return <MapContainer className="property-pin-map" center={[latitude, longitude]} zoom={16} scrollWheelZoom>
    <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
    <Marker position={[latitude, longitude]} draggable={editable} eventHandlers={{ dragend: (event) => { const point = (event.target as LeafletMarker).getLatLng(); onChange(point.lat, point.lng); } }} />
    {editable ? <MapClick onChange={onChange} /> : null}
  </MapContainer>;
}

function MapClick({ onChange }: { onChange: Props["onChange"] }) {
  useMapEvents({ click: (event) => onChange(event.latlng.lat, event.latlng.lng) });
  return null;
}
