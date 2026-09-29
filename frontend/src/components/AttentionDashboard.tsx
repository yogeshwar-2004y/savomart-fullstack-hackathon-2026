import {
  AlertCircle,
  ArrowRight,
  BarChart3,
  Building2,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  ClipboardList,
  Compass,
  FileClock,
  HelpCircle,
  Info,
  LoaderCircle,
  MapPinned,
  Sparkles,
  Zap,
} from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { listReports, type ReportSummary } from "../services/m1";
import { listAssignments, listProperties, type Assignment, type PropertyRecord } from "../services/m2";
import { listCatchmentStudies, listSurveyZones, type CatchmentStudy, type SurveyZone } from "../services/m3";
import type { RoleId } from "./RoleShell";

type DashboardData = {
  reports?: ReportSummary[];
  assignments?: Assignment[];
  properties?: PropertyRecord[];
  studies?: CatchmentStudy[];
  zones?: SurveyZone[];
};

const roleCopy: Record<RoleId, { eyebrow: string; title: string; intro: string }> = {
  "bd-manager": {
    eyebrow: "Expansion Intelligence Workspace",
    title: "Good decisions start with visible evidence",
    intro: "Screen Chennai localities, delegate on-site property scouting, request ground-truth catchment studies, and record audited expansion decisions.",
  },
  "bd-executive": {
    eyebrow: "Field Scouting Operations",
    title: "On-site property inspection queue",
    intro: "Open an assigned scouting hotspot, confirm accurate GPS coordinates, capture property specifications and photos, and submit for deterministic scoring.",
  },
  "survey-manager": {
    eyebrow: "Survey Operations Planning",
    title: "Plan catchment coverage and delegate field zones",
    intro: "Review incoming catchment requests, inspect 90-day spatial reuse coverage, partition non-overlapping work zones, and assign survey executives.",
  },
  "survey-executive": {
    eyebrow: "Field Survey Execution",
    title: "Ground-truth lane observations",
    intro: "Inspect assigned longitudinal work zones, record residential and commercial unit density with footfall ratings, and complete zones with draft resilience.",
  },
};

