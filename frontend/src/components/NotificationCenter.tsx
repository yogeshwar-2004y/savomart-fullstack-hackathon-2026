import {
  AlertCircle,
  Bell,
  Building2,
  Check,
  CheckCheck,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  ClipboardList,
  Compass,
  FileClock,
  Sparkles,
  X,
} from "lucide-react";
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";
import { listReports, type ReportSummary } from "../services/m1";
import { listAssignments, listProperties, type Assignment, type PropertyRecord } from "../services/m2";
import { listCatchmentStudies, listSurveyZones, type CatchmentStudy, type SurveyZone } from "../services/m3";
import type { RoleId } from "./RoleShell";

export type NotificationItem = {
  id: string;
  title: string;
  message: string;
  timestamp: string;
  to: string;
  icon: ReactNode;
  category: "urgent" | "action" | "info" | "success";
};

interface NotificationCenterProps {
  activeRole: RoleId;
  currentUserId: string;
}

export function NotificationCenter({ activeRole, currentUserId }: NotificationCenterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const bellRef = useRef<HTMLButtonElement>(null);
  const [panelPosition, setPanelPosition] = useState({ top: 0, left: 0, width: 360 });
  const [filter, setFilter] = useState<"all" | "unread">("all");
  const [readIds, setReadIds] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem(`savo_notifications_read_${currentUserId}`);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [properties, setProperties] = useState<PropertyRecord[]>([]);
  const [studies, setStudies] = useState<CatchmentStudy[]>([]);
  const [zones, setZones] = useState<SurveyZone[]>([]);

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      listReports(),
      listAssignments(),
      listProperties(),
      listCatchmentStudies(),
      listSurveyZones(),
    ]).then(([repRes, assignRes, propRes, studyRes, zoneRes]) => {
      if (!active) return;
      if (repRes.status === "fulfilled") setReports(repRes.value);
      if (assignRes.status === "fulfilled") setAssignments(assignRes.value);
      if (propRes.status === "fulfilled") setProperties(propRes.value);
      if (studyRes.status === "fulfilled") setStudies(studyRes.value);
      if (zoneRes.status === "fulfilled") setZones(zoneRes.value);
    });

    return () => {
      active = false;
    };
  }, [activeRole, currentUserId]);

  const notifications = useMemo<NotificationItem[]>(() => {
    const list: NotificationItem[] = [];

    if (activeRole === "bd-manager") {
      // Under review properties needing final decision
      const underReview = properties.filter((p) => p.stage === "under_review");
      underReview.forEach((p) => {
        list.push({
          id: `prop-under-review-${p.id}`,
          title: "Final Decision Needed",
          message: `${p.address} has completed field catchment study. Evaluation v2 ready for approval/rejection.`,
          timestamp: p.transitions.at(-1)?.created_at ?? p.created_at,
          to: `/manager/properties/${p.id}`,
          icon: <Sparkles size={16} />,
          category: "urgent",
        });
      });

      // Scouted properties waiting for review
      const scouted = properties.filter((p) => p.stage === "scouted");
      scouted.forEach((p) => {
        list.push({
          id: `prop-scouted-${p.id}`,
          title: "New Property Submitted",
          message: `${p.assignee_name} captured site at ${p.address} (Score: ${p.evaluations[0]?.score.toFixed(1) ?? "–"}).`,
          timestamp: p.created_at,
          to: `/manager/properties/${p.id}`,
          icon: <Building2 size={16} />,
          category: "action",
        });
      });

      // Saved reports ready for scouting assignment
      reports.forEach((r) => {
        list.push({
          id: `report-ready-${r.id}`,
          title: "Area Report Ready",
          message: `Locality "${r.area_name}" analyzed (Fitness Score: ${r.score.toFixed(1)} · ${r.rating}). Ready for scouting.`,
          timestamp: r.created_at,
          to: `/manager/reports/${r.id}`,
          icon: <Compass size={16} />,
          category: "info",
        });
      });
    } else if (activeRole === "bd-executive") {
      // Open scouting assignments
      const open = assignments.filter((a) => !a.property_id);
      open.forEach((a) => {
        list.push({
          id: `assignment-open-${a.id}`,
          title: "New Scouting Assignment",
          message: `Visit hotspot "${a.target_label}" in ${a.area_name} and capture property details with photos.`,
          timestamp: a.created_at,
          to: `/executive/assignments/${a.id}`,
          icon: <ClipboardCheck size={16} />,
          category: "urgent",
        });
      });

      // Submitted properties
      const submitted = assignments.filter((a) => a.property_id);
      submitted.forEach((a) => {
        list.push({
          id: `assignment-submitted-${a.id}`,
          title: "Property Submitted",
          message: `Hotspot "${a.target_label}" successfully evaluated and delivered to BD Manager review.`,
          timestamp: a.created_at,
          to: "/executive/submitted",
          icon: <CheckCircle2 size={16} />,
          category: "success",
        });
      });
    } else if (activeRole === "survey-manager") {
      // Catchment requests needing planning
      const requested = studies.filter((s) => s.status === "requested");
      requested.forEach((s) => {
        list.push({
          id: `study-requested-${s.id}`,
          title: "Catchment Study Requested",
          message: `BD Manager requested ground-truth field survey for ${s.target_label}. Plan zones now.`,
          timestamp: s.created_at,
          to: `/survey-manager/studies/${s.id}`,
          icon: <ClipboardList size={16} />,
          category: "urgent",
        });
      });

      // Reused / completed studies
      const completed = studies.filter((s) => ["completed", "reused"].includes(s.status));
      completed.forEach((s) => {
        list.push({
          id: `study-done-${s.id}`,
          title: s.status === "reused" ? "Prior Coverage Reused" : "Catchment Survey Completed",
          message: `${s.target_label}: ${s.reuse_coverage.toFixed(0)}% coverage. Findings linked to property evaluation.`,
          timestamp: s.created_at,
          to: `/survey-manager/results`,
          icon: <CheckCircle2 size={16} />,
          category: "success",
        });
      });
    } else if (activeRole === "survey-executive") {
      // Assigned zones
      const activeZones = zones.filter((z) => z.status !== "completed");
      activeZones.forEach((z) => {
        list.push({
          id: `zone-assigned-${z.id}`,
          title: "Work Zone Assigned",
          message: `Survey zone "${z.label}" in ${z.study_label}. Collect residential/commercial units and footfall.`,
          timestamp: z.created_at,
          to: `/survey-executive/zones/${z.id}`,
          icon: <ClipboardList size={16} />,
          category: "action",
        });
      });

      // Draft recovery check
      const draftZones = activeZones.filter((zone) =>
        Object.keys(window.localStorage).some((key) => key.includes(zone.id) && key.includes("draft"))
      );
      draftZones.forEach((z) => {
        list.push({
          id: `draft-zone-${z.id}`,
          title: "Local Draft Available",
          message: `You have saved field observations in "${z.label}". Click to restore.`,
          timestamp: new Date().toISOString(),
          to: `/survey-executive/drafts`,
          icon: <FileClock size={16} />,
          category: "urgent",
        });
      });
    }

    return list.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  }, [activeRole, reports, assignments, properties, studies, zones]);

  const unreadCount = useMemo(
    () => notifications.filter((item) => !readIds.includes(item.id)).length,
    [notifications, readIds]
  );

  function markAsRead(id: string) {
    if (!readIds.includes(id)) {
      const next = [...readIds, id];
      setReadIds(next);
      try {
        localStorage.setItem(`savo_notifications_read_${currentUserId}`, JSON.stringify(next));
      } catch {
        // LocalStorage fallback
      }
    }
  }

  function markAllAsRead() {
    const allIds = notifications.map((n) => n.id);
    setReadIds(allIds);
    try {
      localStorage.setItem(`savo_notifications_read_${currentUserId}`, JSON.stringify(allIds));
    } catch {
      // LocalStorage fallback
    }
  }

  const visibleNotifications = useMemo(() => {
    if (filter === "unread") {
      return notifications.filter((n) => !readIds.includes(n.id));
    }
    return notifications;
  }, [notifications, filter, readIds]);

  useLayoutEffect(() => {
    if (!isOpen) return;

    function positionPanel() {
      const bell = bellRef.current;
      if (!bell) return;
      const rect = bell.getBoundingClientRect();
      const width = Math.min(360, window.innerWidth - 24);
      const besideSidebar = window.innerWidth > 820 && bell.closest(".app-sidebar");
      const preferredLeft = besideSidebar ? rect.right + 12 : rect.right - width;
      setPanelPosition({
        top: Math.min(rect.bottom + 8, window.innerHeight - 48),
        left: Math.max(12, Math.min(preferredLeft, window.innerWidth - width - 12)),
        width,
      });
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
        bellRef.current?.focus();
      }
    }

    positionPanel();
    window.addEventListener("resize", positionPanel);
    window.addEventListener("scroll", positionPanel, true);
    window.addEventListener("keydown", handleEscape);
    return () => {
      window.removeEventListener("resize", positionPanel);
      window.removeEventListener("scroll", positionPanel, true);
      window.removeEventListener("keydown", handleEscape);
    };
  }, [isOpen]);

  return (
    <div className="notification-center-wrap">
      <button
        ref={bellRef}
        type="button"
        className={`notification-bell-btn ${unreadCount > 0 ? "has-unread" : ""}`}
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label={`Notifications (${unreadCount} unread)`}
        aria-expanded={isOpen}
        title={`Notifications (${unreadCount} unread)`}
      >
        <Bell size={18} />
        {unreadCount > 0 ? (
          <span className="unread-badge-pill">{unreadCount > 9 ? "9+" : unreadCount}</span>
        ) : null}
      </button>

      {isOpen ? createPortal(
        <>
          <div className="notification-backdrop" onClick={() => setIsOpen(false)} />
          <div className="notification-popover" role="dialog" aria-label="Activity Feed" style={panelPosition}>
            <div className="notification-popover-header">
              <div className="notification-header-title">
                <strong>Activity Feed & Alerts</strong>
                {unreadCount > 0 ? (
                  <span className="unread-counter-tag">{unreadCount} new</span>
                ) : null}
              </div>
              <div className="notification-header-actions">
                {unreadCount > 0 ? (
                  <button
                    type="button"
                    className="icon-text-btn"
                    onClick={markAllAsRead}
                    title="Mark all as read"
                  >
                    <CheckCheck size={14} />
                    <span>Mark all read</span>
                  </button>
                ) : null}
                <button
                  type="button"
                  className="icon-button quiet compact"
                  onClick={() => setIsOpen(false)}
                  aria-label="Close notifications"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* Filter Tabs */}
            <div className="notification-filter-tabs">
              <button
                type="button"
                className={`tab-btn ${filter === "all" ? "active" : ""}`}
                onClick={() => setFilter("all")}
              >
                All ({notifications.length})
              </button>
              <button
                type="button"
                className={`tab-btn ${filter === "unread" ? "active" : ""}`}
                onClick={() => setFilter("unread")}
              >
                Unread ({unreadCount})
              </button>
            </div>

            {/* Notifications List */}
            <div className="notification-items-list">
              {visibleNotifications.length === 0 ? (
                <div className="notification-empty">
                  <CheckCircle2 size={28} />
                  <p>All caught up!</p>
                  <small>No {filter === "unread" ? "unread" : ""} notifications for this role.</small>
                </div>
              ) : (
                visibleNotifications.map((item) => {
                  const isRead = readIds.includes(item.id);
                  return (
                    <Link
                      key={item.id}
                      to={item.to}
                      className={`notification-item ${item.category} ${isRead ? "read" : "unread"}`}
                      onClick={() => {
                        markAsRead(item.id);
                        setIsOpen(false);
                      }}
                    >
                      <div className={`notification-item-icon ${item.category}`}>
                        {item.icon}
                      </div>
                      <div className="notification-item-content">
                        <div className="notification-item-top">
                          <strong>{item.title}</strong>
                          <span className="notif-time">
                            {new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                          </span>
                        </div>
                        <p>{item.message}</p>
                      </div>
                      {!isRead ? <span className="unread-dot" /> : null}
                      <ChevronRight size={14} className="notif-arrow" />
                    </Link>
                  );
                })
              )}
            </div>
          </div>
        </>,
        document.body
      ) : null}
    </div>
  );
}
