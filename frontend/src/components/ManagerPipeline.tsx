import { AlertCircle, Building2, ChevronRight, Flag, LoaderCircle, MapPin, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { PropertyPinMap } from "./PropertyPinMap";
import { changeStage, listProperties, loadPhoto, type PipelineStage, type PropertyPhoto, type PropertyRecord } from "../services/m2";

const transitions: Record<PipelineStage, PipelineStage[]> = {
  scouted: ["shortlisted", "rejected"], shortlisted: ["survey_requested", "under_review", "rejected"],
  survey_requested: ["under_review", "rejected"], under_review: ["approved", "rejected", "shortlisted"],
  approved: [], rejected: ["shortlisted"]
};

export function ManagerPipeline() {
  const [properties, setProperties] = useState<PropertyRecord[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const selected = useMemo(() => properties.find((item) => item.id === selectedId) ?? properties[0], [properties, selectedId]);
  async function refresh() {
    setLoading(true);
    try { const items = await listProperties(); setProperties(items); setError(""); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load properties"); }
    finally { setLoading(false); }
  }
  useEffect(() => { void refresh(); }, []);
  async function advance(stage: PipelineStage) {
    if (!selected) return;
    const reason = window.prompt(`Reason for moving to ${stage.replaceAll("_", " ")}:`);
    if (!reason) return;
    try {
      const updated = await changeStage(selected.id, stage, reason);
      setProperties((items) => items.map((item) => item.id === updated.id ? updated : item)); setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Stage change failed"); }
  }
  return <section className="m2-workspace manager-pipeline">
    <header className="m2-heading"><div><p className="eyebrow">M2 Manager Pipeline</p><h2>Scouted properties</h2></div><button className="icon-button quiet" title="Refresh properties" onClick={refresh}><RefreshCw size={18} /></button></header>
    {error ? <div className="inline-error"><AlertCircle size={18} />{error}</div> : null}
    {loading ? <div className="state-panel"><LoaderCircle className="spin" /> Loading properties</div> : null}
    {!loading && !properties.length ? <div className="empty-panel"><Building2 /><h3>No properties captured</h3><p>Assign a hotspot above, then switch to BD Executive to submit a property.</p></div> : null}
    {properties.length ? <div className="pipeline-layout"><div className="property-list">{properties.map((item) => { const evaluation = item.evaluations.at(-1); return <button key={item.id} className={item.id === selected?.id ? "property-list-item active" : "property-list-item"} onClick={() => setSelectedId(item.id)}><span><strong>{item.address}</strong><small>{item.area_name} · {item.assignee_name}</small></span><span><b>{evaluation?.score.toFixed(1) ?? "–"}</b><small className={`stage-chip ${item.stage}`}>{item.stage.replaceAll("_", " ")}</small></span><ChevronRight size={18} /></button>; })}</div>{selected ? <PropertyReview property={selected} onStage={advance} /> : null}</div> : null}
  </section>;
}

function PropertyReview({ property, onStage }: { property: PropertyRecord; onStage: (stage: PipelineStage) => void }) {
  const evaluation = property.evaluations.at(-1);
  return <article className="property-review"><header className="property-review-header"><div><p className="eyebrow">{property.area_name} · {property.target_label}</p><h2>{property.address}</h2><p>{property.size_sq_ft.toLocaleString()} sq ft · ₹{property.rent_monthly.toLocaleString("en-IN")}/month · {property.assignee_name}</p></div><div className="property-score"><strong>{evaluation?.score.toFixed(1) ?? "–"}</strong><span>{evaluation?.rating}</span><small>v{evaluation?.version} · {evaluation?.scoring_version}</small></div></header>
    {property.review_flags.length ? <div className="review-flags"><Flag size={18} /><div><strong>Manager review flags</strong>{property.review_flags.map((flag) => <p key={flag}>{flag}</p>)}</div></div> : null}
    <div className="review-grid"><div><PropertyPinMap latitude={property.latitude} longitude={property.longitude} onChange={() => undefined} editable={false} /><small><MapPin size={13} /> {property.latitude.toFixed(6)}, {property.longitude.toFixed(6)}</small></div><div className="property-facts"><span><small>Frontage</small><b>{property.frontage_ft ? `${property.frontage_ft} ft` : "Missing"}</b></span><span><small>Road width</small><b>{property.road_width_ft ? `${property.road_width_ft} ft` : "Missing"}</b></span><span><small>Visibility</small><b>{property.visibility_rating}/5</b></span><span><small>Condition</small><b>{property.condition_rating}/5</b></span><span><small>Parking</small><b>{property.parking_available ? "Yes" : "No"}</b></span><span><small>Utilities</small><b>{property.power_backup && property.water_available ? "Power + water" : property.power_backup ? "Power" : property.water_available ? "Water" : "Missing"}</b></span></div></div>
    {property.photos.length ? <PhotoGallery photos={property.photos} /> : <p className="muted">No property photos were supplied.</p>}
    {evaluation ? <><div className="decision-summary"><div><h3>Recommendation</h3><p>{evaluation.recommendation}</p></div><div><h3>Top reasons</h3>{evaluation.insights.map((item) => <p key={item}>{item}</p>)}</div><div><h3>Risks</h3>{evaluation.risks.length ? evaluation.risks.map((item) => <p key={item}>{item}</p>) : <p>No automatic risk threshold was triggered.</p>}</div></div><details className="evaluation-ledger"><summary>Why this property score?</summary><div className="metric-table"><div className="metric-row metric-head"><span>Metric</span><span>Raw</span><span>Weight</span><span>Points</span></div>{evaluation.metrics.map((metric) => <details className="metric-row" key={metric.key}><summary><span><b>{metric.label}</b><em>{metric.evidence_kind}</em></span><span>{metric.raw_value === null ? "Missing" : `${metric.raw_value.toFixed(2)} ${metric.raw_unit}`}</span><span>{Math.round(metric.weight * 100)}%</span><strong>{metric.contribution.toFixed(2)}</strong></summary><div className="metric-detail"><p><b>Source:</b> {metric.source} · {new Date(metric.fetched_at).toLocaleString()}</p><p><b>Rule:</b> {metric.transformation}</p><p><b>Limitations:</b> {metric.limitations}</p></div></details>)}</div><div className="limitations"><strong>Limitations</strong>{evaluation.limitations.map((item) => <p key={item}>{item}</p>)}</div></details></> : null}
    <section className="pipeline-actions"><div><p className="eyebrow">Current stage</p><strong className={`stage-chip ${property.stage}`}>{property.stage.replaceAll("_", " ")}</strong></div><div>{transitions[property.stage].map((stage) => <button key={stage} className={stage === "rejected" ? "secondary-button danger" : "primary-button"} onClick={() => onStage(stage)}>{stage.replaceAll("_", " ")}</button>)}</div></section>
    <details className="history"><summary>Stage history ({property.transitions.length})</summary>{[...property.transitions].reverse().map((item) => <div key={item.id}><b>{item.to_stage.replaceAll("_", " ")}</b><span>{item.actor_name} · {new Date(item.created_at).toLocaleString()}</span><p>{item.reason}</p></div>)}</details>
  </article>;
}

function PhotoGallery({ photos }: { photos: PropertyPhoto[] }) {
  const [urls, setUrls] = useState<Record<string, string>>({});
  useEffect(() => {
    let active = true;
    const created: string[] = [];
    Promise.all(photos.map(async (photo) => {
      const url = await loadPhoto(photo.url); created.push(url); return [photo.id, url] as const;
    })).then((items) => { if (active) setUrls(Object.fromEntries(items)); }).catch(() => undefined);
    return () => { active = false; created.forEach(URL.revokeObjectURL); };
  }, [photos]);
  return <div className="photo-gallery">{photos.map((photo) => urls[photo.id] ? <img key={photo.id} src={urls[photo.id]} alt={photo.filename} /> : <div key={photo.id} className="photo-loading"><LoaderCircle className="spin" /></div>)}</div>;
}
