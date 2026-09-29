import { ArrowRight, BarChart3, Building2, CheckCircle2, ChevronRight, ClipboardList, Compass, MapPinned, ShieldCheck, Sparkles, UserCheck, Users, X } from "lucide-react";
import { useEffect, useState } from "react";
import type { RoleId } from "./RoleShell";
import { roles } from "./RoleShell";

interface WorkspaceWelcomeProps {
  isOpen: boolean;
  activeRole: RoleId;
  currentUserId: string;
  onClose: () => void;
  onSwitchRole: (role: RoleId) => void;
}

export function WorkspaceWelcome({
  isOpen,
  activeRole,
  currentUserId,
  onClose,
  onSwitchRole,
}: WorkspaceWelcomeProps) {
  const [selectedTab, setSelectedTab] = useState<"welcome" | "roles" | "workflow">("welcome");

  useEffect(() => {
    if (!isOpen) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const currentRoleObj = roles.find((r) => r.id === activeRole) ?? roles[0];
  const currentUserObj = currentRoleObj.users.find((u) => u.id === currentUserId) ?? currentRoleObj.users[0];

  return (
    <div
      className="modal-backdrop welcome-modal-backdrop"
      role="presentation"
      onMouseDown={onClose}
    >
      <div
        className="welcome-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="welcome-title"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <header className="welcome-header">
          <div className="welcome-brand">
            <div className="brand-pin welcome-pin">
              <span>S</span>
            </div>
            <div>
              <span className="eyebrow welcome-eyebrow">
                <Sparkles size={13} style={{ display: "inline", verticalAlign: "-2px" }} /> Savo SiteScout Operations
              </span>
              <h2 id="welcome-title">Chennai Expansion Workspace</h2>
            </div>
          </div>
          <button
            className="icon-button quiet welcome-close"
            type="button"
            aria-label="Close welcome guide"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </header>

        <div className="welcome-tabs-nav" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={selectedTab === "welcome"}
            className={`welcome-tab-btn ${selectedTab === "welcome" ? "active" : ""}`}
            onClick={() => setSelectedTab("welcome")}
          >
            <Compass size={16} /> Overview
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={selectedTab === "roles"}
            className={`welcome-tab-btn ${selectedTab === "roles" ? "active" : ""}`}
            onClick={() => setSelectedTab("roles")}
          >
            <Users size={16} /> Roles & Access ({roles.length})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={selectedTab === "workflow"}
            className={`welcome-tab-btn ${selectedTab === "workflow" ? "active" : ""}`}
            onClick={() => setSelectedTab("workflow")}
          >
            <BarChart3 size={16} /> 4-Stage Workflow
          </button>
        </div>

        <div className="welcome-body">
          {selectedTab === "welcome" ? (
            <div className="welcome-content-fade">
              <div className="welcome-hero-banner">
                <p className="welcome-intro-lead">
                  <strong>Savo SiteScout</strong> is a unified intelligence and field operations workspace designed for Savomart's expansion across Greater Chennai.
                </p>
                <p className="welcome-intro-sub">
                  Carry real Chennai localities from virtual GIS area screening to on-site property scouting, ground-truth catchment observations, and audited investment decisions.
                </p>
              </div>

              <div className="welcome-current-role-card">
                <div className="welcome-role-badge">
                  <UserCheck size={18} />
                  <span>Currently Active Workspace</span>
                </div>
                <div className="welcome-role-details">
                  <div className="welcome-role-icon">{currentRoleObj.icon}</div>
                  <div>
                    <h3>{currentRoleObj.label}</h3>
                    <p>{currentRoleObj.focus}</p>
                    <small>Logged in as <strong>{currentUserObj.name}</strong> ({currentUserObj.id})</small>
                  </div>
                </div>
              </div>

              <div className="welcome-quick-capabilities">
                <h4>What you can do in this workspace:</h4>
                <div className="welcome-caps-grid">
                  <div className="welcome-cap-item">
                    <MapPinned size={18} />
                    <div>
                      <strong>M1 Area Intelligence</strong>
                      <span>OSM boundary geocoding, 200 GCC wards, 11 SAVOmart reference store buffers.</span>
                    </div>
                  </div>
                  <div className="welcome-cap-item">
                    <Building2 size={18} />
                    <div>
                      <strong>M2 Property Scouting</strong>
                      <span>Field pin capture, photo uploads, and versioned deterministic scoring.</span>
                    </div>
                  </div>
                  <div className="welcome-cap-item">
                    <ClipboardList size={18} />
                    <div>
                      <strong>M3 Catchment Studies</strong>
                      <span>90-day spatial reuse union, 1–8 zone partitioning, and lane density observations.</span>
                    </div>
                  </div>
                  <div className="welcome-cap-item">
                    <ShieldCheck size={18} />
                    <div>
                      <strong>Audited Governance</strong>
                      <span>Immutable transition logs, metric provenance, and structured decision reasons.</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : selectedTab === "roles" ? (
            <div className="welcome-content-fade">
              <p className="welcome-roles-intro">
                Switching roles immediately updates the workspace view, sidebar navigation, and demo identity headers sent with API requests:
              </p>
              <div className="welcome-roles-grid">
                {roles.map((r) => {
                  const isCurrent = r.id === activeRole;
                  return (
                    <div
                      key={r.id}
                      className={`welcome-role-tile ${isCurrent ? "active-role" : ""}`}
                    >
                      <div className="welcome-role-tile-header">
                        <span className="welcome-role-tile-icon">{r.icon}</span>
                        <div>
                          <h4>{r.label}</h4>
                          <span className="welcome-user-tag">{r.users.map((u) => u.name).join(", ")}</span>
                        </div>
                        {isCurrent ? <span className="active-pill">Active</span> : null}
                      </div>
                      <p className="welcome-role-tile-focus">{r.focus}</p>
                      <div className="welcome-role-tile-routes">
                        <small>Key destinations:</small>
                        <ul>
                          {r.navigation.slice(1, 4).map((nav) => (
                            <li key={nav.to}>{nav.label}</li>
                          ))}
                        </ul>
                      </div>
                      {!isCurrent ? (
                        <button
                          type="button"
                          className="secondary-button compact welcome-role-switch-btn"
                          onClick={() => {
                            onSwitchRole(r.id);
                            onClose();
                          }}
                        >
                          Switch to {r.shortLabel} <ChevronRight size={14} />
                        </button>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="welcome-content-fade">
              <div className="welcome-workflow-steps">
                <div className="welcome-step-card">
                  <div className="welcome-step-num">1</div>
                  <div className="welcome-step-body">
                    <span className="welcome-step-role">BD Manager</span>
                    <h4>M1 Area Screening & Hotspots</h4>
                    <p>Search Chennai areas or select map cells. The system scores population density, competitors, and accessibility to generate candidate scouting hotspots.</p>
                  </div>
                </div>
                <div className="welcome-step-card">
                  <div className="welcome-step-num">2</div>
                  <div className="welcome-step-body">
                    <span className="welcome-step-role">BD Executive</span>
                    <h4>M2 On-Site Property Capture</h4>
                    <p>Open assigned hotspot, correct GPS coordinates, record rent, size, frontage, road width, utilities, and upload verified site photos for initial Evaluation v1.</p>
                  </div>
                </div>
                <div className="welcome-step-card">
                  <div className="welcome-step-num">3</div>
                  <div className="welcome-step-body">
                    <span className="welcome-step-role">Survey Manager & Executive</span>
                    <h4>M3 Catchment Study & Field Evidence</h4>
                    <p>Manager partitions 1 km catchment into work zones. Executives survey lanes for residential/commercial unit density and pedestrian/vehicle activity.</p>
                  </div>
                </div>
                <div className="welcome-step-card">
                  <div className="welcome-step-num">4</div>
                  <div className="welcome-step-body">
                    <span className="welcome-step-role">BD Manager</span>
                    <h4>Evaluation v2 & Audited Decision</h4>
                    <p>Catchment observations update property fitness to Evaluation v2. The manager reviews score deltas and records a formal decision with full audit provenance.</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <footer className="welcome-footer">
          <div className="welcome-footer-info">
            <CheckCircle2 size={16} color="var(--success)" />
            <span>PostGIS, Redis, & FastAPI live on local environment</span>
          </div>
          <button className="primary-button welcome-continue-btn" type="button" onClick={onClose}>
            Continue to workspace <ArrowRight size={17} />
          </button>
        </footer>
      </div>
    </div>
  );
}
