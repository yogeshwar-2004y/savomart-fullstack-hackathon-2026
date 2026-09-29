import { AlertCircle, CheckCircle2, Crosshair, LoaderCircle, MapPin, RefreshCw, Save } from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import { completeSurveyZone, listSurveyZones, submitLane, type LaneSubmission, type SurveyZone } from "../services/m3";
import { CatchmentMap } from "./CatchmentMap";

type LaneForm = {
  lane_name: string; gps_accuracy_m: string; observed_at: string; residential_units: string;
  commercial_units: string; pedestrian_activity: string; vehicle_activity: string; notes: string;
};
const localDateTime = () => {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
};
const blankForm = (): LaneForm => ({ lane_name: "", gps_accuracy_m: "25", observed_at: localDateTime(), residential_units: "", commercial_units: "", pedestrian_activity: "3", vehicle_activity: "3", notes: "" });
const draftKey = (zoneId: string) => `sitescout-survey-draft:${zoneId}`;

export function SurveyExecutiveWorkspace() {
  const [zones, setZones] = useState<SurveyZone[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [form, setForm] = useState<LaneForm>(blankForm);
  const [point, setPoint] = useState({ latitude: 12.98, longitude: 80.22 });
  const [submissionId, setSubmissionId] = useState(crypto.randomUUID());
  const [lastSubmission, setLastSubmission] = useState<LaneSubmission | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const selected = useMemo(() => zones.find((zone) => zone.id === selectedId), [zones, selectedId]);

  async function refresh() {
    setLoading(true);
    try { setZones(await listSurveyZones()); setError(""); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load survey assignments"); }
    finally { setLoading(false); }
  }
  useEffect(() => { void refresh(); }, []);
  useEffect(() => {
    if (!selected) return;
    localStorage.setItem(draftKey(selected.id), JSON.stringify({ form, point, submissionId, savedAt: new Date().toISOString() }));
  }, [form, point, selected, submissionId]);

  function choose(zone: SurveyZone) {
    const stored = localStorage.getItem(draftKey(zone.id));
    if (stored) {
      try {
        const draft = JSON.parse(stored);
        setForm(draft.form); setPoint(draft.point); setSubmissionId(draft.submissionId);
      } catch { prepareFresh(zone); }
    } else prepareFresh(zone);
    setSelectedId(zone.id); setLastSubmission(null); setError("");
  }

  function prepareFresh(zone: SurveyZone) {
    setForm(blankForm()); setPoint(geometryCenter(zone.geometry.coordinates)); setSubmissionId(crypto.randomUUID());
  }

  function useGps() {
    navigator.geolocation?.getCurrentPosition(
      (position) => { setPoint({ latitude: position.coords.latitude, longitude: position.coords.longitude }); setForm((item) => ({ ...item, gps_accuracy_m: Math.round(position.coords.accuracy).toString() })); },
      () => setError("GPS was unavailable. Tap the map to record the observation location."),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  async function save(event: FormEvent) {
    event.preventDefault(); if (!selected) return;
    setSaving(true);
    try {
      const saved = await submitLane(selected.id, {
        client_submission_id: submissionId, lane_name: form.lane_name,
        latitude: point.latitude, longitude: point.longitude,
        gps_accuracy_m: Number(form.gps_accuracy_m), observed_at: new Date(form.observed_at).toISOString(),
        residential_units: Number(form.residential_units), commercial_units: Number(form.commercial_units),
        pedestrian_activity: Number(form.pedestrian_activity), vehicle_activity: Number(form.vehicle_activity),
        notes: form.notes || null, status: "submitted"
      });
      localStorage.removeItem(draftKey(selected.id)); setLastSubmission(saved);
      prepareFresh(selected); await refresh(); setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Submission failed; the local draft is preserved"); }
    finally { setSaving(false); }
  }

  async function complete() {
    if (!selected) return;
    try { await completeSurveyZone(selected.id); localStorage.removeItem(draftKey(selected.id)); setSelectedId(""); await refresh(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not complete zone"); }
  }

  if (loading) return <section className="m3-workspace state-panel"><LoaderCircle className="spin" /> Loading survey work</section>;
  return <section className="m3-workspace survey-executive-workspace">
    <header className="m2-heading"><div><p className="eyebrow">M3 Lane Survey</p><h2>My catchment zones</h2></div><button className="icon-button quiet" title="Refresh assignments" onClick={refresh}><RefreshCw size={18} /></button></header>
    {error ? <div className="inline-error"><AlertCircle size={18} />{error}</div> : null}
    {lastSubmission ? <div className="success-banner"><CheckCircle2 size={19} /><span><strong>Lane observation saved</strong><small>{lastSubmission.location_mismatch ? `GPS review flagged · ${lastSubmission.mismatch_distance_m.toFixed(0)} m outside zone` : "Location matches the assigned zone"}</small></span></div> : null}
    {!zones.length ? <div className="empty-panel"><MapPin /><h3>No survey zones assigned</h3><p>The Survey Manager can split an incoming catchment request.</p></div> : null}
    {!selected ? <div className="assignment-list">{zones.map((zone) => <button className="assignment-card" key={zone.id} disabled={zone.status === "completed"} onClick={() => choose(zone)}><span className={`stage-chip ${zone.status}`}>{zone.status.replace("_", " ")}</span><strong>{zone.label}</strong><span>{zone.study_label}</span><small>{zone.submission_count} submitted lanes{localStorage.getItem(draftKey(zone.id)) ? " · local draft available" : ""}</small><b>{zone.status === "completed" ? "Completed" : "Open zone"}</b></button>)}</div> : null}
    {selected ? <form className="property-form lane-form" onSubmit={save}><div className="form-title"><div><p className="eyebrow">{selected.study_label}</p><h2>{selected.label}</h2><p>Drafts save automatically on this device.</p></div><button type="button" className="secondary-button" onClick={() => setSelectedId("")}>Back</button></div><section className="form-section"><div className="section-heading"><h3>Observation location</h3><button type="button" className="secondary-button compact" onClick={useGps}><Crosshair size={16} />Use GPS</button></div><CatchmentMap shapes={[{ geometry: selected.geometry, color: "#782B90", label: selected.label }]} point={point} onPointChange={(latitude, longitude) => setPoint({ latitude, longitude })} /><div className="form-grid"><label>Lane or street<input required minLength={2} value={form.lane_name} onChange={(event) => setForm({ ...form, lane_name: event.target.value })} /></label><label>GPS accuracy (m)<input required type="number" min={1} max={5000} value={form.gps_accuracy_m} onChange={(event) => setForm({ ...form, gps_accuracy_m: event.target.value })} /></label><label>Observed at<input required type="datetime-local" value={form.observed_at} onChange={(event) => setForm({ ...form, observed_at: event.target.value })} /></label></div></section><section className="form-section"><h3>Lane observations</h3><div className="form-grid"><label>Residential units<input required type="number" min={0} max={10000} value={form.residential_units} onChange={(event) => setForm({ ...form, residential_units: event.target.value })} /></label><label>Commercial units<input required type="number" min={0} max={5000} value={form.commercial_units} onChange={(event) => setForm({ ...form, commercial_units: event.target.value })} /></label><label>Pedestrian activity (1-5)<input required type="number" min={1} max={5} value={form.pedestrian_activity} onChange={(event) => setForm({ ...form, pedestrian_activity: event.target.value })} /></label><label>Vehicle activity (1-5)<input required type="number" min={1} max={5} value={form.vehicle_activity} onChange={(event) => setForm({ ...form, vehicle_activity: event.target.value })} /></label></div><label>Notes<textarea maxLength={3000} value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></label></section><div className="lane-actions"><button className="primary-button" disabled={saving}>{saving ? <LoaderCircle className="spin" size={18} /> : <Save size={18} />}Submit lane</button><button type="button" className="secondary-button" disabled={!selected.submission_count} onClick={complete}>Complete zone</button></div></form> : null}
  </section>;
}

function geometryCenter(coordinates: unknown): { latitude: number; longitude: number } {
  const points: number[][] = [];
  const visit = (value: unknown) => {
    if (Array.isArray(value) && value.length >= 2 && typeof value[0] === "number" && typeof value[1] === "number") points.push(value as number[]);
    else if (Array.isArray(value)) value.forEach(visit);
  };
  visit(coordinates);
  const total = points.reduce((sum, point) => ({ latitude: sum.latitude + point[1], longitude: sum.longitude + point[0] }), { latitude: 0, longitude: 0 });
  return points.length ? { latitude: total.latitude / points.length, longitude: total.longitude / points.length } : { latitude: 12.98, longitude: 80.22 };
}
