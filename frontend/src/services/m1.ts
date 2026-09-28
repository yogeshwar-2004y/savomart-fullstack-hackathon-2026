export type GeoJSONGeometry = {
  type: "Polygon" | "MultiPolygon";
  coordinates: number[][][] | number[][][][];
};

export type AreaSearchResult = {
  display_name: string;
  selection_method: "locality" | "pincode";
  query: string;
  geometry: GeoJSONGeometry;
  source: string;
  limitations?: string | null;
};

export type Job = {
  id: string;
  analysis_id: string;
  report_id?: string | null;
  status: "queued" | "fetching" | "scoring" | "completed" | "failed";
  progress: number;
  status_detail?: string | null;
  attempts: number;
  error_code?: string | null;
  retryable: boolean;
  updated_at: string;
};

export type Metric = {
  key: string;
  category: string;
  label: string;
  raw_value: number | null;
  raw_unit: string;
  normalized_value: number;
  weight: number;
  contribution: number;
  source_name: string;
  source_url?: string | null;
  fetched_at: string;
  geography: string;
  transformation: string;
  limitations: string;
  evidence_kind: string;
  cache_age_seconds?: number | null;
};

export type Suggestion = {
  rank: number;
  label: string;
  latitude: number;
  longitude: number;
  rationale: string;
  evidence: Record<string, unknown>;
};

export type ReportSummary = {
  id: string;
  area_id: string;
  area_name: string;
  score: number;
  rating: string;
  scoring_version: string;
  created_at: string;
};

export type AreaReport = ReportSummary & {
  analysis_id: string;
  title: string;
  summary: string;
  source_snapshot_at: string;
  used_cached_evidence: boolean;
  cache_age_seconds?: number | null;
  selection_method: string;
  area_sq_km: number;
  geometry: GeoJSONGeometry;
  metrics: Metric[];
  suggestions: Suggestion[];
};

export type Comparison = {
  left: AreaReport;
  right: AreaReport;
  score_delta: number;
  metric_deltas: Record<string, number>;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}/api/v1${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", "X-Demo-Role": "bd-manager", ...options?.headers }
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed with ${response.status}`);
  }
  return response.json();
}

export const searchAreas = (query: string, method: "locality" | "pincode") =>
  request<AreaSearchResult[]>(`/areas/search?q=${encodeURIComponent(query)}&method=${method}`);

export const startAnalysis = (area: { name: string; query?: string; selection_method: string; geometry: GeoJSONGeometry }) =>
  request<{ analysis_id: string; job_id: string; status: Job["status"] }>("/areas/analyses", {
    method: "POST", body: JSON.stringify({ area })
  });

export const getJob = (id: string) => request<Job>(`/jobs/${id}`);
export const retryJob = (id: string) => request<{ job_id: string; status: Job["status"]; attempts: number }>(`/jobs/${id}/retry`, { method: "POST" });
export const listReports = () => request<ReportSummary[]>("/area-reports");
export const getReport = (id: string) => request<AreaReport>(`/area-reports/${id}`);
export const compareReports = (left: string, right: string) => request<Comparison>(`/area-reports/compare?left_id=${left}&right_id=${right}`);
