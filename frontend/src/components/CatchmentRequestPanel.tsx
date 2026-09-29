import { AlertCircle, ClipboardPlus, LoaderCircle, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listReports, type ReportSummary } from "../services/m1";
import { listProperties, type PropertyRecord } from "../services/m2";
import { createCatchmentStudy, listCatchmentStudies, type CatchmentStudy } from "../services/m3";

export function CatchmentRequestPanel() {
  const [properties, setProperties] = useState<PropertyRecord[]>([]);
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [studies, setStudies] = useState<CatchmentStudy[]>([]);
  const [target, setTarget] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    setLoading(true);
    try {
      const [propertyItems, reportItems, studyItems] = await Promise.all([
        listProperties(), listReports(), listCatchmentStudies()
      ]);
      setProperties(propertyItems); setReports(reportItems); setStudies(studyItems); setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load catchment requests"); }
    finally { setLoading(false); }
  }
  useEffect(() => { void refresh(); }, []);

  async function requestStudy() {
    if (!target) return;
    const [targetType, targetId] = target.split(":");
    setSaving(true);
    try {
      const created = await createCatchmentStudy(targetType as "property" | "area_report", targetId);
      setStudies((items) => [created, ...items]); setTarget(""); setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not request study"); }
    finally { setSaving(false); }
  }

  return <section className="m3-workspace catchment-request-panel">
    <header className="m2-heading"><div><p className="eyebrow">M3 Catchment Request</p><h2>Request field evidence</h2></div><button className="icon-button quiet" title="Refresh studies" onClick={refresh}><RefreshCw size={18} /></button></header>
    {error ? <div className="inline-error"><AlertCircle size={18} />{error}</div> : null}
    <div className="request-row"><select aria-label="Catchment target" value={target} onChange={(event) => setTarget(event.target.value)}><option value="">Choose a property or area report</option><optgroup label="Properties">{properties.map((item) => <option key={item.id} value={`property:${item.id}`}>{item.address} · {item.area_name}</option>)}</optgroup><optgroup label="Area reports">{reports.map((item) => <option key={item.id} value={`area_report:${item.id}`}>{item.area_name} · {item.score.toFixed(1)}</option>)}</optgroup></select><button className="primary-button" disabled={!target || saving} onClick={requestStudy}>{saving ? <LoaderCircle className="spin" size={17} /> : <ClipboardPlus size={17} />}Request study</button></div>
    {loading ? <div className="state-panel"><LoaderCircle className="spin" /> Loading studies</div> : <div className="study-summary-list">{studies.map((study) => { const sourceCount = study.source_study_ids?.length ?? (study.source_study_id ? 1 : 0); return <Link to={`/manager/catchments/${study.id}`} key={study.id}><span className={`stage-chip ${study.status}`}>{study.status}</span><strong>{study.target_label}</strong><small>{study.progress_percent.toFixed(0)}% complete · {study.reuse_coverage.toFixed(0)}% reused</small>{sourceCount ? <small>{sourceCount} source study{sourceCount === 1 ? "" : "ies"} · latest {study.reuse_age_days?.toFixed(1)} days old</small> : null}</Link>; })}</div>}
  </section>;
}
