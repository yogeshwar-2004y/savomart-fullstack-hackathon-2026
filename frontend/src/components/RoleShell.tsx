import {
  BarChart3,
  BriefcaseBusiness,
  Building2,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  ClipboardList,
  Compass,
  Database,
  FileClock,
  Files,
  History,
  LayoutDashboard,
  MapPinned,
  Menu,
  PanelLeftClose,
  Server,
  Smartphone,
  Sparkles,
  UserCheck,
  Waves,
  X,
} from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import type { HealthResponse } from "../services/health";
import { WorkspaceWelcome } from "./WorkspaceWelcome";
import { NotificationCenter } from "./NotificationCenter";

export type RoleId = "bd-manager" | "bd-executive" | "survey-manager" | "survey-executive";
export type DemoUser = { id: string; name: string };
export type NavItem = { to: string; label: string; icon: ReactNode; section?: string };
export type Role = {
  id: RoleId;
  label: string;
  shortLabel: string;
  focus: string;
  icon: ReactNode;
  users: DemoUser[];
  navigation: NavItem[];
};

export const roleHome: Record<RoleId, string> = {
  "bd-manager": "/manager",
  "bd-executive": "/executive",
  "survey-manager": "/survey-manager",
  "survey-executive": "/survey-executive",
};

export const roles: Role[] = [
  {
    id: "bd-manager",
    label: "BD Manager",
    shortLabel: "BD",
    focus: "Area intelligence, scouting delegation, and expansion decisions",
    icon: <MapPinned size={18} />,
    users: [{ id: "bd-manager-1", name: "Meera Raman" }],
    navigation: [
      { to: "/manager", label: "Overview", icon: <LayoutDashboard size={18} />, section: "Workspace" },
      { to: "/manager/areas", label: "Area Intelligence", icon: <MapPinned size={18} />, section: "Intelligence" },
      { to: "/manager/reports", label: "Saved Reports", icon: <Files size={18} />, section: "Intelligence" },
      { to: "/manager/assignments", label: "Scouting Assignments", icon: <ClipboardCheck size={18} />, section: "Field Operations" },
      { to: "/manager/properties", label: "Property Pipeline", icon: <Building2 size={18} />, section: "Field Operations" },
      { to: "/manager/catchments", label: "Catchment Requests", icon: <BarChart3 size={18} />, section: "Field Operations" },
      { to: "/manager/decisions", label: "Decisions & History", icon: <History size={18} />, section: "Governance" },
    ],
  },
  {
    id: "bd-executive",
    label: "BD Executive",
    shortLabel: "BD",
    focus: "Assigned scouting visits, GPS verification, and property capture",
    icon: <Smartphone size={18} />,
    users: [
      { id: "bd-executive-1", name: "Arun Kumar" },
      { id: "bd-executive-2", name: "Kavya Selvan" },
    ],
    navigation: [
      { to: "/executive", label: "Overview", icon: <LayoutDashboard size={18} />, section: "Workspace" },
      { to: "/executive/assignments", label: "My Scouting Assignments", icon: <ClipboardCheck size={18} />, section: "Scouting Tasks" },
      { to: "/executive/submitted", label: "Properties Submitted", icon: <Building2 size={18} />, section: "Scouting Tasks" },
    ],
  },
  {
    id: "survey-manager",
    label: "Survey Manager",
    shortLabel: "Survey",
    focus: "Catchment study planning, zone partitioning, and results tracking",
    icon: <BriefcaseBusiness size={18} />,
    users: [{ id: "survey-manager-1", name: "Priya Natarajan" }],
    navigation: [
      { to: "/survey-manager", label: "Overview", icon: <LayoutDashboard size={18} />, section: "Workspace" },
      { to: "/survey-manager/requests", label: "Requests Needing Action", icon: <BriefcaseBusiness size={18} />, section: "Catchment Studies" },
      { to: "/survey-manager/progress", label: "Studies in Progress", icon: <BarChart3 size={18} />, section: "Catchment Studies" },
      { to: "/survey-manager/results", label: "Results and History", icon: <History size={18} />, section: "Catchment Studies" },
    ],
  },
  {
    id: "survey-executive",
    label: "Survey Executive",
    shortLabel: "Survey",
    focus: "Assigned zone visits, lane-level counts, and draft recovery",
    icon: <ClipboardList size={18} />,
    users: [
      { id: "survey-executive-1", name: "Dinesh Ravi" },
      { id: "survey-executive-2", name: "Nila Krishnan" },
    ],
    navigation: [
      { to: "/survey-executive", label: "Overview", icon: <LayoutDashboard size={18} />, section: "Workspace" },
      { to: "/survey-executive/zones", label: "Assigned Zones", icon: <ClipboardList size={18} />, section: "Field Surveys" },
      { to: "/survey-executive/drafts", label: "Local Drafts to Restore", icon: <FileClock size={18} />, section: "Field Surveys" },
    ],
  },
];

