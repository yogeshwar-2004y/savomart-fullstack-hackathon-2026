import { BarChart3, BriefcaseBusiness, Building2, ChevronLeft, ChevronRight, ClipboardCheck, ClipboardList, Database, FileClock, Files, History, LayoutDashboard, MapPinned, Menu, PanelLeftClose, Server, Smartphone, Waves, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import type { HealthResponse } from "../services/health";

export type RoleId = "bd-manager" | "bd-executive" | "survey-manager" | "survey-executive";
type DemoUser = { id: string; name: string };
type NavItem = { to: string; label: string; icon: ReactNode };
type Role = { id: RoleId; label: string; shortLabel: string; focus: string; icon: ReactNode; users: DemoUser[]; navigation: NavItem[] };

export const roleHome: Record<RoleId, string> = {
  "bd-manager": "/manager", "bd-executive": "/executive", "survey-manager": "/survey-manager", "survey-executive": "/survey-executive"
};

export const roles: Role[] = [
  { id: "bd-manager", label: "BD Manager", shortLabel: "BD", focus: "Area intelligence and expansion decisions", icon: <MapPinned size={18} />, users: [{ id: "bd-manager-1", name: "Meera Raman" }], navigation: [
    { to: "/manager", label: "Overview", icon: <LayoutDashboard size={19} /> }, { to: "/manager/areas", label: "Area Intelligence", icon: <MapPinned size={19} /> }, { to: "/manager/reports", label: "Saved Reports", icon: <Files size={19} /> }, { to: "/manager/assignments", label: "Scouting Assignments", icon: <ClipboardCheck size={19} /> }, { to: "/manager/properties", label: "Property Pipeline", icon: <Building2 size={19} /> }, { to: "/manager/catchments", label: "Catchment Requests", icon: <BarChart3 size={19} /> }, { to: "/manager/decisions", label: "Decisions", icon: <History size={19} /> }
  ] },
  { id: "bd-executive", label: "BD Executive", shortLabel: "BD", focus: "Assigned scouting and property capture", icon: <Smartphone size={18} />, users: [{ id: "bd-executive-1", name: "Arun Kumar" }, { id: "bd-executive-2", name: "Kavya Selvan" }], navigation: [
    { to: "/executive", label: "Overview", icon: <LayoutDashboard size={19} /> }, { to: "/executive/assignments", label: "My Scouting Assignments", icon: <ClipboardCheck size={19} /> }, { to: "/executive/submitted", label: "Properties Submitted", icon: <Building2 size={19} /> }
  ] },
  { id: "survey-manager", label: "Survey Manager", shortLabel: "Survey", focus: "Catchment planning, coverage, and results", icon: <BriefcaseBusiness size={18} />, users: [{ id: "survey-manager-1", name: "Priya Natarajan" }], navigation: [
    { to: "/survey-manager", label: "Overview", icon: <LayoutDashboard size={19} /> }, { to: "/survey-manager/requests", label: "Requests Needing Action", icon: <BriefcaseBusiness size={19} /> }, { to: "/survey-manager/progress", label: "Studies in Progress", icon: <BarChart3 size={19} /> }, { to: "/survey-manager/results", label: "Results and History", icon: <History size={19} /> }
  ] },
  { id: "survey-executive", label: "Survey Executive", shortLabel: "Survey", focus: "Assigned zones and lane observations", icon: <ClipboardList size={18} />, users: [{ id: "survey-executive-1", name: "Dinesh Ravi" }, { id: "survey-executive-2", name: "Nila Krishnan" }], navigation: [
    { to: "/survey-executive", label: "Overview", icon: <LayoutDashboard size={19} /> }, { to: "/survey-executive/zones", label: "Assigned Zones", icon: <ClipboardList size={19} /> }, { to: "/survey-executive/drafts", label: "Local Drafts to Restore", icon: <FileClock size={19} /> }
  ] }
];

type RoleShellProps = { activeRole: RoleId; currentUserId: string; health: HealthResponse | null; healthError: string | null; onRoleChange: (role: RoleId) => void; onUserChange: (userId: string) => void; children: ReactNode };

export function RoleShell({ activeRole, currentUserId, health, healthError, onRoleChange, onUserChange, children }: RoleShellProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();
  const selected = roles.find((role) => role.id === activeRole) ?? roles[0];
  const user = selected.users.find((item) => item.id === currentUserId) ?? selected.users[0];
  useEffect(() => setDrawerOpen(false), [location.pathname]);

  return <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
    <a className="skip-link" href="#workspace-content">Skip to workspace</a>
    <header className="mobile-header"><button className="icon-button" type="button" aria-label="Open navigation" onClick={() => setDrawerOpen(true)}><Menu /></button><Brand compact /><span className="mobile-role">{selected.shortLabel}</span></header>
    {drawerOpen ? <button className="drawer-scrim" aria-label="Close navigation" onClick={() => setDrawerOpen(false)} /> : null}
    <aside className={`app-sidebar ${drawerOpen ? "drawer-open" : ""}`} aria-label="Primary navigation">
      <div className="sidebar-brand-row"><Brand compact={collapsed} /><button className="sidebar-close-mobile icon-button" type="button" aria-label="Close navigation" onClick={() => setDrawerOpen(false)}><X /></button></div>
      <div className="identity-card">
        <label htmlFor="demo-role">Demo role</label><div className="select-with-icon">{selected.icon}<select id="demo-role" value={activeRole} onChange={(event) => onRoleChange(event.target.value as RoleId)}>{roles.map((role) => <option key={role.id} value={role.id}>{role.label}</option>)}</select></div>
        <label htmlFor="demo-user">Demo user</label><select id="demo-user" value={user.id} onChange={(event) => onUserChange(event.target.value)}>{selected.users.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
      </div>
      <div className="workspace-label"><span>Current workspace</span><strong>{selected.label}</strong><small>{selected.focus}</small></div>
      <nav className="sidebar-nav">{selected.navigation.map((item) => <NavLink key={item.to} to={item.to} end={item.to === roleHome[activeRole]} title={collapsed ? item.label : undefined}>{item.icon}<span>{item.label}</span></NavLink>)}</nav>
      <div className="sidebar-spacer" /><ServiceHealth health={health} error={healthError} collapsed={collapsed} />
      <button className="sidebar-collapse" type="button" onClick={() => setCollapsed((value) => !value)} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>{collapsed ? <ChevronRight size={18} /> : <><PanelLeftClose size={18} /><span>Collapse sidebar</span><ChevronLeft size={16} /></>}</button>
    </aside>
    <main id="workspace-content" className="workspace-content" tabIndex={-1}>{children}</main>
  </div>;
}

function Brand({ compact = false }: { compact?: boolean }) {
  return <div className="savo-brand" aria-label="Savo SiteScout"><div className="brand-pin"><span>S</span></div>{compact ? null : <div><strong>SAVO</strong><span>SiteScout</span></div>}</div>;
}

function ServiceHealth({ health, error, collapsed }: { health: HealthResponse | null; error: string | null; collapsed: boolean }) {
  const allOk = !error && health?.database.status === "ok" && health?.redis.status === "ok";
  return <div className={`sidebar-health ${allOk ? "healthy" : "unhealthy"}`} title={error ?? "API, PostGIS, and Redis status"}><span className="health-dot" />{collapsed ? null : <div><strong>{allOk ? "Services connected" : error ? "Backend unavailable" : "Checking services"}</strong><span><Server size={12} /> API <Database size={12} /> DB <Waves size={12} /> Queue</span></div>}</div>;
}
