import { AlertCircle, ArrowLeft, Building2, LoaderCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getProperty, listAssignments, type Assignment, type PropertyRecord } from "../services/m2";
import { PropertyPinMap } from "./PropertyPinMap";

export function SubmittedProperties() {
  const { propertyId } = useParams();
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [property, setProperty] = useState<PropertyRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    setLoading(true);
    Promise.all([listAssignments(), propertyId ? getProperty(propertyId) : Promise.resolve(null)])
      .then(([items, detail]) => { setAssignments(items); setProperty(detail); setError(""); })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Could not load submitted properties"))
      .finally(() => setLoading(false));
  }, [propertyId]);
  const submitted = assignments.filter((item) => item.property_id);
  const evaluation = property?.evaluations.at(-1);
  return <section className="submitted-page"><header className="page-heading"><div><p className="eyebrow">M2 Field Scouting</p><h1>{property ? "Property evaluation" : "Properties submitted"}</h1><p>Review what you captured and its current manager stage.</p></div>{property ? <Link className="secondary-button" to="/executive/submitted"><ArrowLeft size={17} />All submissions</Link> : <Link className="secondary-button" to="/executive/assignments">My assignments</Link>}</header>
    {loading ? <div className="state-panel"><LoaderCircle className="spin" /> Loading submissions</div> : null}
    {error ? <div className="inline-error" role="alert"><AlertCircle />{error}</div> : null}
    {!loading && !error && !property && !submitted.length ? <div className="empty-panel"><Building2 /><h2>No submitted properties</h2><p>Open a scouting assignment to capture one.</p></div> : null}
    {!property && !loading ? <div className="report-card-grid">{submitted.map((item) => <Link className="report-card" key={item.id} to={`/executive/properties/${item.property_id}`}><p className="eyebrow">{item.area_name}</p><h2>{item.target_label}</h2><p>{item.assignee_name} · submitted</p><span className="report-card-action">Open evaluation</span></Link>)}</div> : null}
    {property ? <article className="executive-property-detail"><header><div><p className="eyebrow">{property.area_name} · {property.target_label}</p><h2>{property.address}</h2><p>{property.size_sq_ft.toLocaleString()} sq ft · ₹{property.rent_monthly.toLocaleString("en-IN")}/month</p></div><div className="property-score"><strong>{evaluation?.score.toFixed(1) ?? "–"}</strong><span>{evaluation?.rating}</span><small>Evaluation v{evaluation?.version}</small></div></header><span className={`stage-chip ${property.stage}`}>{property.stage.replaceAll("_", " ")}</span><div className="submitted-detail-grid"><PropertyPinMap latitude={property.latitude} longitude={property.longitude} editable={false} onChange={() => undefined} /><div><h3>Manager status</h3><p>{property.transitions.at(-1)?.reason ?? "Awaiting manager review"}</p><h3>Leading reasons</h3>{evaluation?.insights.slice(0, 3).map((item) => <p key={item}>{item}</p>)}<h3>Risks</h3>{evaluation?.risks.length ? evaluation.risks.map((item) => <p key={item}>{item}</p>) : <p>No automatic risk threshold was triggered.</p>}</div></div><details className="evaluation-ledger"><summary>Why this score?</summary><div className="metric-table">{evaluation?.metrics.map((metric, index) => <div className="submitted-metric" key={`${metric.key}-${index}`}><strong>{metric.label}</strong><span>{metric.contribution.toFixed(2)} points · {metric.evidence_kind}</span><small>{metric.source} · {metric.limitations}</small></div>)}</div></details></article> : null}
  </section>;
}