type RoleShellProps = {
  activeRole: RoleId;
  currentUserId: string;
  health: HealthResponse | null;
  healthError: string | null;
  onRoleChange: (role: RoleId) => void;
  onUserChange: (userId: string) => void;
  children: ReactNode;
};

export function RoleShell({
  activeRole,
  currentUserId,
  health,
  healthError,
  onRoleChange,
  onUserChange,
  children,
}: RoleShellProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [welcomeOpen, setWelcomeOpen] = useState(false);
  const location = useLocation();

  const selected = roles.find((role) => role.id === activeRole) ?? roles[0];
  const user = selected.users.find((item) => item.id === currentUserId) ?? selected.users[0];

  useEffect(() => {
    setDrawerOpen(false);
    setDropdownOpen(false);
  }, [location.pathname]);

  // Close dropdown on Escape key or outside click
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setDropdownOpen(false);
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  function handleSelectRole(roleId: RoleId, userId?: string) {
    const targetRole = roles.find((r) => r.id === roleId) ?? roles[0];
    const targetUserId = userId || targetRole.users[0].id;
    onRoleChange(roleId);
    onUserChange(targetUserId);
    setDropdownOpen(false);
  }

  // Group navigation items
  const groupedNavigation: Record<string, NavItem[]> = {};
  for (const item of selected.navigation) {
    const section = item.section ?? "Workspace";
    if (!groupedNavigation[section]) {
      groupedNavigation[section] = [];
    }
    groupedNavigation[section].push(item);
  }

  return (
    <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
      <a className="skip-link" href="#workspace-content">
        Skip to workspace
      </a>

      <header className="mobile-header">
        <button
          className="icon-button mobile-menu-btn"
          type="button"
          aria-label="Open navigation drawer"
          onClick={() => setDrawerOpen(true)}
        >
          <Menu size={22} />
        </button>
        <Brand compact />
        <div className="mobile-header-right">
          <NotificationCenter activeRole={activeRole} currentUserId={currentUserId} />
          <div className="mobile-role-container">
            <button
              className="mobile-role-pill"
              type="button"
              onClick={() => setDropdownOpen((prev) => !prev)}
              title="Switch demo role"
              aria-expanded={dropdownOpen}
            >
              <span>{selected.label}</span>
              <ChevronDown size={14} />
            </button>
            {dropdownOpen ? (
              <RoleDropdownMenu
                activeRole={activeRole}
                currentUserId={currentUserId}
                onSelectRole={handleSelectRole}
                onClose={() => setDropdownOpen(false)}
              />
            ) : null}
          </div>
        </div>
      </header>

      {drawerOpen ? (
        <button
          className="drawer-scrim"
          aria-label="Close navigation"
          onClick={() => setDrawerOpen(false)}
        />
      ) : null}

      <aside
        className={`app-sidebar ${drawerOpen ? "drawer-open" : ""}`}
        aria-label="Primary navigation"
      >
        <div className="sidebar-brand-row">
          <Brand compact={collapsed} />
          <div className="sidebar-brand-actions">
            <NotificationCenter activeRole={activeRole} currentUserId={currentUserId} />
            <button
              className="sidebar-close-mobile icon-button quiet"
              type="button"
              aria-label="Close navigation"
              onClick={() => setDrawerOpen(false)}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Sleek Role Switcher Dropdown */}
        <div className="sidebar-role-card">
          <button
            type="button"
            className={`role-switcher-trigger ${dropdownOpen ? "active" : ""}`}
            onClick={() => setDropdownOpen((prev) => !prev)}
            title={collapsed ? `${selected.label} (${user.name}) - Click to switch role` : "Click to switch role or demo user"}
            aria-haspopup="listbox"
            aria-expanded={dropdownOpen}
          >
            <div className="role-trigger-icon-box">{selected.icon}</div>
            {!collapsed ? (
              <div className="role-trigger-text">
                <span className="role-trigger-eyebrow">Active Workspace</span>
                <strong>{selected.label}</strong>
                <small className="role-trigger-user">{user.name}</small>
              </div>
            ) : null}
            {!collapsed ? <ChevronDown size={16} className={`role-trigger-chevron ${dropdownOpen ? "rotate" : ""}`} /> : null}
          </button>

          {dropdownOpen ? (
            <RoleDropdownMenu
              activeRole={activeRole}
              currentUserId={currentUserId}
              onSelectRole={handleSelectRole}
              onClose={() => setDropdownOpen(false)}
            />
          ) : null}
        </div>

        {/* Sidebar Navigation Groups */}
        <nav className="sidebar-nav">
          {Object.entries(groupedNavigation).map(([sectionTitle, navItems]) => (
            <div key={sectionTitle} className="nav-group">
              {!collapsed ? (
                <span className="nav-group-heading">{sectionTitle}</span>
              ) : (
                <div className="nav-group-divider" />
              )}
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === roleHome[activeRole]}
                  title={collapsed ? `${item.label} (${sectionTitle})` : undefined}
                  className={({ isActive }) => `sidebar-nav-link ${isActive ? "active" : ""}`}
                >
                  <span className="nav-icon-wrap">{item.icon}</span>
                  {!collapsed ? <span className="nav-label">{item.label}</span> : null}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar-spacer" />

        {/* Workspace Guide / Onboarding Trigger */}
        <div className="sidebar-guide-box">
          <button
            type="button"
            className="sidebar-guide-btn"
            onClick={() => setWelcomeOpen(true)}
            title={collapsed ? "Workspace Guide & Overview" : undefined}
          >
            <Compass size={17} />
            {!collapsed ? <span>Workspace Guide</span> : null}
            {!collapsed ? <Sparkles size={14} className="guide-sparkle" /> : null}
          </button>
        </div>

        {/* Service Health Pill */}
        <ServiceHealth health={health} error={healthError} collapsed={collapsed} />

        {/* Collapse Sidebar Button */}
        <button
          className="sidebar-collapse"
          type="button"
          onClick={() => setCollapsed((value) => !value)}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <ChevronRight size={18} />
          ) : (
            <>
              <PanelLeftClose size={18} />
              <span>Collapse sidebar</span>
              <ChevronLeft size={16} />
            </>
          )}
        </button>
      </aside>

      <main id="workspace-content" className="workspace-content" tabIndex={-1}>
        {children}
      </main>

      {/* Workspace Welcome & Guide Modal */}
      <WorkspaceWelcome
        isOpen={welcomeOpen}
        activeRole={activeRole}
        currentUserId={currentUserId}
        onClose={() => setWelcomeOpen(false)}
        onSwitchRole={onRoleChange}
      />
    </div>
  );
}

