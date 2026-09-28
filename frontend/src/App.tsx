import { Database, Server, Waves } from "lucide-react";
import { useEffect, useState } from "react";
import { RoleShell, type RoleId } from "./components/RoleShell";
import { getHealth, type HealthResponse } from "./services/health";
import { M1Workspace } from "./components/M1Workspace";

export function App() {
  const [activeRole, setActiveRole] = useState<RoleId>("bd-manager");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then((result) => {
        setHealth(result);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Unable to reach API");
      });
  }, []);

  return (
    <main>
      <header className="topbar">
        <div className="brand-mark">S</div>
        <div>
          <p className="eyebrow">Savo SiteScout</p>
          <h1>Area Scout Intelligence</h1>
        </div>
      </header>

      <section className="status-band" aria-label="Service health">
        <div>
          <p className="eyebrow">Entire check</p>
          <h2>{health ? health.service : "Connecting to backend"}</h2>
        </div>
        <div className="health-grid">
          <HealthPill icon={<Server size={18} />} label="API" status={error ? "error" : "ok"} />
          <HealthPill icon={<Database size={18} />} label="PostGIS" status={health?.database.status ?? "error"} />
          <HealthPill icon={<Waves size={18} />} label="Redis" status={health?.redis.status ?? "error"} />
        </div>
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      <RoleShell activeRole={activeRole} onRoleChange={setActiveRole} />
      {activeRole === "bd-manager" ? <M1Workspace /> : <section className="role-placeholder"><h2>M1 is owned by the BD Manager</h2><p>This milestone implements Area Intelligence only. M2 and M3 remain deliberately out of scope.</p></section>}
    </main>
  );
}

function HealthPill({
  icon,
  label,
  status
}: {
  icon: React.ReactNode;
  label: string;
  status: "ok" | "error";
}) {
  return (
    <div className={`health-pill ${status}`}>
      {icon}
      <span>{label}</span>
      <strong>{status}</strong>
    </div>
  );
}
