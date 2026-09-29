import { apiPhoto, apiRequest } from "./api";

export type Assignee = { id: string; name: string };
export type Assignment = {
  id: string; area_report_id: string; area_name: string; suggestion_id?: string | null;
  target_label: string; latitude: number; longitude: number; assignee_id: string;
  assignee_name: string; status: string; instructions?: string | null; property_id?: string | null; created_at: string;
};
export type EvaluationMetric = {
  key: string; label: string; raw_value: number | null; raw_unit: string; normalized_value: number;
  weight: number; contribution: number; source: string; fetched_at: string; evidence_kind: string;
  transformation: string; limitations: string;
};
export type Evaluation = {
  id: string; version: number; scoring_version: string; score: number; rating: string;
  recommendation: string; metrics: EvaluationMetric[]; insights: string[]; risks: string[];
  limitations: string[]; source_snapshot_at: string; created_at: string;
};
export type PropertyPhoto = { id: string; filename: string; content_type: string; byte_size: number; url: string };
export type PropertyRecord = {
  id: string; assignment_id: string; area_report_id: string; area_name: string; target_label: string;
  assignee_name: string; latitude: number; longitude: number; address: string; rent_monthly: number;
  size_sq_ft: number; frontage_ft?: number | null; road_width_ft?: number | null; property_type: string;
  floor_level: string; visibility_rating: number; condition_rating: number; parking_available: boolean;
  power_backup: boolean; water_available: boolean; notes?: string | null; stage: PipelineStage;
  duplicate_review: boolean; suspicious_gps: boolean; review_flags: string[]; photos: PropertyPhoto[];
  evaluations: Evaluation[]; transitions: { id: string; from_stage?: string | null; to_stage: string; actor_name: string; reason: string; created_at: string }[];
  created_at: string;
};
export type PipelineStage = "scouted" | "shortlisted" | "survey_requested" | "under_review" | "approved" | "rejected";

export const listAssignees = () => apiRequest<Assignee[]>("/scout-assignments/assignees");
export const createAssignment = (data: { area_report_id: string; suggestion_id: string; assignee_id: string; instructions?: string }) =>
  apiRequest<Assignment>("/scout-assignments", { method: "POST", body: JSON.stringify(data) });
export const listAssignments = () => apiRequest<Assignment[]>("/scout-assignments");
export const listProperties = () => apiRequest<PropertyRecord[]>("/properties");
export const getProperty = (id: string) => apiRequest<PropertyRecord>(`/properties/${id}`);
export const changeStage = (id: string, stage: PipelineStage, reason: string) =>
  apiRequest<PropertyRecord>(`/properties/${id}/stage`, { method: "POST", body: JSON.stringify({ stage, reason }) });
export const captureProperty = (assignmentId: string, payload: Record<string, unknown>, photos: File[]) => {
  const form = new FormData();
  form.append("payload", JSON.stringify(payload));
  photos.forEach((photo) => form.append("photos", photo));
  return apiRequest<PropertyRecord>(`/scout-assignments/${assignmentId}/properties`, { method: "POST", body: form });
};
export const loadPhoto = apiPhoto;
