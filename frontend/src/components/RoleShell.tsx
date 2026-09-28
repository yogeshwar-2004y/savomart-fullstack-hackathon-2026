import { BriefcaseBusiness, ClipboardList, MapPinned, Smartphone } from "lucide-react";
import type { ReactNode } from "react";

export type RoleId = "bd-manager" | "bd-executive" | "survey-manager" | "survey-executive";

type Role = {
  id: RoleId;
  label: string;
  focus: string;
  icon: ReactNode;
};

export const roles: Role[] = [
  {
    id: "bd-manager",
    label: "BD Manager",
    focus: "Select Chennai areas, review reports, and request catchment studies.",
    icon: <MapPinned size={18} />
  },
  {
    id: "bd-executive",
    label: "BD Executive",
    focus: "Scout assigned hotspots and capture property details from the field.",
    icon: <Smartphone size={18} />
  },
  {
    id: "survey-manager",
    label: "Survey Manager",
    focus: "Plan catchment work, split zones, assign teams, and track progress.",
    icon: <BriefcaseBusiness size={18} />
  },
  {
    id: "survey-executive",
    label: "Survey Executive",
    focus: "Capture lane observations with simple mobile-friendly draft recovery.",
    icon: <ClipboardList size={18} />
  }
];

type RoleShellProps = {
  activeRole: RoleId;
  onRoleChange: (role: RoleId) => void;
};

export function RoleShell({ activeRole, onRoleChange }: RoleShellProps) {
  const selected = roles.find((role) => role.id === activeRole) ?? roles[0];

  return (
    <section className="role-shell" aria-label="Role workspace">
      <nav className="role-tabs" aria-label="Demo role switcher">
        {roles.map((role) => (
          <button
            className={role.id === activeRole ? "role-tab active" : "role-tab"}
            key={role.id}
            onClick={() => onRoleChange(role.id)}
            type="button"
          >
            {role.icon}
            <span>{role.label}</span>
          </button>
        ))}
      </nav>
      <div className="workspace">
        <div>
          <p className="eyebrow">Current persona</p>
          <h2>{selected.label}</h2>
          <p>{selected.focus}</p>
        </div>
        <div className="workflow-strip" aria-label="Workflow milestones">
          <span>M1 Area Intelligence</span>
          <span>M2 Property Evaluation</span>
          <span>M3 Catchment Operations</span>
        </div>
      </div>
    </section>
  );
}