export function AttentionDashboard({ role }: { role: RoleId }) {
  const [data, setData] = useState<DashboardData>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [guideExpanded, setGuideExpanded] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    const request: Promise<DashboardData> =
      role === "bd-manager"
        ? Promise.all([listReports(), listProperties(), listCatchmentStudies()]).then(
            ([reports, properties, studies]) => ({ reports, properties, studies })
          )
        : role === "bd-executive"
        ? listAssignments().then((assignments) => ({ assignments }))
        : role === "survey-manager"
        ? listCatchmentStudies().then((studies) => ({ studies }))
        : listSurveyZones().then((zones) => ({ zones }));

    request
      .then((result) => {
        if (active) {
          setData(result);
          setError("");
        }
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Workspace data is unavailable");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [role]);

  const attention = useMemo(() => buildAttention(role, data), [role, data]);
  const nextActions = useMemo(() => buildNextActions(role, data), [role, data]);
  const copy = roleCopy[role];

  return (
    <div className="role-dashboard">
      <header className="dashboard-hero">
        <div>
          <span className="eyebrow hero-eyebrow">
            <Sparkles size={13} style={{ display: "inline", verticalAlign: "-2px" }} /> {copy.eyebrow}
          </span>
          <h1>{copy.title}</h1>
          <p>{copy.intro}</p>
        </div>
        <WorkflowPath activeRole={role} onToggleGuide={() => setGuideExpanded((v) => !v)} />
      </header>

      {/* Expandable Workflow Progress Guide */}
      {guideExpanded ? (
        <section className="workflow-stepper-panel" aria-label="End-to-End Workflow Guide">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Savo SiteScout Workflow</span>
              <h3>The 4-Stage Expansion Lifecycle</h3>
            </div>
            <button
              type="button"
              className="icon-button quiet compact"
              onClick={() => setGuideExpanded(false)}
            >
              Close
            </button>
          </div>
          <div className="lifecycle-steps-grid">
            <div className={`lifecycle-step ${role === "bd-manager" ? "current-role-step" : ""}`}>
              <div className="step-badge">Phase 1</div>
              <h4>M1 Area Intelligence</h4>
              <p>BD Manager screens Chennai localities, analyses population density, OSM retail features, and competition headroom to extract scouting hotspots.</p>
              <small>Role: <strong>BD Manager</strong></small>
            </div>
            <div className={`lifecycle-step ${role === "bd-executive" ? "current-role-step" : ""}`}>
              <div className="step-badge">Phase 2</div>
              <h4>M2 Property Scouting</h4>
              <p>BD Executive visits hotspot on-site, corrects GPS pin, captures building dimensions, frontage, road width, utilities, and photos for Evaluation v1.</p>
              <small>Role: <strong>BD Executive</strong></small>
            </div>
            <div className={`lifecycle-step ${["survey-manager", "survey-executive"].includes(role) ? "current-role-step" : ""}`}>
              <div className="step-badge">Phase 3</div>
              <h4>M3 Catchment Study</h4>
              <p>Survey Manager checks 90-day coverage reuse and partitions remaining area into 1–8 zones. Survey Executives record lane density observations.</p>
              <small>Roles: <strong>Survey Manager & Executive</strong></small>
            </div>
            <div className={`lifecycle-step ${role === "bd-manager" ? "current-role-step" : ""}`}>
              <div className="step-badge">Phase 4</div>
              <h4>Decision & Governance</h4>
              <p>Catchment summary appends Evaluation v2 to the property. BD Manager examines score deltas and records an audited approval or rejection.</p>
              <small>Role: <strong>BD Manager</strong></small>
            </div>
          </div>
        </section>
      ) : null}

      {/* Dynamic "What should I do next?" Actionable Guide */}
      <section className="next-action-card" aria-label="What should I do next?">
        <div className="next-action-header">
          <div className="next-action-title-group">
            <div className="next-action-icon-badge">
              <Zap size={20} />
            </div>
            <div>
              <span className="eyebrow">Recommended Next Steps</span>
              <h2>What should I do next?</h2>
            </div>
          </div>
          {nextActions.primary ? (
            <Link className="primary-button highlight-cta" to={nextActions.primary.to}>
              {nextActions.primary.label} <ArrowRight size={17} />
            </Link>
          ) : null}
        </div>

        <div className="next-action-steps-list">
          {nextActions.steps.map((step, idx) => (
            <div key={idx} className="next-action-step-item">
              <div className="step-number-pill">{idx + 1}</div>
              <div className="step-content">
                <strong>{step.title}</strong>
                <p>{step.detail}</p>
              </div>
              {step.link ? (
                <Link className="secondary-button compact step-link-btn" to={step.link.to}>
                  {step.link.label} <ChevronRight size={15} />
                </Link>
              ) : null}
            </div>
          ))}
        </div>
      </section>

      {/* Live Work Queue Cards */}
      <section className="attention-section" aria-labelledby="attention-title">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Live Activity Metrics</span>
            <h2 id="attention-title">Work Queue Status</h2>
          </div>
          {attention.primary ? (
            <Link className="secondary-button" to={attention.primary.to}>
              {attention.primary.label} <ArrowRight size={16} />
            </Link>
          ) : null}
        </div>

        {loading ? (
          <div className="state-panel">
            <LoaderCircle className="spin" size={24} /> Loading your workspace data...
          </div>
        ) : null}

        {error ? (
          <div className="inline-error" role="alert">
            <AlertCircle size={20} />
            <div>
              <strong>Could not load live work</strong>
              <p>{error}</p>
            </div>
          </div>
        ) : null}

        {!loading && !error && !attention.cards.length ? (
          <div className="empty-panel">
            <ClipboardCheck size={32} />
            <h3>You are completely caught up</h3>
            <p>No open assignments or pending items are waiting for this demo identity.</p>
          </div>
        ) : null}

        {!loading && !error ? (
          <div className="attention-grid">
            {attention.cards.map((card) => (
              <Link className={`attention-card ${card.tone}`} to={card.to} key={card.label}>
                <span className="attention-icon">{card.icon}</span>
                <div className="attention-card-body">
                  <strong>{card.value}</strong>
                  <h3>{card.label}</h3>
                  <p>{card.detail}</p>
                </div>
                <ChevronRight size={20} className="attention-card-arrow" />
              </Link>
            ))}
          </div>
        ) : null}
      </section>
    </div>
  );
}

type Attention = {
  primary: { to: string; label: string };
  cards: Array<{ label: string; value: number; detail: string; to: string; tone: string; icon: ReactNode }>;
};

function buildAttention(role: RoleId, data: DashboardData): Attention {
  if (role === "bd-manager") {
    const pending = data.properties?.filter((item) => !["approved", "rejected"].includes(item.stage)) ?? [];
    const studies = data.studies?.filter((item) => ["requested", "assigned", "in_progress"].includes(item.status)) ?? [];
    const completedStudies = data.studies?.filter((item) => ["completed", "reused"].includes(item.status)) ?? [];

    return {
      primary: { to: "/manager/areas", label: "Start Area Analysis" },
      cards: [
        {
          label: "Saved Area Reports",
          value: data.reports?.length ?? 0,
          detail: "Screened Chennai localities with scouting hotspots",
          to: data.reports?.[0] ? `/manager/reports/${data.reports[0].id}` : "/manager/reports",
          tone: "purple",
          icon: <MapPinned />,
        },
        {
          label: "Properties Awaiting Decision",
          value: pending.length,
          detail: pending[0] ? `${pending[0].address} (${pending[0].stage.replaceAll("_", " ")})` : "No open property reviews",
          to: pending[0] ? `/manager/properties/${pending[0].id}` : "/manager/properties",
          tone: "yellow",
          icon: <Building2 />,
        },
        {
          label: "Active Catchment Studies",
          value: studies.length,
          detail: studies[0] ? `${studies[0].target_label}: ${studies[0].progress_percent.toFixed(0)}% complete` : `${completedStudies.length} completed/reused studies`,
          to: studies[0] ? `/manager/catchments/${studies[0].id}` : "/manager/catchments",
          tone: "green",
          icon: <BarChart3 />,
        },
      ],
    };
  }

  if (role === "bd-executive") {
    const open = data.assignments?.filter((item) => !item.property_id) ?? [];
    const submitted = data.assignments?.filter((item) => item.property_id) ?? [];
    return {
      primary: { to: "/executive/assignments", label: open.length ? "Open Next Assignment" : "Review Submissions" },
      cards: [
        {
          label: "Open Scouting Assignments",
          value: open.length,
          detail: open[0] ? `${open[0].target_label}, ${open[0].area_name}` : "No uncaptured assignments waiting",
          to: open[0] ? `/executive/assignments/${open[0].id}` : "/executive/assignments",
          tone: "yellow",
          icon: <ClipboardCheck />,
        },
        {
          label: "Properties Submitted",
          value: submitted.length,
          detail: "Captured on-site records with Evaluation v1 scores",
          to: submitted[0]?.property_id ? `/executive/submitted` : "/executive/submitted",
          tone: "green",
          icon: <Building2 />,
        },
      ],
    };
  }

  if (role === "survey-manager") {
    const requested = data.studies?.filter((item) => item.status === "requested") ?? [];
    const active = data.studies?.filter((item) => ["assigned", "in_progress"].includes(item.status)) ?? [];
    const completed = data.studies?.filter((item) => ["completed", "reused"].includes(item.status)) ?? [];

    return {
      primary: {
        to: requested[0] ? `/survey-manager/studies/${requested[0].id}` : active[0] ? `/survey-manager/studies/${active[0].id}` : "/survey-manager/requests",
        label: requested.length ? "Plan Requested Study" : active.length ? "Track Active Studies" : "Open Requests",
      },
      cards: [
        {
          label: "Requests Needing Zones",
          value: requested.length,
          detail: requested[0]?.target_label ?? "No unplanned catchment requests",
          to: requested[0] ? `/survey-manager/studies/${requested[0].id}` : "/survey-manager/requests",
          tone: "yellow",
          icon: <ClipboardList />,
        },
        {
          label: "Studies in Progress",
          value: active.length,
          detail: active[0] ? `${active[0].target_label}: ${active[0].progress_percent.toFixed(0)}% complete` : "No field surveys active",
          to: active[0] ? `/survey-manager/studies/${active[0].id}` : "/survey-manager/progress",
          tone: "purple",
          icon: <BarChart3 />,
        },
        {
          label: "Results & Reused Studies",
          value: completed.length,
          detail: completed[0] ? `${completed[0].target_label}: ${completed[0].status.replaceAll("_", " ")}` : "No completed studies yet",
          to: "/survey-manager/results",
          tone: "green",
          icon: <CheckCircle2 />,
        },
      ],
    };
  }

  const openZones = data.zones?.filter((item) => item.status !== "completed") ?? [];
  const completedZones = data.zones?.filter((item) => item.status === "completed") ?? [];
  const draftCount = openZones.filter((zone) =>
    Object.keys(window.localStorage).some((key) => key.includes(zone.id) && key.includes("draft"))
  ).length;

  return {
    primary: { to: "/survey-executive/zones", label: openZones.length ? "Open Next Zone" : "Review My Zones" },
    cards: [
      {
        label: "Assigned Work Zones",
        value: openZones.length,
        detail: openZones[0] ? `${openZones[0].label} (${openZones[0].study_label})` : "All assigned zones completed",
        to: openZones[0] ? `/survey-executive/zones/${openZones[0].id}` : "/survey-executive/zones",
        tone: "purple",
        icon: <ClipboardList />,
      },
      {
        label: "Local Drafts to Restore",
        value: draftCount,
        detail: draftCount ? "In-progress observations saved locally" : "No unsent local drafts",
        to: "/survey-executive/drafts",
        tone: "yellow",
        icon: <FileClock />,
      },
      {
        label: "Completed Zones",
        value: completedZones.length,
        detail: "Submitted lane observations aggregated",
        to: "/survey-executive/zones",
        tone: "green",
        icon: <CheckCircle2 />,
      },
    ],
  };
}

type ActionStep = {
  title: string;
  detail: string;
  link?: { to: string; label: string };
};

type NextActions = {
  primary?: { to: string; label: string };
  steps: ActionStep[];
};

function buildNextActions(role: RoleId, data: DashboardData): NextActions {
  if (role === "bd-manager") {
    const underReview = data.properties?.filter((p) => p.stage === "under_review") ?? [];
    const surveyReq = data.properties?.filter((p) => p.stage === "survey_requested") ?? [];
    const scouted = data.properties?.filter((p) => ["scouted", "shortlisted"].includes(p.stage)) ?? [];
    const reports = data.reports ?? [];

    if (underReview.length > 0) {
      return {
        primary: { to: `/manager/properties/${underReview[0].id}`, label: "Review Final Evaluation" },
        steps: [
          {
            title: `Make final expansion decision for "${underReview[0].address}"`,
            detail: `Catchment study has completed and Evaluation v2 has been appended (Score: ${underReview[0].evaluations.at(-1)?.score.toFixed(1) ?? "–"}). Review score deltas and record an audited decision (Approve / Reject).`,
            link: { to: `/manager/properties/${underReview[0].id}`, label: "Open Property Review" },
          },
          {
            title: "Screen new Chennai expansion localities",
            detail: "Initiate M1 area screening on OpenStreetMap boundaries or 0.01° grid cells.",
            link: { to: "/manager/areas", label: "Go to Area Intelligence" },
          },
        ],
      };
    }

    if (surveyReq.length > 0) {
      return {
        primary: { to: "/manager/catchments", label: "View Catchment Requests" },
        steps: [
          {
            title: `Catchment field survey in progress for "${surveyReq[0].address}"`,
            detail: "The catchment study has been handed off to the Survey Manager for zone partitioning and executive lane observation collection.",
            link: { to: "/manager/catchments", label: "Catchment Studies" },
          },
          {
            title: "Inspect property pipeline for other candidates",
            detail: "Review scouted candidates and shortlist promising sites for survey operations.",
            link: { to: "/manager/properties", label: "Property Pipeline" },
          },
        ],
      };
    }

    if (scouted.length > 0) {
      return {
        primary: { to: `/manager/properties/${scouted[0].id}`, label: "Review Scouted Site" },
        steps: [
          {
            title: `Review scouted property "${scouted[0].address}"`,
            detail: `Evaluation v1 generated by BD Executive (${scouted[0].evaluations[0]?.score.toFixed(1) ?? "–"} pts). Move to 'Shortlisted' or 'Survey Requested' to initiate catchment operations.`,
            link: { to: `/manager/properties/${scouted[0].id}`, label: "Review Property" },
          },
          {
            title: "Analyze additional Chennai areas",
            detail: "Use Velachery or grid cells to generate new scouting hotspots.",
            link: { to: "/manager/areas", label: "Area Intelligence" },
          },
        ],
      };
    }

    return {
      primary: { to: "/manager/areas", label: "Search an Area" },
      steps: [
        {
          title: "Search a Chennai area or select map cells",
          detail: "Type 'Velachery' or pick GCC ward boundaries on the map to start an M1 Area Intelligence analysis.",
          link: { to: "/manager/areas", label: "Start Area Search" },
        },
        {
          title: "Assign candidate hotspots to field executives",
          detail: "From saved reports, click 'Assign' beside any scouting suggestion to delegate field capture.",
          link: { to: "/manager/reports", label: "View Saved Reports" },
        },
      ],
    };
  }

  if (role === "bd-executive") {
    const open = data.assignments?.filter((a) => !a.property_id) ?? [];
    const submitted = data.assignments?.filter((a) => a.property_id) ?? [];

    if (open.length > 0) {
      return {
        primary: { to: `/executive/assignments/${open[0].id}`, label: "Open Next Assignment" },
        steps: [
          {
            title: `Capture property for "${open[0].target_label}" in ${open[0].area_name}`,
            detail: "Visit the assigned hotspot on-site. Correct the map pin, fill in building specifications, monthly rent, utilities, and upload verified photos.",
            link: { to: `/executive/assignments/${open[0].id}`, label: "Start Property Capture" },
          },
          {
            title: "Check previously submitted properties",
            detail: `You have submitted ${submitted.length} property record(s) for manager review.`,
            link: { to: "/executive/submitted", label: "View Submissions" },
          },
        ],
      };
    }

    return {
      primary: { to: "/executive/submitted", label: "View Submitted Properties" },
      steps: [
        {
          title: "All scouting assignments completed!",
          detail: "You have captured all open assignments. Check 'Properties Submitted' to inspect evaluation scores.",
          link: { to: "/executive/submitted", label: "Review Submissions" },
        },
        {
          title: "Coordinate with your BD Manager",
          detail: "Switch to BD Manager to assign new hotspots from M1 Area Intelligence reports.",
        },
      ],
    };
  }

  if (role === "survey-manager") {
    const requested = data.studies?.filter((s) => s.status === "requested") ?? [];
    const active = data.studies?.filter((s) => ["assigned", "in_progress"].includes(s.status)) ?? [];

    if (requested.length > 0) {
      return {
        primary: { to: `/survey-manager/studies/${requested[0].id}`, label: "Plan Catchment Zones" },
        steps: [
          {
            title: `Plan work zones for "${requested[0].target_label}"`,
            detail: "Inspect the 1 km target radius on the map. Review suggested mapped roads from OSM, choose 1–8 non-overlapping work zones, and assign field executives.",
            link: { to: `/survey-manager/studies/${requested[0].id}`, label: "Open Study Planner" },
          },
          {
            title: "Track active field survey operations",
            detail: `Monitor submitted lane observations across ${active.length} active study/studies.`,
            link: { to: "/survey-manager/progress", label: "Studies in Progress" },
          },
        ],
      };
    }

    if (active.length > 0) {
      return {
        primary: { to: `/survey-manager/studies/${active[0].id}`, label: "Track Active Study" },
        steps: [
          {
            title: `Monitor field survey for "${active[0].target_label}"`,
            detail: `Field executives are surveying zones (${active[0].progress_percent.toFixed(0)}% complete). Track lane observations and GPS quality.`,
            link: { to: `/survey-manager/studies/${active[0].id}`, label: "View Live Progress" },
          },
        ],
      };
    }

    return {
      primary: { to: "/survey-manager/requests", label: "Check Requests" },
      steps: [
        {
          title: "No pending catchment requests",
          detail: "New requests will appear when a BD Manager moves a property to 'Survey Requested'.",
          link: { to: "/survey-manager/requests", label: "Open Requests Queue" },
        },
        {
          title: "Inspect completed studies and reuse coverage",
          detail: "Revisit historical survey evidence and 90-day coverage reuse records.",
          link: { to: "/survey-manager/results", label: "Results & History" },
        },
      ],
    };
  }

  // Survey Executive
  const openZones = data.zones?.filter((z) => z.status !== "completed") ?? [];
  const draftCount = openZones.filter((zone) =>
    Object.keys(window.localStorage).some((key) => key.includes(zone.id) && key.includes("draft"))
  ).length;

  if (draftCount > 0) {
    return {
      primary: { to: "/survey-executive/drafts", label: "Restore Local Draft" },
      steps: [
        {
          title: "Restore unsent local survey draft",
          detail: "You have an unfinished lane observation saved locally on this browser. Restore and submit to avoid lost progress.",
          link: { to: "/survey-executive/drafts", label: "Open Drafts" },
        },
        {
          title: "Complete assigned survey zones",
          detail: `You have ${openZones.length} open zone(s) assigned.`,
          link: { to: "/survey-executive/zones", label: "Assigned Zones" },
        },
      ],
    };
  }

  if (openZones.length > 0) {
    return {
      primary: { to: `/survey-executive/zones/${openZones[0].id}`, label: "Start Zone Survey" },
      steps: [
        {
          title: `Conduct field survey for "${openZones[0].label}" (${openZones[0].study_label})`,
          detail: "Walk the assigned zone, record residential and commercial unit counts, rate pedestrian/vehicle activity, and complete the zone.",
          link: { to: `/survey-executive/zones/${openZones[0].id}`, label: "Open Zone" },
        },
      ],
    };
  }

  return {
    primary: { to: "/survey-executive/zones", label: "View My Zones" },
    steps: [
      {
        title: "All assigned survey zones are completed!",
        detail: "You have completed all allocated field zones. Check with your Survey Manager for new zone assignments.",
        link: { to: "/survey-executive/zones", label: "My Zones" },
      },
    ],
  };
}

function WorkflowPath({
  activeRole,
  onToggleGuide,
}: {
  activeRole: RoleId;
  onToggleGuide: () => void;
}) {
  const current =
    activeRole === "bd-manager" ? 1 : activeRole === "bd-executive" ? 2 : 3;

  return (
    <div className="workflow-path-container">
      <div className="workflow-path" aria-label="Site scouting workflow">
        <span className={current >= 1 ? "active" : ""}>
          M1 <small>Area</small>
        </span>
        <i />
        <span className={current >= 2 ? "active" : ""}>
          M2 <small>Property</small>
        </span>
        <i />
        <span className={current >= 3 ? "active" : ""}>
          M3 <small>Catchment</small>
        </span>
        <i />
        <span className={current >= 1 ? "active" : ""}>
          Gov <small>Decision</small>
        </span>
      </div>
      <button
        type="button"
        className="workflow-guide-trigger"
        onClick={onToggleGuide}
        title="View 4-stage workflow explanations"
      >
        <HelpCircle size={14} /> <span>Workflow Guide</span>
      </button>
    </div>
  );
}
