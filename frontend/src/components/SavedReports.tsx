import { AlertCircle, ArrowLeft, BarChart3, LoaderCircle, MapPinned, RefreshCw, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { compareReports, getReport, listReports, listStores, type AreaReport, type Comparison, type ReportSummary, type StoreLocation } from "../services/m1";
import { AreaMap } from "./AreaMap";
import { ReportView } from "./M1Workspace";

export function SavedReports() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  function load() {
    setLoading(true);
    setError("");
    listReports().then((items) => { setReports(items); setError(""); })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Could not load saved reports"))
      .finally(() => setLoading(false));
  }
  useEffect(() => { load(); }, []);
  return <section className="reports-page"><header className="page-heading"><div><p className="eyebrow">M1 Area Intelligence</p><h1>Saved Area Fitness Reports</h1><p>Reopen the exact saved geometry, evidence, and scoring version.</p></div><Link className="secondary-button" to="/manager/areas"><ArrowLeft size={17} />Area selection</Link></header>
    {loading ? <div className="state-panel"><LoaderCircle className="spin" /> Loading saved reports</div> : null}
    {error ? <div className="inline-error" role="alert"><AlertCircle />{error}<button type="button" className="secondary-button compact" onClick={load}><RefreshCw size={16} />Retry</button></div> : null}
    {!loading && !error && !reports.length ? <div className="empty-panel"><MapPinned /><h2>No saved reports</h2><p>Analyze a Chennai area to create the first report.</p><Link className="primary-button" to="/manager/areas">Analyze an area</Link></div> : null}
    <div className="report-card-grid">{reports.map((item) => <Link className="report-card" key={item.id} to={`/manager/reports/${item.id}`}><div><span className="report-card-icon"><MapPinned size={20} /></span><span className="report-card-score">{item.score.toFixed(1)}<small>/ 100</small></span></div><h2>{item.area_name}</h2><p>{item.rating} · {item.scoring_version}</p><small>Saved {new Date(item.created_at).toLocaleString()}</small><span className="report-card-action">Open report <BarChart3 size={16} /></span></Link>)}</div>
  </section>;
}

export function SavedReportDetail() {
  const { reportId } = useParams();
  const navigate = useNavigate();
  const [report, setReport] = useState<AreaReport | null>(null);
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [stores, setStores] = useState<StoreLocation[]>([]);
  const [compareId, setCompareId] = useState("");
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!reportId) return;
    setLoading(true);
    Promise.all([getReport(reportId), listReports().catch(() => [] as ReportSummary[]), listStores().catch(() => [] as StoreLocation[])]).then(([detail, items, storeItems]) => {
      setReport(detail); setReports(items); setStores(storeItems); setError("");
    }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Could not open report"))
      .finally(() => setLoading(false));
  }, [reportId]);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") navigate("/manager/reports"); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navigate]);
  const compareOptions = useMemo(() => reports.filter((item) => item.id !== reportId), [reports, reportId]);
  async function compare() {
    if (!reportId || !compareId) return;
    try {
      const result = await compareReports(reportId, compareId);
      setComparison({ ...result, score_delta: -result.score_delta });
      setError("");
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Comparison failed"); }
  }
  return <section className="report-detail-page"><header className="page-heading"><div><p className="eyebrow">Saved Area Fitness Report</p><h1>{report?.area_name ?? "Opening report"}</h1></div><Link className="secondary-button" to="/manager/reports" aria-label="Close report"><X size={18} />Close</Link></header>
    {loading ? <div className="state-panel"><LoaderCircle className="spin" /> Opening report</div> : null}
    {error ? <div className="inline-error" role="alert"><AlertCircle />{error}</div> : null}
    {report ? <div className="report-detail-layout"><div className="report-map-column"><div className="map-workspace"><AreaMap geometry={report.geometry} suggestions={report.suggestions} stores={stores} cellMode={false} onCellClick={() => undefined} /><div className="map-overlay-legend compact"><span><i className="overlay-area" />Saved area</span><span><i className="overlay-hotspot" />Scout hotspot</span><span><i className="overlay-store">S</i>Store</span></div></div><p className="map-source-line">{report.boundary_type} boundary · {report.source} · {new Date(report.boundary_lookup_at).toLocaleString()}</p></div><ReportView report={report} compareOptions={compareOptions} compareId={compareId} setCompareId={setCompareId} compare={compare} comparison={comparison} /></div> : null}
  </section>;
}
