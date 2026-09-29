import type { GeoJsonObject } from "geojson";
import L from "leaflet";
import { useEffect } from "react";
import { CircleMarker, GeoJSON, MapContainer, Marker, Popup, TileLayer, useMap, useMapEvents } from "react-leaflet";
import type { GeoJSONGeometry, StoreLocation, Suggestion } from "../services/m1";

const CHENNAI_CENTER: [number, number] = [13.03, 80.22];

type Props = {
  geometry: GeoJSONGeometry | null;
  suggestions: Suggestion[];
  stores: StoreLocation[];
  cellMode: boolean;
  onCellClick: (lat: number, lon: number) => void;
};

function MapEvents({ enabled, onCellClick }: { enabled: boolean; onCellClick: Props["onCellClick"] }) {
  useMapEvents({
    click(event) {
      if (enabled) onCellClick(event.latlng.lat, event.latlng.lng);
    }
  });
  return null;
}

function FitGeometry({ geometry }: { geometry: GeoJSONGeometry | null }) {
  const map = useMap();
  if (geometry) {
    const layer = new L.GeoJSON(geometry as GeoJsonObject);
    const bounds = layer.getBounds();
    if (bounds.isValid() && !map.getBounds().contains(bounds)) map.fitBounds(bounds, { padding: [24, 24] });
  }
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

const storeIcon = L.divIcon({
  className: "savo-store-marker",
  html: '<span class="savo-store-pin"><b>S</b></span>',
  iconAnchor: [16, 36], iconSize: [32, 38], tooltipAnchor: [0, -30],
});

export function AreaMap({ geometry, suggestions, stores, cellMode, onCellClick }: Props) {
  return (
    <MapContainer center={CHENNAI_CENTER} zoom={11} className={cellMode ? "area-map selecting" : "area-map"}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <MapEvents enabled={cellMode} onCellClick={onCellClick} />
      <ResizeMap />
      <FitGeometry geometry={geometry} />
      {geometry ? <GeoJSON key={JSON.stringify(geometry)} data={geometry as GeoJsonObject} style={{ color: "#782B90", weight: 3, fillColor: "#FFF200", fillOpacity: 0.22 }} /> : null}
      {stores.map((store) => <Marker key={store.store_code} position={[store.latitude, store.longitude]} icon={storeIcon} zIndexOffset={500}><Popup><strong>SAVOmart {store.name}</strong><p>{store.address}</p><small>{store.source_status} · source fetched {new Date(store.retrieved_at).toLocaleString()}</small></Popup></Marker>)}
      {suggestions.map((suggestion) => (
        <CircleMarker key={`${suggestion.rank}-${suggestion.latitude}`} center={[suggestion.latitude, suggestion.longitude]} radius={8} pathOptions={{ color: "#fff", weight: 2, fillColor: "#E25430", fillOpacity: 1 }}>
          <Popup><strong>{suggestion.rank}. {suggestion.label}</strong><p>{suggestion.rationale}</p><small>Open the saved report below to assign this hotspot.</small></Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
