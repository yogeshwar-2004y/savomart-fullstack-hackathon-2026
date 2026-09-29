import { AlertCircle, ArrowRight, BarChart3, Building2, ClipboardCheck, ClipboardList, LoaderCircle, MapPinned } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { listReports, type ReportSummary } from "../services/m1";
import { listAssignments, listProperties, type Assignment, type PropertyRecord } from "../services/m2";
import { listCatchmentStudies, listSurveyZones, type CatchmentStudy, type SurveyZone } from "../services/m3";
import type { RoleId } from "./RoleShell";

type DashboardData = { reports?: ReportSummary[]; assignments?: Assignment[]; properties?: PropertyRecord[]; studies?: CatchmentStudy[]; zones?: SurveyZone[] };
const roleCopy: Record<RoleId, { eyebrow: string; title: string; intro: string }> = {
  "bd-manager": { eyebrow: "Expansion workspace", title: "Good decisions start with visible evidence", intro: "Move from Chennai area intelligence to property review and catchment-backed decisions." },
  "bd-executive": { eyebrow: "Field scouting", title: "Your next property visit", intro: "Open an assigned hotspot, confirm the location, and capture a complete property record." },
  "survey-manager": { eyebrow: "Survey operations", title: "Plan coverage and unblock field work", intro: "Review incoming catchment requests, create practical zones, and track submitted evidence." },
  "survey-executive": { eyebrow: "Lane survey", title: "Capture observations without losing progress", intro: "Open your assigned zone, restore any local draft, and submit verified lane observations." }
};

export function AttentionDashboard({ role }: { role: RoleId }) {
  const [data, setData] = useState<DashboardData>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setLoading(true);
    const request: Promise<DashboardData> = role === "bd-manager"
      ? Promise.all([listReports(), listProperties(), listCatchmentStudies()]).then(([reports, properties, studies]) => ({ reports, properties, studies }))
      : role === "bd-executive" ? listAssignments().then((assignments) => ({ assignments }))
        : role === "survey-manager" ? listCatchmentStudies().then((studies) => ({ studies }))
          : listSurveyZones().then((zones) => ({ zones }));
    request.then((result) => { if (active) { setData(result); setError(""); } })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Workspace data is unavailable"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [role]);
  const attention = useMemo(() => buildAttention(role, data), [role, data]);
  const copy = roleCopy[role];
  return <div className="role-dashboard">
    <header className="dashboard-hero"><div><p className="eyebrow">{copy.eyebrow}</p><h1>{copy.title}</h1><p>{copy.intro}</p></div><WorkflowPath activeRole={role} /></header>
    <section className="attention-section" aria-labelledby="attention-title">
      <div className="section-heading"><div><p className="eyebrow">Live work queue</p><h2 id="attention-title">What needs my attention?</h2></div>{attention.primary ? <Link className="primary-button" to={attention.primary.to}>{attention.primary.label}<ArrowRight size={17} /></Link> : null}</div>
      {loading ? <div className="state-panel"><LoaderCircle className="spin" /> Loading your workspace</div> : null}
      {error ? <div className="inline-error" role="alert"><AlertCircle size={18} /><div><strong>Could not load live work</strong><p>{error}</p></div></div> : null}
      {!loading && !error && !attention.cards.length ? <div className="empty-panel"><ClipboardCheck /><h3>You are caught up</h3><p>No assigned or pending work is waiting for this demo user.</p></div> : null}
      {!loading && !error ? <div className="attention-grid">{attention.cards.map((card) => <Link className={`attention-card ${card.tone}`} to={card.to} key={card.label}><span className="attention-icon">{card.icon}</span><div><strong>{card.value}</strong><h3>{card.label}</h3><p>{card.detail}</p></div><ArrowRight size={18} /></Link>)}</div> : null}
    </section>
  </div>;
}