type RoleDropdownMenuProps = {
  activeRole: RoleId;
  currentUserId: string;
  onSelectRole: (roleId: RoleId, userId?: string) => void;
  onClose: () => void;
};

function RoleDropdownMenu({
  activeRole,
  currentUserId,
  onSelectRole,
  onClose,
}: RoleDropdownMenuProps) {
  return (
    <>
      <div className="role-dropdown-backdrop" onClick={onClose} />
      <div className="role-dropdown-menu" role="listbox" aria-label="Select operational role">
        <div className="role-dropdown-header">
          <span>Switch Workspace Role</span>
          <button
            type="button"
            className="icon-button quiet compact"
            onClick={onClose}
            aria-label="Close dropdown"
          >
            <X size={15} />
          </button>
        </div>
        <div className="role-dropdown-list">
          {roles.map((role) => {
            const isActive = role.id === activeRole;
            return (
              <div
                key={role.id}
                className={`role-dropdown-option ${isActive ? "active" : ""}`}
              >
                <button
                  type="button"
                  className="role-dropdown-main-btn"
                  onClick={() => onSelectRole(role.id)}
                >
                  <div className="role-dropdown-icon">{role.icon}</div>
                  <div className="role-dropdown-info">
                    <div className="role-dropdown-title-row">
                      <strong>{role.label}</strong>
                      {isActive ? (
                        <span className="active-badge">
                          <Check size={12} /> Active
                        </span>
                      ) : null}
                    </div>
                    <p className="role-dropdown-desc">{role.focus}</p>
                  </div>
                </button>
                {role.users.length > 1 ? (
                  <div className="role-dropdown-users">
                    <span className="role-user-label">Switch identity:</span>
                    <div className="role-user-pills">
                      {role.users.map((u) => (
                        <button
                          key={u.id}
                          type="button"
                          className={`user-pill ${isActive && currentUserId === u.id ? "selected" : ""}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectRole(role.id, u.id);
                          }}
                        >
                          <UserCheck size={12} />
                          <span>{u.name}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link to="/" className="savo-brand" aria-label="Savo SiteScout Home">
      <div className="brand-pin">
        <span>S</span>
      </div>
      {compact ? null : (
        <div>
          <strong>SAVO</strong>
          <span>SiteScout</span>
        </div>
      )}
    </Link>
  );
}

function ServiceHealth({
  health,
  error,
  collapsed,
}: {
  health: HealthResponse | null;
  error: string | null;
  collapsed: boolean;
}) {
  const allOk = !error && health?.database.status === "ok" && health?.redis.status === "ok";
  return (
    <div
      className={`sidebar-health ${allOk ? "healthy" : "unhealthy"}`}
      title={error ?? "FastAPI, PostgreSQL/PostGIS, and Redis live status"}
    >
      <span className="health-dot" />
      {collapsed ? null : (
        <div>
          <strong>{allOk ? "Services connected" : error ? "Backend unavailable" : "Checking services"}</strong>
          <span>
            <Server size={12} /> API <Database size={12} /> PostGIS <Waves size={12} /> Redis
          </span>
        </div>
      )}
    </div>
  );
}
