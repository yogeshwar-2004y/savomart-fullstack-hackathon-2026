import { AlertCircle, Building2, ChevronRight, Flag, LoaderCircle, MapPin, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { PropertyPinMap } from "./PropertyPinMap";
import { changeStage, listProperties, loadPhoto, type PipelineStage, type PropertyPhoto, type PropertyRecord } from "../services/m2";

const transitions: Record<PipelineStage, PipelineStage[]> = {
  scouted: ["shortlisted", "rejected"], shortlisted: ["survey_requested", "under_review", "rejected"],
  survey_requested: ["under_review", "rejected"], under_review: ["approved", "rejected", "shortlisted"],
  approved: [], rejected: ["shortlisted"]
};

export function ManagerPipeline({ view = "pipeline" }: { view?: "pipeline" | "decisions" }) {
  const { propertyId } = useParams();
  const [properties, setProperties] = useState<PropertyRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pendingStage, setPendingStage] = useState<PipelineStage | null>(null);
  const [stageReason, setStageReason] = useState("");
  const selected = useMemo(() => properties.find((item) => item.id === propertyId), [properties, propertyId]);
  async function refresh() {
    setLoading(true);
    try { const items = await listProperties(); setProperties(items); setError(""); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load properties"); }
    finally { setLoading(false); }
  }
  useEffect(() => { void refresh(); }, []);
  async function advance() {
    if (!selected || !pendingStage || !stageReason.trim()) return;
    try {
      const updated = await changeStage(selected.id, pendingStage, stageReason.trim());
      setProperties((items) => items.map((item) => item.id === updated.id ? updated : item));
      setPendingStage(null); setStageReason(""); setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Stage change failed"); }
  }
  return <section className="m2-workspace manager-pipeline">
    <header className="m2-heading"><div><p className="eyebrow">M2 Manager Pipeline</p><h2>{view === "decisions" ? "Decisions and history" : selected ? "Property review" : "Property pipeline"}</h2></div><button className="icon-button quiet" title="Refresh properties" onClick={refresh}><RefreshCw size={18} /></button></header>
    {error ? <div className="inline-error"><AlertCircle size={18} />{error}</div> : null}
    {loading ? <div className="state-panel"><LoaderCircle className="spin" /> Loading properties</div> : null}
    {!loading && !properties.length ? <div className="empty-panel"><Building2 /><h3>No properties captured</h3><p>Assign a hotspot above, then switch to BD Executive to submit a property.</p></div> : null}
    {propertyId ? <Link className="secondary-button pipeline-back" to="/manager/properties">Back to pipeline</Link> : null}
    {properties.length && !propertyId ? <div className="pipeline-card-grid">{properties.filter((item) => view !== "decisions" || item.transitions.length > 1).map((item) => { const evaluation = item.evaluations.at(-1); const drivers = [...(evaluation?.metrics ?? [])].sort((a, b) => b.contribution - a.contribution).slice(0, 2); const next = transitions[item.stage][0]; return <Link key={item.id} className="pipeline-card" to={`/manager/properties/${item.id}`}><div><span className={`stage-chip ${item.stage}`}>{item.stage.replaceAll("_", " ")}</span><strong className="pipeline-card-score">{evaluation?.score.toFixed(1) ?? "–"}</strong></div><h3>{item.address}</h3><p>{item.area_name} · {item.assignee_name}</p><small>GPS {item.latitude.toFixed(5)}, {item.longitude.toFixed(5)}</small><div className="pipeline-card-evidence"><strong>Leading drivers</strong>{drivers.map((metric) => <span key={metric.key}>{metric.label} +{metric.contribution.toFixed(1)} · {metric.evidence_kind}</span>)}<strong>Risk</strong><span>{evaluation?.risks[0] ?? "No automatic risk threshold triggered"}</span></div><footer><small>Updated {new Date(item.transitions.at(-1)?.created_at ?? item.created_at).toLocaleString()}</small><span>{next ? `Next: ${next.replaceAll("_", " ")}` : "Review history"} <ChevronRight size={16} /></span></footer></Link>; })}</div> : null}
    {selected ? <PropertyReview key={selected.id} property={selected} onStage={setPendingStage} /> : null}
    {pendingStage ? <div className="modal-backdrop" role="presentation" onMouseDown={() => setPendingStage(null)}><section className="decision-dialog" role="dialog" aria-modal="true" aria-labelledby="decision-title" onMouseDown={(event) => event.stopPropagation()}><p className="eyebrow">Decision history</p><h2 id="decision-title">Move to {pendingStage.replaceAll("_", " ")}</h2><p>Record a concise reason. It will remain visible in the property history.</p><label htmlFor="stage-reason">Reason</label><textarea id="stage-reason" autoFocus value={stageReason} onChange={(event) => setStageReason(event.target.value)} rows={4} placeholder="Why is this the next decision?" /><div className="dialog-actions"><button className="secondary-button" type="button" onClick={() => { setPendingStage(null); setStageReason(""); }}>Cancel</button><button className="primary-button" type="button" disabled={!stageReason.trim()} onClick={() => void advance()}>Confirm stage</button></div></section></div> : null}
  </section>;
}

function PropertyReview({ property, onStage }: { property: PropertyRecord; onStage: (stage: PipelineStage) => void }) {
  const latest = property.evaluations.at(-1);
  const [selectedVersion, setSelectedVersion] = useState(latest?.version ?? 1);
  const evaluation = property.evaluations.find((item) => item.version === selectedVersion) ?? latest;
  const catchmentMetric = evaluation?.metrics.find((metric) => metric.key === "catchment_observations");
  return <article className="property-review"><header className="property-review-header"><div><p className="eyebrow">{property.area_name} · {property.target_label}</p><h2>{property.address}</h2><p>{property.size_sq_ft.toLocaleString()} sq ft · ₹{property.rent_monthly.toLocaleString("en-IN")}/month · {property.assignee_name}</p></div><div className="property-score"><strong>{evaluation?.score.toFixed(1) ?? "–"}</strong><span>{evaluation?.rating}</span><small>v{evaluation?.version} · {evaluation?.scoring_version}</small></div></header>
    {property.review_flags.length ? <div className="review-flags"><Flag size={18} /><div><strong>Manager review flags</strong>{property.review_flags.map((flag) => <p key={flag}>{flag}</p>)}</div></div> : null}
    <div className="review-grid"><div><PropertyPinMap latitude={property.latitude} longitude={property.longitude} onChange={() => undefined} editable={false} /><small><MapPin size={13} /> {property.latitude.toFixed(6)}, {property.longitude.toFixed(6)}</small></div><div className="property-facts"><span><small>Frontage</small><b>{property.frontage_ft ? `${property.frontage_ft} ft` : "Missing"}</b></span><span><small>Road width</small><b>{property.road_width_ft ? `${property.road_width_ft} ft` : "Missing"}</b></span><span><small>Visibility</small><b>{property.visibility_rating}/5</b></span><span><small>Condition</small><b>{property.condition_rating}/5</b></span><span><small>Parking</small><b>{property.parking_available ? "Yes" : "No"}</b></span><span><small>Utilities</small><b>{property.power_backup && property.water_available ? "Power + water" : property.power_backup ? "Power" : property.water_available ? "Water" : "Missing"}</b></span></div></div>
    {property.photos.length ? <PhotoGallery photos={property.photos} /> : <p className="muted">No property photos were supplied.</p>}
    {property.evaluations.length ? <section className="evaluation-history" aria-label="Evaluation history"><div><p className="eyebrow">Evaluation history</p><h3>Score versions</h3></div><div>{property.evaluations.map((item) => <button type="button" className={item.version === evaluation?.version ? "active" : ""} key={item.id} onClick={() => setSelectedVersion(item.version)}><span><strong>v{item.version}</strong>{item.version === latest?.version ? <em>Latest</em> : null}</span><b>{item.score.toFixed(1)}</b><small>{item.scoring_version}</small><small>{new Date(item.created_at).toLocaleString()}</small></button>)}</div></section> : null}
    {catchmentMetric ? <section className="catchment-evidence"><div><p className="eyebrow">Linked catchment insights</p><h3>Evaluation v{evaluation?.version}</h3></div><strong>{catchmentMetric.raw_value?.toFixed(0) ?? "0"} lane observations · {catchmentMetric.contribution.toFixed(2)} points</strong><p>{catchmentMetric.source} · {new Date(catchmentMetric.fetched_at).toLocaleString()}</p><small>{catchmentMetric.evidence_kind} evidence · {catchmentMetric.limitations}</small></section> : null}
    {evaluation ? <><div className="decision-summary"><div><h3>Recommendation</h3><p>{evaluation.recommendation}</p></div><div><h3>Top reasons</h3>{evaluation.insights.map((item) => <p key={item}>{item}</p>)}</div><div><h3>Risks</h3>{evaluation.risks.length ? evaluation.risks.map((item) => <p key={item}>{item}</p>) : <p>No automatic risk threshold was triggered.</p>}</div></div><details className="evaluation-ledger"><summary>Why this property score?</summary><div className="metric-table"><div className="metric-row metric-head"><span>Metric</span><span>Raw</span><span>Weight</span><span>Points</span></div>{evaluation.metrics.map((metric, index) => <details className="metric-row" key={`${metric.key}-${index}`}><summary><span><b>{metric.label}</b><em>{metric.evidence_kind}</em></span><span>{metric.raw_value === null ? "Missing" : `${metric.raw_value.toFixed(2)} ${metric.raw_unit}`}</span><span>{Math.round(metric.weight * 100)}%</span><strong>{metric.contribution.toFixed(2)}</strong></summary><div className="metric-detail"><p><b>Source:</b> {metric.source} · {new Date(metric.fetched_at).toLocaleString()}</p><p><b>Rule:</b> {metric.transformation}</p><p><b>Limitations:</b> {metric.limitations}</p></div></details>)}</div><div className="limitations"><strong>Limitations</strong>{evaluation.limitations.map((item) => <p key={item}>{item}</p>)}</div></details></> : null}
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