type Attention = { primary: { to: string; label: string }; cards: Array<{ label: string; value: number; detail: string; to: string; tone: string; icon: ReactNode }> };
function buildAttention(role: RoleId, data: DashboardData): Attention {
  if (role === "bd-manager") {
    const pending = data.properties?.filter((item) => !["approved", "rejected"].includes(item.stage)) ?? [];
    const studies = data.studies?.filter((item) => ["requested", "assigned", "in_progress"].includes(item.status)) ?? [];
    return { primary: { to: "/manager/areas", label: "Analyze an area" }, cards: [
      { label: "Saved area reports", value: data.reports?.length ?? 0, detail: "Available for comparison and hotspot assignment", to: data.reports?.[0] ? `/manager/reports/${data.reports[0].id}` : "/manager/reports", tone: "purple", icon: <MapPinned /> },
      { label: "Properties awaiting decision", value: pending.length, detail: pending[0] ? `${pending[0].target_label} is ${pending[0].stage.replaceAll("_", " ")}` : "No open property reviews", to: pending[0] ? `/manager/properties/${pending[0].id}` : "/manager/properties", tone: "yellow", icon: <Building2 /> },
      { label: "Active catchment studies", value: studies.length, detail: studies[0] ? `${studies[0].target_label}: ${studies[0].progress_percent.toFixed(0)}% complete` : "No catchment work in progress", to: studies[0] ? `/manager/catchments/${studies[0].id}` : "/manager/catchments", tone: "green", icon: <BarChart3 /> }
    ] };
  }
  if (role === "bd-executive") {
    const open = data.assignments?.filter((item) => !item.property_id) ?? [];
    const submitted = data.assignments?.filter((item) => item.property_id) ?? [];
    return { primary: { to: "/executive/assignments", label: open.length ? "Open next assignment" : "Review submissions" }, cards: [
      { label: "Scouting assignments", value: open.length, detail: open[0] ? `${open[0].target_label}, ${open[0].area_name}` : "No unsubmitted assignments", to: open[0] ? `/executive/assignments/${open[0].id}` : "/executive/assignments", tone: "yellow", icon: <ClipboardCheck /> },
      { label: "Properties submitted", value: submitted.length, detail: "Captured assignments visible to your manager", to: submitted[0]?.property_id ? `/executive/properties/${submitted[0].property_id}` : "/executive/submitted", tone: "green", icon: <Building2 /> }
    ] };
  }
  if (role === "survey-manager") {
    const requested = data.studies?.filter((item) => item.status === "requested") ?? [];
    const active = data.studies?.filter((item) => ["assigned", "in_progress"].includes(item.status)) ?? [];
    return { primary: { to: requested[0] ? `/survey-manager/studies/${requested[0].id}` : "/survey-manager/requests", label: requested.length ? "Plan requested study" : "Open requests" }, cards: [
      { label: "Requests needing zones", value: requested.length, detail: requested[0]?.target_label ?? "No unplanned requests", to: requested[0] ? `/survey-manager/studies/${requested[0].id}` : "/survey-manager/requests", tone: "yellow", icon: <ClipboardList /> },
      { label: "Studies in progress", value: active.length, detail: active[0] ? `${active[0].target_label}: ${active[0].progress_percent.toFixed(0)}% complete` : "No field work underway", to: active[0] ? `/survey-manager/studies/${active[0].id}` : "/survey-manager/progress", tone: "purple", icon: <BarChart3 /> }
    ] };
  }
  const openZones = data.zones?.filter((item) => item.status !== "completed") ?? [];
  const draftCount = openZones.filter((zone) => Object.keys(window.localStorage).some((key) => key.includes(zone.id) && key.includes("draft"))).length;
  return { primary: { to: "/survey-executive/zones", label: openZones.length ? "Open next zone" : "Review my zones" }, cards: [
    { label: "Zones assigned", value: openZones.length, detail: openZones[0]?.label ?? "No incomplete zones", to: openZones[0] ? `/survey-executive/zones/${openZones[0].id}` : "/survey-executive/zones", tone: "purple", icon: <ClipboardList /> },
    { label: "Local drafts to restore", value: draftCount, detail: draftCount ? "Draft observations remain on this device" : "No unsent local drafts", to: "/survey-executive/drafts", tone: "yellow", icon: <ClipboardCheck /> }
  ] };
}

function WorkflowPath({ activeRole }: { activeRole: RoleId }) {
  const current = activeRole === "bd-manager" ? 1 : activeRole === "bd-executive" ? 2 : 3;
  return <div className="workflow-path" aria-label="Site scouting workflow"><span className={current >= 1 ? "active" : ""}>M1 <small>Area</small></span><i /><span className={current >= 2 ? "active" : ""}>M2 <small>Property</small></span><i /><span className={current >= 3 ? "active" : ""}>M3 <small>Catchment</small></span></div>;
}
