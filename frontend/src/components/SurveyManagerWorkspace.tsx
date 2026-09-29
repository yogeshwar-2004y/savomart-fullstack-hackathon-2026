import { AlertCircle, LoaderCircle, Map, RefreshCw, Users } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { listCatchmentStudies, listSurveyAssignees, planSurveyZones, type CatchmentStudy, type SurveyAssignee } from "../services/m3";
import { CatchmentMap } from "./CatchmentMap";

export function SurveyManagerWorkspace() {
  const [studies, setStudies] = useState<CatchmentStudy[]>([]);
  const [assignees, setAssignees] = useState<SurveyAssignee[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [zoneCount, setZoneCount] = useState(2);
  const [selectedAssignees, setSelectedAssignees] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const selected = useMemo(() => studies.find((item) => item.id === selectedId) ?? studies[0], [studies, selectedId]);

  async function refresh() {
    setLoading(true);
    try {
      const [studyItems, people] = await Promise.all([listCatchmentStudies(), listSurveyAssignees()]);
      setStudies(studyItems); setAssignees(people); setSelectedAssignees((current) => current.length ? current : people.map((item) => item.id)); setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load survey operations"); }
    finally { setLoading(false); }
  }
  useEffect(() => { void refresh(); }, []);

  async function createZones() {
    if (!selected || !selectedAssignees.length) return;
    try {
      const updated = await planSurveyZones(selected.id, zoneCount, selectedAssignees);
      setStudies((items) => items.map((item) => item.id === updated.id ? updated : item)); setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not create zones"); }
  }

  return <section className="m3-workspace survey-manager-workspace">
    <header className="m2-heading"><div><p className="eyebrow">M3 Survey Manager</p><h2>Catchment work planner</h2></div><button className="icon-button quiet" title="Refresh studies" onClick={refresh}><RefreshCw size={18} /></button></header>
    {error ? <div className="inline-error"><AlertCircle size={18} />{error}</div> : null}
    {loading ? <div className="state-panel"><LoaderCircle className="spin" /> Loading requests</div> : null}
    {!loading && !studies.length ? <div className="empty-panel"><Map /><h3>No catchment requests</h3><p>A BD Manager can request one for a saved property or area report.</p></div> : null}
    {selected ? <div className="survey-manager-layout"><aside className="study-list">{studies.map((study) => <button key={study.id} className={study.id === selected.id ? "active" : ""} onClick={() => setSelectedId(study.id)}><span className={`stage-chip ${study.status}`}>{study.status}</span><strong>{study.target_label}</strong><small>{study.progress_percent.toFixed(0)}% · {study.zones.length} zones</small></button>)}</aside><article className="study-detail"><header><div><p className="eyebrow">{selected.target_type.replace("_", " ")}</p><h2>{selected.target_label}</h2></div><strong>{selected.progress_percent.toFixed(0)}%</strong></header><CatchmentMap shapes={[{ geometry: selected.target_geometry, color: "#782B90", label: "Target" }, ...selected.zones.map((zone) => ({ geometry: zone.geometry, color: zone.status === "completed" ? "#16835f" : "#d89b00", label: zone.label }))]} /><div className="reuse-note"><strong>Reuse check</strong><span>{selected.reuse_coverage.toFixed(1)}% coverage · threshold {selected.reuse_min_coverage.toFixed(0)}% · max age {selected.reuse_max_age_days} days</span>{selected.source_study_id ? <small>Source {selected.source_study_id} ({selected.reuse_age_days?.toFixed(1)} days old)</small> : <small>No recent overlapping completed study found.</small>}</div>{selected.status === "requested" ? <section className="zone-planner"><label>Work zones<input type="number" min={1} max={8} value={zoneCount} onChange={(event) => setZoneCount(Number(event.target.value))} /></label><fieldset><legend><Users size={15} /> Assign survey executives</legend>{assignees.map((person) => <label key={person.id}><input type="checkbox" checked={selectedAssignees.includes(person.id)} onChange={(event) => setSelectedAssignees((items) => event.target.checked ? [...items, person.id] : items.filter((id) => id !== person.id))} />{person.name}</label>)}</fieldset><button className="primary-button" disabled={!selectedAssignees.length} onClick={createZones}>Create non-overlapping zones</button></section> : null}<div className="zone-progress-list">{selected.zones.map((zone) => <div key={zone.id}><span className={`stage-chip ${zone.status}`}>{zone.status.replace("_", " ")}</span><strong>{zone.label}</strong><small>{zone.assignee_name} · {zone.submission_count} lane observations</small>{zone.mismatch_review ? <b>GPS review needed</b> : null}</div>)}</div>{selected.summary ? <CatchmentSummary summary={selected.summary} /> : null}</article></div> : null}
  </section>;
}

function CatchmentSummary({ summary }: { summary: Record<string, unknown> }) {
  return <section className="catchment-summary"><h3>Catchment insights</h3><p><strong>{summary.evidence_kind === "demo" ? "Demo/simulated data" : "Real field-survey data"}</strong> · {String(summary.source ?? "Submitted lane observations")}</p><div><span><small>Lane observations</small><b>{String(summary.observation_count ?? 0)}</b></span><span><small>Residential units</small><b>{String(summary.residential_units ?? 0)}</b></span><span><small>Commercial units</small><b>{String(summary.commercial_units ?? 0)}</b></span><span><small>Coverage</small><b>{String(summary.coverage_percent ?? 0)}%</b></span></div><p>{String(summary.limitations ?? "Field observations require manager interpretation.")}</p></section>;
}
