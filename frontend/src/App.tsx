import { Activity, Database, Server, Waves } from "lucide-react";
import { useEffect, useState } from "react";
import { RoleShell, type RoleId } from "./components/RoleShell";
import { getHealth, type HealthResponse } from "./services/health";

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
          <h1>Chennai expansion workflow foundation</h1>
        </div>
      </header>

      <section className="status-band" aria-label="Service health">
        <div>
          <p className="eyebrow">End-to-end check</p>
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

      <section className="foundation-list" aria-label="Foundation scope">
        <div>
          <Activity size={20} />
          <span>Background jobs and score provenance modules are scaffolded for M1.</span>
        </div>
        <div>
          <Database size={20} />
          <span>PostgreSQL/PostGIS remains the source of truth; Redis is queue and TTL cache only.</span>
        </div>
      </section>
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
