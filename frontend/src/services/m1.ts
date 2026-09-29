export type GeoJSONGeometry = {
  type: "Polygon" | "MultiPolygon";
  coordinates: number[][][] | number[][][][];
};

export type GeoJSONPoint = { type: "Point"; coordinates: [number, number] };

export type StoreLocation = {
  store_code: string;
  name: string;
  address?: string | null;
  latitude: number;
  longitude: number;
  source: string;
  source_url?: string | null;
  source_status: string;
  retrieved_at: string;
};

export type GeographyProvenance = {
  source: string;
  source_id: string;
  source_url?: string | null;
  source_license?: string | null;
  boundary_type: "official" | "osm-derived" | "third-party" | "point-only" | "user-selected" | "approximate";
  lookup_at: string;
  is_official: boolean;
  is_approximate: boolean;
  approximation_warning?: string | null;
  resolver_cache_age_seconds?: number | null;
};

export type AreaSearchResult = GeographyProvenance & {
  display_name: string;
  selection_method: "locality" | "pincode";
  query: string;
  geometry: GeoJSONGeometry | GeoJSONPoint;
  cache_age_seconds?: number | null;
  limitations?: string | null;
};

export type AreaSelection = GeographyProvenance & {
  name: string;
  query?: string;
  selection_method: "locality" | "pincode" | "cells" | "radius" | "ward";
  geometry: GeoJSONGeometry;
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
  id: string;
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

export type AreaReport = ReportSummary & Omit<GeographyProvenance, "lookup_at"> & {
  analysis_id: string;
  title: string;
  summary: string;
  source_snapshot_at: string;
  used_cached_evidence: boolean;
  cache_age_seconds?: number | null;
  selection_method: string;
  boundary_lookup_at: string;
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

import { apiRequest as request } from "./api";

export const searchAreas = (query: string, method: "locality" | "pincode") =>
  request<AreaSearchResult[]>(`/areas/search?q=${encodeURIComponent(query)}&method=${method}`);
export const getGccWard = (wardId: number) => request<AreaSelection>(`/areas/wards/${wardId}`);
export const listStores = () => request<StoreLocation[]>("/areas/stores");

export const createApproximateRadius = (result: AreaSearchResult, radius_m: number) =>
  request<AreaSelection>("/areas/approximate-radius", {
    method: "POST", body: JSON.stringify({
      point: result.geometry, radius_m, display_name: result.display_name, query: result.query,
      source_id: result.source_id, source: result.source, source_url: result.source_url,
      source_license: result.source_license, lookup_at: result.lookup_at,
      resolver_cache_age_seconds: result.cache_age_seconds
    })
  });

export const startAnalysis = (area: AreaSelection) =>
  request<{ analysis_id: string; job_id: string; status: Job["status"] }>("/areas/analyses", {
    method: "POST", body: JSON.stringify({ area })
  });

export const getJob = (id: string) => request<Job>(`/jobs/${id}`);
export const retryJob = (id: string) => request<{ job_id: string; status: Job["status"]; attempts: number }>(`/jobs/${id}/retry`, { method: "POST" });
export const listReports = () => request<ReportSummary[]>("/area-reports");
export const getReport = (id: string) => request<AreaReport>(`/area-reports/${id}`);
export const compareReports = (left: string, right: string) => request<Comparison>(`/area-reports/compare?left_id=${left}&right_id=${right}`);
