import { AlertCircle, ClipboardCheck, LoaderCircle, UserPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listAssignments, type Assignment } from "../services/m2";

export function ManagerAssignments() {
  const [items, setItems] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    listAssignments().then((result) => { setItems(result); setError(""); })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Assignments unavailable"))
      .finally(() => setLoading(false));
  }, []);
  return <section className="manager-assignments"><header className="page-heading"><div><p className="eyebrow">M2 Scouting Handoff</p><h1>Scouting assignments</h1><p>Track assigned hotspots and the properties that came back from the field.</p></div><Link className="primary-button" to="/manager/reports"><UserPlus size={17} />Assign from a report</Link></header>
    {loading ? <div className="state-panel"><LoaderCircle className="spin" /> Loading assignments</div> : null}
    {error ? <div className="inline-error" role="alert"><AlertCircle />{error}</div> : null}
    {!loading && !error && !items.length ? <div className="empty-panel"><ClipboardCheck /><h2>No scouting assignments</h2><p>Open a saved report and assign one of its hotspots.</p></div> : null}
    <div className="study-card-grid">{items.map((item) => <article className="study-card" key={item.id}><span className={`stage-chip ${item.status}`}>{item.property_id ? "Property submitted" : "Awaiting scout"}</span><h2>{item.target_label}</h2><p>{item.area_name} · {item.assignee_name}</p><small>{item.instructions || "No additional instructions"}</small><small>Assigned {new Date(item.created_at).toLocaleString()}</small>{item.property_id ? <Link className="secondary-button" to={`/manager/properties/${item.property_id}`}>Review property</Link> : <Link className="secondary-button" to={`/manager/reports/${item.area_report_id}`}>Open source report</Link>}</article>)}</div>
  </section>;
}
