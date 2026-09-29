import { AlertCircle, BarChart3, CheckCircle2, Grid2X2, LoaderCircle, MapPin, Maximize2, Minimize2, PanelLeftClose, PanelLeftOpen, Play, RefreshCw, Search, UserPlus } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AreaMap } from "./AreaMap";
import {
  type AreaReport, type AreaSearchResult, type AreaSelection, type Comparison, type Job, type ReportSummary,
  type StoreLocation, compareReports, createApproximateRadius, getGccWard, getJob, getReport, listStores, retryJob, searchAreas, startAnalysis
} from "../services/m1";
import { createAssignment, listAssignees, type Assignee } from "../services/m2";

type Selection = AreaSelection & { limitations?: string | null };

const CELL_SIZE = 0.01;

export function M1Workspace() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("Velachery");
  const [method, setMethod] = useState<"locality" | "pincode" | "ward" | "cells">("locality");
  const [searching, setSearching] = useState(false);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [searchResults, setSearchResults] = useState<AreaSearchResult[]>([]);
  const [cells, setCells] = useState<number[][][][]>([]);
  const [cellMode, setCellMode] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [report, setReport] = useState<AreaReport | null>(null);
  const [stores, setStores] = useState<StoreLocation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [panelCollapsed, setPanelCollapsed] = useState(false);
  const [mapFocused, setMapFocused] = useState(false);

  useEffect(() => { void listStores().then(setStores).catch(() => setStores([])); }, []);

  useEffect(() => {
    if (!job || job.status === "completed" || job.status === "failed") return;
    const timer = window.setInterval(async () => {
      try {
        const next = await getJob(job.id);
        setJob(next);
        if (next.status === "completed" && next.report_id) {
          navigate(`/manager/reports/${next.report_id}`);
        }
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "Could not refresh analysis progress");
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [job]);

  const mapGeometry = report?.geometry ?? selection?.geometry ?? null;

  async function onSearch(event: FormEvent) {
    event.preventDefault();
    if (method === "cells") return;
    setSearching(true); setError(null); setReport(null);
    try {
      if (method === "ward") {
        const wardId = Number(query);
        if (!Number.isInteger(wardId) || wardId < 1 || wardId > 200) throw new Error("Enter a GCC ward ID from 1 to 200");
        setSelection(await getGccWard(wardId)); setSearchResults([]); setCells([]);
        return;
      }
      const found = await searchAreas(query, method);
      setSearchResults(found);
      if (found.length === 1 && found[0].geometry.type !== "Point") selectResult(found[0]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Area search failed");
    } finally { setSearching(false); }
  }

  function selectResult(result: AreaSearchResult) {
    if (result.geometry.type === "Point") return;
    setCells([]); setCellMode(false);
    setSelection({
      name: result.display_name.split(",")[0], query: result.query,
      selection_method: result.selection_method, geometry: result.geometry,
      source: result.source, source_id: result.source_id, source_url: result.source_url,
      source_license: result.source_license, boundary_type: result.boundary_type,
      lookup_at: result.lookup_at, is_official: result.is_official,
      is_approximate: false, resolver_cache_age_seconds: result.cache_age_seconds,
      limitations: result.limitations
    });
  }

  async function selectRadius(result: AreaSearchResult, radius: number) {
    setSearching(true); setError(null);
    try {
      const area = await createApproximateRadius(result, radius);
      setSelection({ ...area, limitations: area.approximation_warning });
      setSearchResults([]); setCells([]); setCellMode(false);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not create approximate area"); }
    finally { setSearching(false); }
  }

  function addCell(lat: number, lon: number) {
    const west = Math.floor(lon / CELL_SIZE) * CELL_SIZE;
    const south = Math.floor(lat / CELL_SIZE) * CELL_SIZE;
    const ring = [[west, south], [west + CELL_SIZE, south], [west + CELL_SIZE, south + CELL_SIZE], [west, south + CELL_SIZE], [west, south]];
    const key = `${west.toFixed(4)}:${south.toFixed(4)}`;
    const exists = cells.some((polygon) => `${polygon[0][0][0].toFixed(4)}:${polygon[0][0][1].toFixed(4)}` === key);
    const next = exists ? cells.filter((polygon) => `${polygon[0][0][0].toFixed(4)}:${polygon[0][0][1].toFixed(4)}` !== key) : [...cells, [ring]];
    setCells(next);
    if (next.length) setSelection({
      name: `Selected Chennai cells (${next.length})`, selection_method: "cells",
      geometry: { type: "MultiPolygon", coordinates: next }, source: "User-selected map cells",
      source_id: "user-cells:pending-server-hash", source_license: null, source_url: null,
      boundary_type: "user-selected", lookup_at: new Date().toISOString(), is_official: false,
      is_approximate: false, limitations: "User-defined geographic squares; not an official administrative boundary."
    });
    else setSelection(null);
  }

  async function analyze() {
    if (!selection || (method === "cells" ? selection.selection_method !== "cells" : method === "ward" ? selection.selection_method !== "ward" : ![method, "radius"].includes(selection.selection_method))) return;
    setError(null); setReport(null);
    try {
      const accepted = await startAnalysis(selection);
      const next = await getJob(accepted.job_id);
      setJob(next);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not start analysis"); }
  }

  async function retry() {
    if (!job) return;
    try { await retryJob(job.id); setJob(await getJob(job.id)); setError(null); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Retry failed"); }
  }

  function changeMode(next: typeof method) {
    setMethod(next); setQuery(next === "pincode" ? "600042" : next === "ward" ? "" : "Velachery");
    setSelection(null); setSearchResults([]); setCells([]); setCellMode(next === "cells"); setError(null); setJob(null);
  }

  return (
    <section className={`m1-layout ${panelCollapsed ? "panel-collapsed" : ""} ${mapFocused ? "map-focused" : ""}`}>
      <aside className="control-panel" aria-hidden={mapFocused || panelCollapsed}>
        <div className="section-heading"><div><p className="eyebrow">M1 Area Intelligence</p><h2>Choose a Chennai area</h2></div><MapPin size={24} /></div>
        <form className="search-form" onSubmit={onSearch}>
          <div className="segmented selection-modes" aria-label="Area selection mode">
            {(["locality", "pincode", "ward", "cells"] as const).map((mode) => <button type="button" key={mode} className={method === mode ? "active" : ""} onClick={() => changeMode(mode)} aria-pressed={method === mode}>{mode === "ward" ? "GCC ward" : mode === "cells" ? "Map grid" : mode === "pincode" ? "Pincode" : "Locality"}</button>)}
          </div>
          {method !== "cells" ? <div className="search-row"><input value={query} onChange={(event) => setQuery(event.target.value)} aria-label={method === "ward" ? "GCC ward ID" : "Chennai locality or pincode"} placeholder={method === "locality" ? "Velachery" : method === "pincode" ? "600042" : "Ward ID, 1–200"} /><button className="icon-button" title="Search" aria-label="Search area" disabled={searching}><Search size={18} /></button></div> : <p className="mode-note">Tap map cells to add or remove them. Each cell spans 0.01° latitude × 0.01° longitude and is not equal-area.</p>}
        </form>
        {searchResults.length ? <div className="search-results">{searchResults.map((result) => <div key={result.source_id} className="search-result"><button type="button" onClick={() => selectResult(result)} disabled={result.geometry.type === "Point"}><strong>{result.display_name.split(",")[0]}</strong><span>{result.boundary_type} · {result.source}</span></button>{result.geometry.type === "Point" ? <div className="radius-actions"><small>Point only. Use an approximate radius:</small>{[1000, 2000, 3000].map((radius) => <button type="button" key={radius} onClick={() => selectRadius(result, radius)}>{radius / 1000} km</button>)}</div> : null}</div>)}</div> : null}
        {method === "cells" ? <button className={cellMode ? "cell-toggle active" : "cell-toggle"} type="button" onClick={() => setCellMode(!cellMode)}><Grid2X2 size={18} />{cellMode ? "Pause cell selection" : "Resume cell selection"}</button> : null}
        {selection ? <div className="selection-summary"><strong>{selection.name}</strong><span>{selection.boundary_type} · {selection.source}</span><small>Source ID: {selection.source_id}</small>{selection.limitations ? <small>{selection.limitations}</small> : null}</div> : <p className="muted">Search for a boundary or choose map cells.</p>}
        <EvidenceLegend />
        <button className="primary-button" type="button" disabled={!selection || (!!job && !["failed", "completed"].includes(job.status))} onClick={analyze}><Play size={18} />Start analysis</button>
        {job ? <JobProgress job={job} onRetry={retry} /> : null}
        {error ? <div className="inline-error"><AlertCircle size={18} />{error}</div> : null}
        <Link className="secondary-button" to="/manager/reports">View saved reports</Link>
      </aside>

      <div className="map-report-panel">
        <div className="map-workspace">
          <div className="map-toolbar" aria-label="Map view controls">
            <button className="map-tool-button" type="button" onClick={() => setPanelCollapsed((value) => !value)} title={panelCollapsed ? "Show area controls" : "Hide area controls"}>{panelCollapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}<span>{panelCollapsed ? "Show panel" : "Focus map"}</span></button>
            <button className="map-tool-button" type="button" onClick={() => setMapFocused((value) => !value)} title={mapFocused ? "Exit full-screen map" : "Full-screen map"}>{mapFocused ? <Minimize2 size={18} /> : <Maximize2 size={18} />}<span>{mapFocused ? "Exit" : "Full screen"}</span></button>
          </div>
          <AreaMap geometry={mapGeometry} suggestions={report?.suggestions ?? []} stores={stores} cellMode={cellMode} onCellClick={addCell} />
          <div className="map-overlay-legend" aria-label="Map overlay legend"><strong>Map layers</strong><span><i className="overlay-area" />Selected area</span><span><i className="overlay-hotspot" />Scouting hotspot</span><span><i className="overlay-store">S</i>SAVOmart store</span></div>
        </div>
        <div className="map-caption"><strong>Real Chennai geography</strong><span>OpenStreetMap tiles and boundaries · {stores.length} operational SAVOmart snapshot pins.</span></div>
      </div>
    </section>
  );
}

function JobProgress({ job, onRetry }: { job: Job; onRetry: () => void }) {
  const steps: Job["status"][] = ["queued", "fetching", "scoring", "completed"];
  const active = job.status === "failed" ? -1 : steps.indexOf(job.status);
  return <div className={`job-progress ${job.status}`}><div className="job-header">{job.status === "failed" ? <AlertCircle size={18} /> : job.status === "completed" ? <CheckCircle2 size={18} /> : <LoaderCircle className="spin" size={18} />}<strong>{job.status}</strong><span>{job.progress}%</span></div><div className="progress-track"><i style={{ width: `${job.progress}%` }} /></div><div className="job-steps">{steps.map((step, index) => <span className={index <= active ? "done" : ""} key={step}>{step}</span>)}</div><small>{job.status_detail}</small>{job.status === "failed" && job.retryable ? <button className="secondary-button" onClick={onRetry}><RefreshCw size={16} />Retry ({job.attempts}/3)</button> : null}</div>;
}

export function ReportView({ report, compareOptions, compareId, setCompareId, compare, comparison }: { report: AreaReport; compareOptions: ReportSummary[]; compareId: string; setCompareId: (id: string) => void; compare: () => void; comparison: Comparison | null }) {
  return <article className="report-view"><header className="report-header"><div><p className="eyebrow">Saved {new Date(report.created_at).toLocaleString()}</p><h2>{report.title}</h2><p>{report.summary}</p></div><div className="score-block"><strong>{report.score.toFixed(1)}</strong><span>/ 100</span><b>{report.rating}</b></div></header>{report.used_cached_evidence ? <div className="cache-note"><AlertCircle size={17} />Cached evidence used after an upstream failure. Age: {formatAge(report.cache_age_seconds)}.</div> : null}<div className="boundary-evidence"><span className="legend-dot geography" /><div><strong>{report.boundary_type} boundary</strong><p>{report.source} · fetched {new Date(report.boundary_lookup_at).toLocaleString()}</p><small>{report.source_id}{report.resolver_cache_age_seconds ? ` · cache age ${formatAge(report.resolver_cache_age_seconds)}` : ""}</small>{report.approximation_warning ? <em>{report.approximation_warning}</em> : null}</div></div><EvidenceLegend /><div className="report-meta"><span>{report.area_sq_km.toFixed(2)} km²</span><span>{report.selection_method}</span><span>{report.scoring_version}</span></div><section className="why-score"><div className="section-heading"><div><p className="eyebrow">Evidence ledger</p><h3>Why this score?</h3></div><BarChart3 size={22} /></div><div className="metric-table"><div className="metric-row metric-head"><span>Signal</span><span>Raw</span><span>Weight</span><span>Points</span></div>{report.metrics.map((metric) => <details className="metric-row" key={metric.key}><summary><span><b>{metric.label}</b><em>{metric.category} · {metricLabel(metric.evidence_kind, metric.category)}</em></span><span>{metric.raw_value === null ? "Unavailable" : `${metric.raw_value.toFixed(2)} ${metric.raw_unit}`}</span><span>{Math.round(metric.weight * 100)}%</span><strong>{metric.contribution.toFixed(2)}</strong></summary><div className="metric-detail"><p><b>Source:</b> {metric.source_name} · {new Date(metric.fetched_at).toLocaleString()}</p><p><b>Normalization:</b> {metric.transformation}</p><p><b>Geography:</b> {metric.geography}</p><p><b>Limitations:</b> {metric.limitations}</p>{metric.cache_age_seconds ? <p><b>Cache age:</b> {formatAge(metric.cache_age_seconds)}</p> : null}</div></details>)}</div></section><section className="suggestions"><h3>Places to scout</h3>{report.suggestions.map((item) => <div key={item.id}><b>{item.rank}</b><span><strong>{item.label}</strong><small>{item.rationale}</small></span><AssignmentControl reportId={report.id} suggestionId={item.id} /></div>)}</section><section className="comparison-controls"><h3>Compare saved reports</h3><div><select value={compareId} onChange={(event) => setCompareId(event.target.value)}><option value="">Choose another report</option>{compareOptions.map((item) => <option value={item.id} key={item.id}>{item.area_name} · {item.score.toFixed(1)}</option>)}</select><button className="secondary-button" disabled={!compareId} onClick={compare}>Compare</button></div>{comparison ? <div className="comparison-result"><span>{comparison.left.area_name}<b>{comparison.left.score.toFixed(1)}</b></span><i>vs</i><span>{comparison.right.area_name}<b>{comparison.right.score.toFixed(1)}</b></span><strong>{comparison.score_delta > 0 ? "+" : ""}{comparison.score_delta.toFixed(1)} points</strong></div> : null}</section></article>;
}

function AssignmentControl({ reportId, suggestionId }: { reportId: string; suggestionId: string }) {
  const [open, setOpen] = useState(false);
  const [people, setPeople] = useState<Assignee[]>([]);
  const [assigneeId, setAssigneeId] = useState("bd-executive-1");
  const [instructions, setInstructions] = useState("");
  const [message, setMessage] = useState("");
  async function show() {
    setOpen(true); setMessage("");
    try { setPeople(await listAssignees()); } catch (reason) { setMessage(reason instanceof Error ? reason.message : "Could not load executives"); }
  }
  async function assign() {
    try {
      const saved = await createAssignment({ area_report_id: reportId, suggestion_id: suggestionId, assignee_id: assigneeId, instructions });
      setMessage(`Assigned to ${saved.assignee_name}`); setOpen(false);
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : "Assignment failed"); }
  }
  if (!open) return <span className="assignment-action"><button className="secondary-button compact" type="button" onClick={show}><UserPlus size={16} />Assign</button>{message ? <small>{message}</small> : null}</span>;
  return <div className="assignment-editor"><select aria-label="BD Executive" value={assigneeId} onChange={(event) => setAssigneeId(event.target.value)}>{people.map((person) => <option value={person.id} key={person.id}>{person.name}</option>)}</select><input aria-label="Scouting instructions" placeholder="Optional field note" value={instructions} onChange={(event) => setInstructions(event.target.value)} /><button className="primary-button compact" type="button" onClick={assign} disabled={!people.length}>Send</button><button className="icon-button quiet" type="button" title="Cancel" onClick={() => setOpen(false)}>×</button>{message ? <small>{message}</small> : null}</div>;
}

function EvidenceLegend() { return <div className="evidence-legend" aria-label="Evidence legend"><span><i className="legend-dot geography" />Real geography</span><span><i className="legend-dot sourced" />Real sourced data</span><span><i className="legend-dot cached" />Cached data</span><span><i className="legend-dot proxy" />Proxy data</span><span><i className="legend-dot field" />Field observations</span><span><i className="legend-dot missing" />Missing data</span><span><i className="legend-dot demo" />Demo/simulated</span></div>; }

function metricLabel(kind: string, category: string) {
  if (kind === "missing") return "missing data";
  if (kind === "demo") return "demo/simulated";
  if (kind === "field-survey") return "field observations";
  const proxy = ["homes", "businesses", "amenities", "mobility", "competition", "people"].includes(category);
  if (kind === "cached") return proxy ? "cached proxy data" : "cached sourced data";
  if (kind === "snapshot") return proxy ? "snapshot proxy data" : "sourced snapshot";
  return proxy ? "proxy data" : kind === "live" ? "real sourced data" : kind;
}

function formatAge(seconds?: number | null) { if (seconds == null) return "unknown"; if (seconds < 60) return `${seconds}s`; if (seconds < 3600) return `${Math.floor(seconds / 60)}m`; return `${Math.floor(seconds / 3600)}h`; }
