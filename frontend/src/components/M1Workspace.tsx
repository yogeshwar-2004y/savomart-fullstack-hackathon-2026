import { AlertCircle, BarChart3, CheckCircle2, Grid2X2, LoaderCircle, MapPin, Play, RefreshCw, Search } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { AreaMap } from "./AreaMap";
import {
  type AreaReport, type AreaSearchResult, type Comparison, type GeoJSONGeometry, type Job, type ReportSummary,
  compareReports, getJob, getReport, listReports, retryJob, searchAreas, startAnalysis
} from "../services/m1";

type Selection = { name: string; query?: string; selection_method: "locality" | "pincode" | "cells"; geometry: GeoJSONGeometry; source: string; limitations?: string | null };

const CELL_SIZE = 0.01;

export function M1Workspace() {
  const [query, setQuery] = useState("Velachery");
  const [method, setMethod] = useState<"locality" | "pincode">("locality");
  const [searching, setSearching] = useState(false);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [cells, setCells] = useState<number[][][][]>([]);
  const [cellMode, setCellMode] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [report, setReport] = useState<AreaReport | null>(null);
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [compareId, setCompareId] = useState("");
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshReports = () => listReports().then(setReports).catch(() => undefined);
  useEffect(() => { void refreshReports(); }, []);

  useEffect(() => {
    if (!job || job.status === "completed" || job.status === "failed") return;
    const timer = window.setInterval(async () => {
      try {
        const next = await getJob(job.id);
        setJob(next);
        if (next.status === "completed" && next.report_id) {
          const saved = await getReport(next.report_id);
          setReport(saved);
          await refreshReports();
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
    setSearching(true); setError(null); setReport(null); setComparison(null);
    try {
      const result = (await searchAreas(query, method))[0];
      selectResult(result);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Area search failed");
    } finally { setSearching(false); }
  }

  function selectResult(result: AreaSearchResult) {
    setCells([]); setCellMode(false);
    setSelection({
      name: result.display_name.split(",")[0], query: result.query,
      selection_method: result.selection_method, geometry: result.geometry,
      source: result.source, limitations: result.limitations
    });
  }

  function addCell(lat: number, lon: number) {
    const west = Math.floor(lon / CELL_SIZE) * CELL_SIZE;
    const south = Math.floor(lat / CELL_SIZE) * CELL_SIZE;
    const ring = [[west, south], [west + CELL_SIZE, south], [west + CELL_SIZE, south + CELL_SIZE], [west, south + CELL_SIZE], [west, south]];
    const key = `${west.toFixed(4)}:${south.toFixed(4)}`;
    const exists = cells.some((polygon) => `${polygon[0][0][0].toFixed(4)}:${polygon[0][0][1].toFixed(4)}` === key);
    const next = exists ? cells.filter((polygon) => `${polygon[0][0][0].toFixed(4)}:${polygon[0][0][1].toFixed(4)}` !== key) : [...cells, [ring]];
    setCells(next);
    if (next.length) setSelection({ name: `Selected Chennai cells (${next.length})`, selection_method: "cells", geometry: { type: "MultiPolygon", coordinates: next }, source: "Manager-selected 0.01 degree map cells", limitations: "Cells are geographic squares and vary slightly in ground area." });
    else setSelection(null);
  }

  async function analyze() {
    if (!selection) return;
    setError(null); setReport(null); setComparison(null);
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

  async function openSaved(id: string) {
    try { setReport(await getReport(id)); setComparison(null); setJob(null); setError(null); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not open report"); }
  }

  async function compare() {
    if (!report || !compareId) return;
    try { setComparison(await compareReports(report.id, compareId)); setError(null); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not compare reports"); }
  }

  const compareOptions = useMemo(() => reports.filter((item) => item.id !== report?.id), [reports, report]);

  return (
    <section className="m1-layout">
      <aside className="control-panel">
        <div className="section-heading"><div><p className="eyebrow">M1 Area Intelligence</p><h2>Choose a Chennai area</h2></div><MapPin size={24} /></div>
        <form className="search-form" onSubmit={onSearch}>
          <div className="segmented" aria-label="Search method">
            <button type="button" className={method === "locality" ? "active" : ""} onClick={() => setMethod("locality")}>Locality</button>
            <button type="button" className={method === "pincode" ? "active" : ""} onClick={() => setMethod("pincode")}>Pincode</button>
          </div>
          <div className="search-row"><input value={query} onChange={(event) => setQuery(event.target.value)} aria-label="Chennai locality or pincode" placeholder={method === "locality" ? "Velachery" : "600042"} /><button className="icon-button" title="Search" disabled={searching}><Search size={18} /></button></div>
        </form>
        <button className={cellMode ? "cell-toggle active" : "cell-toggle"} type="button" onClick={() => { setCellMode(!cellMode); setReport(null); }}><Grid2X2 size={18} />{cellMode ? "Click cells on map" : "Select map cells"}</button>
        {selection ? <div className="selection-summary"><strong>{selection.name}</strong><span>{selection.selection_method} · {selection.source}</span>{selection.limitations ? <small>{selection.limitations}</small> : null}</div> : <p className="muted">Search for a boundary or choose map cells.</p>}
        <button className="primary-button" type="button" disabled={!selection || (!!job && !["failed", "completed"].includes(job.status))} onClick={analyze}><Play size={18} />Start analysis</button>
        {job ? <JobProgress job={job} onRetry={retry} /> : null}
        {error ? <div className="inline-error"><AlertCircle size={18} />{error}</div> : null}
        <div className="saved-reports"><div className="list-title"><h3>Saved reports</h3><button className="icon-button quiet" title="Refresh reports" onClick={refreshReports}><RefreshCw size={16} /></button></div>{reports.length ? reports.map((item) => <button key={item.id} className="report-list-item" onClick={() => openSaved(item.id)}><span><strong>{item.area_name}</strong><small>{new Date(item.created_at).toLocaleString()}</small></span><b>{item.score.toFixed(1)}</b></button>) : <p className="muted">Completed analyses appear here.</p>}</div>
      </aside>

      <div className="map-report-panel">
        <AreaMap geometry={mapGeometry} suggestions={report?.suggestions ?? []} cellMode={cellMode} onCellClick={addCell} />
        {report ? <ReportView report={report} compareOptions={compareOptions} compareId={compareId} setCompareId={setCompareId} compare={compare} comparison={comparison} /> : <div className="map-caption"><strong>Real Chennai geography</strong><span>OpenStreetMap tiles and boundaries. Click cells only when cell selection is active.</span></div>}
      </div>
    </section>
  );
}

function JobProgress({ job, onRetry }: { job: Job; onRetry: () => void }) {
  const steps: Job["status"][] = ["queued", "fetching", "scoring", "completed"];
  const active = job.status === "failed" ? -1 : steps.indexOf(job.status);
  return <div className={`job-progress ${job.status}`}><div className="job-header">{job.status === "failed" ? <AlertCircle size={18} /> : job.status === "completed" ? <CheckCircle2 size={18} /> : <LoaderCircle className="spin" size={18} />}<strong>{job.status}</strong><span>{job.progress}%</span></div><div className="progress-track"><i style={{ width: `${job.progress}%` }} /></div><div className="job-steps">{steps.map((step, index) => <span className={index <= active ? "done" : ""} key={step}>{step}</span>)}</div><small>{job.status_detail}</small>{job.status === "failed" && job.retryable ? <button className="secondary-button" onClick={onRetry}><RefreshCw size={16} />Retry ({job.attempts}/3)</button> : null}</div>;
}

function ReportView({ report, compareOptions, compareId, setCompareId, compare, comparison }: { report: AreaReport; compareOptions: ReportSummary[]; compareId: string; setCompareId: (id: string) => void; compare: () => void; comparison: Comparison | null }) {
  return <article className="report-view"><header className="report-header"><div><p className="eyebrow">Saved {new Date(report.created_at).toLocaleString()}</p><h2>{report.title}</h2><p>{report.summary}</p></div><div className="score-block"><strong>{report.score.toFixed(1)}</strong><span>/ 100</span><b>{report.rating}</b></div></header>{report.used_cached_evidence ? <div className="cache-note"><AlertCircle size={17} />Cached evidence used after an upstream failure. Age: {formatAge(report.cache_age_seconds)}.</div> : null}<div className="report-meta"><span>{report.area_sq_km.toFixed(2)} km²</span><span>{report.selection_method}</span><span>{report.scoring_version}</span></div><section className="why-score"><div className="section-heading"><div><p className="eyebrow">Evidence ledger</p><h3>Why this score?</h3></div><BarChart3 size={22} /></div><div className="metric-table"><div className="metric-row metric-head"><span>Signal</span><span>Raw</span><span>Weight</span><span>Points</span></div>{report.metrics.map((metric) => <details className="metric-row" key={metric.key}><summary><span><b>{metric.label}</b><em>{metric.category} · {metric.evidence_kind}</em></span><span>{metric.raw_value === null ? "Unavailable" : `${metric.raw_value.toFixed(2)} ${metric.raw_unit}`}</span><span>{Math.round(metric.weight * 100)}%</span><strong>{metric.contribution.toFixed(2)}</strong></summary><div className="metric-detail"><p><b>Source:</b> {metric.source_name} · {new Date(metric.fetched_at).toLocaleString()}</p><p><b>Normalization:</b> {metric.transformation}</p><p><b>Geography:</b> {metric.geography}</p><p><b>Limitations:</b> {metric.limitations}</p>{metric.cache_age_seconds ? <p><b>Cache age:</b> {formatAge(metric.cache_age_seconds)}</p> : null}</div></details>)}</div></section><section className="suggestions"><h3>Places to scout</h3>{report.suggestions.map((item) => <div key={item.rank}><b>{item.rank}</b><span><strong>{item.label}</strong><small>{item.rationale}</small></span></div>)}</section><section className="comparison-controls"><h3>Compare saved reports</h3><div><select value={compareId} onChange={(event) => setCompareId(event.target.value)}><option value="">Choose another report</option>{compareOptions.map((item) => <option value={item.id} key={item.id}>{item.area_name} · {item.score.toFixed(1)}</option>)}</select><button className="secondary-button" disabled={!compareId} onClick={compare}>Compare</button></div>{comparison ? <div className="comparison-result"><span>{comparison.left.area_name}<b>{comparison.left.score.toFixed(1)}</b></span><i>vs</i><span>{comparison.right.area_name}<b>{comparison.right.score.toFixed(1)}</b></span><strong>{comparison.score_delta > 0 ? "+" : ""}{comparison.score_delta.toFixed(1)} points</strong></div> : null}</section></article>;
}

function formatAge(seconds?: number | null) { if (seconds == null) return "unknown"; if (seconds < 60) return `${seconds}s`; if (seconds < 3600) return `${Math.floor(seconds / 60)}m`; return `${Math.floor(seconds / 3600)}h`; }
