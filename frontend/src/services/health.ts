export type DependencyStatus = {
  status: "ok" | "error";
  detail?: string | null;
};

export type HealthResponse = {
  status: "ok" | "degraded" | "error";
  service: string;
  database: DependencyStatus;
  redis: DependencyStatus;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${apiBaseUrl}/api/v1/health`);
  if (!response.ok) {
    throw new Error(`Health check failed with ${response.status}`);
  }
  return response.json();
}
