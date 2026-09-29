import { AlertCircle, Camera, CheckCircle2, Crosshair, LoaderCircle, MapPin } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { PropertyPinMap } from "./PropertyPinMap";
import { captureProperty, listAssignments, type Assignment, type PropertyRecord } from "../services/m2";

type FormState = {
  address: string; rent_monthly: string; size_sq_ft: string; frontage_ft: string; road_width_ft: string;
  property_type: string; floor_level: string; visibility_rating: string; condition_rating: string;
  parking_available: boolean; power_backup: boolean; water_available: boolean; notes: string;
};
const initialForm: FormState = { address: "", rent_monthly: "", size_sq_ft: "", frontage_ft: "", road_width_ft: "", property_type: "street_shop", floor_level: "ground", visibility_rating: "3", condition_rating: "3", parking_available: false, power_backup: false, water_available: false, notes: "" };

export function ExecutiveWorkspace() {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [selected, setSelected] = useState<Assignment | null>(null);
  const [form, setForm] = useState<FormState>(initialForm);
  const [pin, setPin] = useState({ latitude: 12.9815, longitude: 80.218 });
  const [photos, setPhotos] = useState<File[]>([]);
  const [saved, setSaved] = useState<PropertyRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    setLoading(true);
    try { setAssignments(await listAssignments()); setError(""); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load assignments"); }
    finally { setLoading(false); }
  }
  useEffect(() => { void refresh(); }, []);

  function choose(item: Assignment) {
    setSelected(item); setPin({ latitude: item.latitude, longitude: item.longitude }); setSaved(null); setError(""); setForm(initialForm); setPhotos([]);
  }

  function useGps() {
    if (!navigator.geolocation) { setError("GPS is not available on this device. Correct the pin on the map."); return; }
    navigator.geolocation.getCurrentPosition(
      (position) => { setPin({ latitude: position.coords.latitude, longitude: position.coords.longitude }); setError(""); },
      () => setError("Location permission was unavailable. Drag or tap the map to correct the pin."),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); if (!selected) return;
    setSaving(true); setError("");
    const numberOrNull = (value: string) => value ? Number(value) : null;
    try {
      const property = await captureProperty(selected.id, {
        ...form, latitude: pin.latitude, longitude: pin.longitude,
        rent_monthly: Number(form.rent_monthly), size_sq_ft: Number(form.size_sq_ft),
        frontage_ft: numberOrNull(form.frontage_ft), road_width_ft: numberOrNull(form.road_width_ft),
        visibility_rating: Number(form.visibility_rating), condition_rating: Number(form.condition_rating)
      }, photos);
      setSaved(property); setSelected(null); await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not save property"); }
    finally { setSaving(false); }
  }

  if (loading) return <section className="m2-workspace state-panel"><LoaderCircle className="spin" /> Loading assignments</section>;
  return <section className="m2-workspace executive-workspace">
    <header className="m2-heading"><div><p className="eyebrow">M2 Property Scouting</p><h2>My scouting assignments</h2></div><button className="icon-button quiet" title="Refresh assignments" onClick={refresh}>↻</button></header>
    {error ? <div className="inline-error"><AlertCircle size={18} />{error}</div> : null}
    {saved ? <div className="success-banner"><CheckCircle2 size={20} /><span><strong>Property captured and evaluated</strong><small>Score {saved.evaluations.at(-1)?.score.toFixed(1)} · {saved.evaluations.at(-1)?.rating}</small></span></div> : null}
    {!assignments.length ? <div className="empty-panel"><MapPin /><h3>No assignments yet</h3><p>A manager can assign a hotspot from a saved M1 report.</p></div> : null}
    {!selected ? <div className="assignment-list">{assignments.map((item) => <button className="assignment-card" key={item.id} onClick={() => !item.property_id && choose(item)} disabled={!!item.property_id}><span className={`stage-chip ${item.status}`}>{item.status}</span><strong>{item.target_label}</strong><span>{item.area_name}</span><small>{item.instructions || "Scout this hotspot and capture a viable property."}</small>{item.property_id ? <b>Property submitted</b> : <b>Open assignment</b>}</button>)}</div> : null}
    {selected ? <form className="property-form" onSubmit={submit}>
      <div className="form-title"><div><p className="eyebrow">Assigned hotspot</p><h2>{selected.target_label}</h2><p>{selected.area_name} · {selected.instructions || "No extra instructions"}</p></div><button type="button" className="secondary-button" onClick={() => setSelected(null)}>Back</button></div>
      <section className="form-section"><div className="section-heading"><h3>Location</h3><button type="button" className="secondary-button compact" onClick={useGps}><Crosshair size={16} />Use GPS</button></div><PropertyPinMap key={selected.id} latitude={pin.latitude} longitude={pin.longitude} onChange={(latitude, longitude) => setPin({ latitude, longitude })} /><small>Drag the pin or tap the map to correct GPS before submitting.</small><label>Street address<input required minLength={5} value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} placeholder="Door number, street, locality" /></label><div className="coordinate-row"><span>Lat {pin.latitude.toFixed(6)}</span><span>Lng {pin.longitude.toFixed(6)}</span></div></section>
      <section className="form-section"><h3>Commercial details</h3><div className="form-grid"><label>Monthly rent (INR)<input required type="number" min="1" value={form.rent_monthly} onChange={(event) => setForm({ ...form, rent_monthly: event.target.value })} /></label><label>Size (sq ft)<input required type="number" min="100" value={form.size_sq_ft} onChange={(event) => setForm({ ...form, size_sq_ft: event.target.value })} /></label><label>Frontage (ft)<input type="number" min="1" value={form.frontage_ft} onChange={(event) => setForm({ ...form, frontage_ft: event.target.value })} /></label><label>Road width (ft)<input type="number" min="1" value={form.road_width_ft} onChange={(event) => setForm({ ...form, road_width_ft: event.target.value })} /></label><label>Property type<select value={form.property_type} onChange={(event) => setForm({ ...form, property_type: event.target.value })}><option value="street_shop">Street shop</option><option value="standalone">Standalone</option><option value="mall_unit">Mall unit</option><option value="mixed_use">Mixed use</option></select></label><label>Floor<select value={form.floor_level} onChange={(event) => setForm({ ...form, floor_level: event.target.value })}><option value="ground">Ground</option><option value="ground_plus_one">Ground + one</option><option value="upper_floor">Upper floor</option><option value="basement">Basement</option></select></label><label>Visibility (1-5)<input required type="number" min="1" max="5" value={form.visibility_rating} onChange={(event) => setForm({ ...form, visibility_rating: event.target.value })} /></label><label>Condition (1-5)<input required type="number" min="1" max="5" value={form.condition_rating} onChange={(event) => setForm({ ...form, condition_rating: event.target.value })} /></label></div><div className="check-row">{(["parking_available", "power_backup", "water_available"] as const).map((key) => <label key={key}><input type="checkbox" checked={form[key]} onChange={(event) => setForm({ ...form, [key]: event.target.checked })} />{key.replaceAll("_", " ")}</label>)}</div><label>Notes<textarea value={form.notes} maxLength={3000} onChange={(event) => setForm({ ...form, notes: event.target.value })} placeholder="Owner, access, constraints, and follow-up notes" /></label></section>
      <section className="form-section"><h3>Photos</h3><label className="photo-input"><Camera size={20} /><span>Add JPEG, PNG, or WebP · max 5 MB each</span><input type="file" accept="image/jpeg,image/png,image/webp" multiple capture="environment" onChange={(event) => setPhotos(Array.from(event.target.files ?? []))} /></label>{photos.length ? <small>{photos.length} photo{photos.length === 1 ? "" : "s"} selected</small> : null}</section>
      <button className="primary-button submit-property" disabled={saving}>{saving ? <LoaderCircle className="spin" size={18} /> : <Camera size={18} />}{saving ? "Evaluating property" : "Save and evaluate"}</button>
    </form> : null}
  </section>;
}
