import { apiRequest } from "./api";
import type { GeoJSONGeometry } from "./m1";

export type SurveyAssignee = { id: string; name: string };
export type LaneSubmission = {
  id: string; client_submission_id: string; zone_id: string; lane_name: string;
  suggested_lane_id?: string | null;
  latitude: number; longitude: number; gps_accuracy_m: number; observed_at: string;
  residential_units: number; commercial_units: number; pedestrian_activity: number;
  vehicle_activity: number; notes?: string | null; status: string;
  evidence_kind: "field-survey" | "demo";
  location_mismatch: boolean; mismatch_distance_m: number; created_at: string;
};
export type MappedLaneSuggestion = { id: string; label: string; geometry: { type: "LineString" | "MultiLineString"; coordinates: number[][] | number[][][] }; length_m: number; osm_way_ids: number[]; source: string; fetched_at: string; observed: boolean };
export type SurveyZone = {
  id: string; study_id: string; study_label: string; label: string; geometry: GeoJSONGeometry;
  assignee_id: string; assignee_name: string; status: string; mismatch_review: boolean;
  submission_count: number; submissions: LaneSubmission[]; created_at: string; completed_at?: string | null;
  suggested_lane_ids: string[]; suggested_lanes: MappedLaneSuggestion[];
};
export type CatchmentStudy = {
  id: string; property_id?: string | null; area_report_id?: string | null;
  target_type: "property" | "area_report"; target_label: string;
  target_geometry: GeoJSONGeometry; survey_geometry: GeoJSONGeometry; status: string;
  source_study_id?: string | null; source_study_ids: string[];
  reuse_coverage: number; reuse_age_days?: number | null;
  reuse_max_age_days: number; reuse_min_coverage: number; progress_percent: number;
  summary?: Record<string, unknown> | null; zones: SurveyZone[];
  lane_suggestions: MappedLaneSuggestion[]; lane_suggestions_fetched_at?: string | null; lane_suggestions_error?: string | null;
  created_at: string; completed_at?: string | null;
};

export const createCatchmentStudy = (target_type: "property" | "area_report", target_id: string) =>
  apiRequest<CatchmentStudy>("/catchment-studies", {
    method: "POST", body: JSON.stringify({ target_type, target_id })
  });
export const listCatchmentStudies = () => apiRequest<CatchmentStudy[]>("/catchment-studies");
export const listSurveyAssignees = () => apiRequest<SurveyAssignee[]>("/catchment-studies/assignees");
export const planSurveyZones = (studyId: string, zone_count: number, assignee_ids: string[], included_lane_ids: string[]) =>
  apiRequest<CatchmentStudy>(`/catchment-studies/${studyId}/zones`, {
    method: "POST", body: JSON.stringify({ zone_count, assignee_ids, included_lane_ids })
  });
export const refreshMappedLanes = (studyId: string, force = false) => apiRequest<CatchmentStudy>(`/catchment-studies/${studyId}/lane-suggestions${force ? "?force=true" : ""}`, { method: "POST" });
export const listSurveyZones = () => apiRequest<SurveyZone[]>("/survey-zones");
export const submitLane = (zoneId: string, payload: Record<string, unknown>) =>
  apiRequest<LaneSubmission>(`/survey-zones/${zoneId}/submissions`, {
    method: "POST", body: JSON.stringify(payload)
  });
export const completeSurveyZone = (zoneId: string) =>
  apiRequest<CatchmentStudy>(`/survey-zones/${zoneId}/complete`, { method: "POST" });
