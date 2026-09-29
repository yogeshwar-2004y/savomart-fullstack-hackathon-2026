import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  LoaderCircle,
  Map,
  RefreshCw,
  Route,
  Users,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  listCatchmentStudies,
  listSurveyAssignees,
  planSurveyZones,
  refreshMappedLanes,
  type CatchmentStudy,
  type SurveyAssignee,
} from "../services/m3";
import { CatchmentMap } from "./CatchmentMap";

type StudyView = "requests" | "progress" | "results" | "detail";

export function SurveyManagerWorkspace({ view }: { view: StudyView }) {
  const { studyId } = useParams();
  const [studies, setStudies] = useState<CatchmentStudy[]>([]);
  const [assignees, setAssignees] = useState<SurveyAssignee[]>([]);
  const [zoneCount, setZoneCount] = useState(2);
  const [selectedAssignees, setSelectedAssignees] = useState<string[]>([]);
  const [includedLaneIds, setIncludedLaneIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [roadsLoading, setRoadsLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const visible = useMemo(
    () =>
      studies.filter(
        (study) =>
          view === "detail" ||
          (view === "requests" && study.status === "requested") ||
          (view === "progress" && ["assigned", "in_progress"].includes(study.status)) ||
          (view === "results" && ["completed", "reused"].includes(study.status))
      ),
    [studies, view]
  );

  const selected = view === "detail" ? studies.find((item) => item.id === studyId) : undefined;

  async function refresh() {
    setLoading(true);
    try {
      const [items, people] = await Promise.all([listCatchmentStudies(), listSurveyAssignees()]);
      setStudies(items);
      setAssignees(people);
      setSelectedAssignees((current) => (current.length ? current : people.map((item) => item.id)));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load survey operations");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  useEffect(() => {
    if (
      !selected ||
      selected.status !== "requested" ||
      selected.lane_suggestions_fetched_at ||
      selected.lane_suggestions_error ||
      roadsLoading
    )
      return;

    setRoadsLoading(true);
    refreshMappedLanes(selected.id)
      .then((updated) =>
        setStudies((items) => items.map((item) => (item.id === updated.id ? updated : item)))
      )
      .catch(() =>
        setStudies((items) =>
          items.map((item) =>
            item.id === selected.id
              ? {
                  ...item,
                  lane_suggestions_error:
                    "Mapped roads are unavailable. Manual zones remain available.",
                }
              : item
          )
        )
      )
      .finally(() => setRoadsLoading(false));
  }, [
    selected?.id,
    selected?.status,
    selected?.lane_suggestions_fetched_at,
    selected?.lane_suggestions_error,
    roadsLoading,
  ]);

  async function createZones() {
    if (!selected || !selectedAssignees.length) return;
    setSaving(true);
    try {
      const updated = await planSurveyZones(
        selected.id,
        zoneCount,
        selectedAssignees,
        includedLaneIds
      );
      setStudies((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create zones");
    } finally {
      setSaving(false);
    }
  }

  async function retryRoads() {
    if (!selected) return;
    setRoadsLoading(true);
    try {
      const updated = await refreshMappedLanes(selected.id, true);
      setStudies((items) => items.map((item) => (item.id === updated.id ? updated : item)));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Road lookup could not be retried");
    } finally {
      setRoadsLoading(false);
    }
  }

  const requestedCount = studies.filter((s) => s.status === "requested").length;
  const progressCount = studies.filter((s) => ["assigned", "in_progress"].includes(s.status)).length;
  const resultsCount = studies.filter((s) => ["completed", "reused"].includes(s.status)).length;

  const title =
    view === "requests"
      ? "Requests Needing Action"
      : view === "progress"
      ? "Studies in Progress"
      : view === "results"
      ? "Results and History"
      : "Catchment Study Details";

  return (
    <section className="m3-workspace survey-manager-workspace">
      <header className="page-heading">
        <div>
          <p className="eyebrow">M3 Survey Operations</p>
          <h1>{title}</h1>
        </div>
        <button
          className="icon-button quiet"
          title="Refresh studies"
          aria-label="Refresh studies"
          onClick={refresh}
        >
          <RefreshCw size={18} />
        </button>
      </header>

      {view !== "detail" ? (
        <div style={{ display: "flex", gap: "8px", margin: "14px 0", flexWrap: "wrap" }}>
          <Link
            className={view === "requests" ? "primary-button" : "secondary-button"}
            to="/survey-manager/requests"
          >
            Requests ({requestedCount})
          </Link>
          <Link
            className={view === "progress" ? "primary-button" : "secondary-button"}
            to="/survey-manager/progress"
          >
            In Progress ({progressCount})
          </Link>
          <Link
            className={view === "results" ? "primary-button" : "secondary-button"}
            to="/survey-manager/results"
          >
            Results & Reused ({resultsCount})
          </Link>
        </div>
      ) : null}

      {error ? (
        <div className="inline-error" role="alert">
          <AlertCircle size={18} />
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="state-panel">
          <LoaderCircle className="spin" /> Loading studies
        </div>
      ) : null}

      {!loading && !visible.length ? (
        <div className="empty-panel">
          <Map />
          <h2>{view === "detail" ? "Study unavailable" : "No studies here"}</h2>
          <p>
            {view === "requests"
              ? studies.length
                ? `No pending requests. (${progressCount} in progress, ${resultsCount} completed/reused)`
                : "BD Manager requests will appear here for zone planning."
              : view === "progress"
              ? studies.length
                ? `No active surveys in progress. (${requestedCount} pending requests, ${resultsCount} completed/reused)`
                : "Studies with assigned zones will appear here."
              : "Completed and reused catchment studies will appear here."}
          </p>
        </div>
      ) : null}

      {view !== "detail" && !loading ? (
        <div className="study-card-grid">
          {visible.map((study) => (
            <Link
              className="study-card"
              key={study.id}
              to={`/survey-manager/studies/${study.id}`}
            >
              <span className={`stage-chip ${study.status}`}>
                {study.status.replaceAll("_", " ")}
              </span>
              <h2>{study.target_label}</h2>
              <p>
                {study.target_type === "property" ? "Property Catchment" : "Area Catchment"} ·{" "}
                {study.progress_percent.toFixed(0)}% complete
              </p>
              <small>
                {study.reuse_coverage.toFixed(1)}% prior coverage · {study.zones.length} zones
              </small>
              <span>
                Open study <ArrowRight size={16} />
              </span>
            </Link>
          ))}
        </div>
      ) : null}

      {selected ? (
        <div className="study-focus">
          <div className="study-focus-toolbar">
            <Link
              className="secondary-button"
              to={
                selected.status === "requested"
                  ? "/survey-manager/requests"
                  : ["completed", "reused"].includes(selected.status)
                  ? "/survey-manager/results"
                  : "/survey-manager/progress"
              }
            >
              Back to list
            </Link>
            <span className={`stage-chip ${selected.status}`}>
              {selected.status.replaceAll("_", " ")}
            </span>
          </div>

          <div className="study-detail-layout">
            <div className="study-map-column">
              <CatchmentMap
                shapes={[
                  { geometry: selected.target_geometry, color: "#782B90", label: "Target" },
                  { geometry: selected.survey_geometry, color: "#4c155d", label: "Remaining" },
                  ...selected.zones.map((zone) => ({
                    geometry: zone.geometry,
                    color: zone.status === "completed" ? "#16835f" : "#9333ea",
                    label: zone.label,
                  })),
                ]}
                lanes={selected.lane_suggestions.map((lane) => ({
                  ...lane,
                  included:
                    includedLaneIds.includes(lane.id) ||
                    selected.zones.some((zone) => zone.suggested_lane_ids.includes(lane.id)),
                }))}
                surveyPoints={selected.zones.flatMap((zone) =>
                  zone.submissions.map((item) => ({
                    latitude: item.latitude,
                    longitude: item.longitude,
                    flagged: item.location_mismatch,
                  }))
                )}
              />
            </div>

            <article className="study-detail">
              <header>
                <div>
                  <p className="eyebrow">{selected.target_type.replace("_", " ")}</p>
                  <h2>{selected.target_label}</h2>
                </div>
                <strong>{selected.progress_percent.toFixed(0)}%</strong>
              </header>

              <div className="reuse-note">
                <strong>Coverage & Prior Studies</strong>
                <span>
                  {selected.reuse_coverage.toFixed(1)}% covered by prior studies;{" "}
                  {Math.max(0, 100 - selected.reuse_coverage).toFixed(1)}% remained for new work.
                </span>
                <small>
                  Threshold: {selected.reuse_min_coverage.toFixed(0)}% within{" "}
                  {selected.reuse_max_age_days} days.{" "}
                  {selected.source_study_ids.length
                    ? `${selected.source_study_ids.length} source study/studies reused.`
                    : "No eligible prior coverage."}
                </small>
              </div>

              {selected.status === "requested" ? (
                <>
                  <section className="lane-review">
                    <div className="section-heading">
                      <div>
                        <p className="eyebrow">OpenStreetMap road extract</p>
                        <h3>Suggested Mapped Lanes</h3>
                      </div>
                      <Route size={19} />
                    </div>

                    {roadsLoading ? (
                      <div className="state-panel">
                        <LoaderCircle className="spin" /> Finding roads in remaining catchment
                      </div>
                    ) : null}

                    {selected.lane_suggestions_error ? (
                      <div className="reuse-note">
                        {selected.lane_suggestions_error}{" "}
                        <button
                          className="secondary-button compact"
                          type="button"
                          disabled={roadsLoading}
                          onClick={retryRoads}
                        >
                          <RefreshCw size={15} /> Retry lookup
                        </button>
                      </div>
                    ) : null}

                    {selected.lane_suggestions_fetched_at ? (
                      <small>
                        {selected.lane_suggestions.length} suggestions · fetched{" "}
                        {new Date(selected.lane_suggestions_fetched_at).toLocaleTimeString()} · OSM
                        via Overpass
                      </small>
                    ) : null}

                    <div className="lane-choice-list">
                      {selected.lane_suggestions.map((lane) => (
                        <label key={lane.id}>
                          <input
                            type="checkbox"
                            checked={includedLaneIds.includes(lane.id)}
                            onChange={(event) =>
                              setIncludedLaneIds((ids) =>
                                event.target.checked
                                  ? [...ids, lane.id]
                                  : ids.filter((id) => id !== lane.id)
                              )
                            }
                          />
                          <span>
                            <strong>{lane.label}</strong>
                            <small>
                              {lane.length_m.toLocaleString()} m mapped · {lane.osm_way_ids.length}{" "}
                              OSM way{lane.osm_way_ids.length === 1 ? "" : "s"}
                            </small>
                          </span>
                        </label>
                      ))}
                    </div>
                  </section>

                  <section className="zone-planner">
                    <label>
                      Work zones
                      <input
                        type="number"
                        min={1}
                        max={8}
                        value={zoneCount}
                        onChange={(event) => setZoneCount(Number(event.target.value))}
                      />
                    </label>
                    <fieldset>
                      <legend>
                        <Users size={15} /> Assign Survey Executives
                      </legend>
                      {assignees.map((person) => (
                        <label key={person.id}>
                          <input
                            type="checkbox"
                            checked={selectedAssignees.includes(person.id)}
                            onChange={(event) =>
                              setSelectedAssignees((items) =>
                                event.target.checked
                                  ? [...items, person.id]
                                  : items.filter((id) => id !== person.id)
                              )
                            }
                          />
                          {person.name}
                        </label>
                      ))}
                    </fieldset>
                    <button
                      className="primary-button"
                      disabled={!selectedAssignees.length || roadsLoading || saving}
                      onClick={createZones}
                    >
                      {saving ? <LoaderCircle className="spin" size={17} /> : null}
                      Create non-overlapping zones
                    </button>
                  </section>
                </>
              ) : null}

              <section className="zone-progress-list">
                <h3>Assigned Zones</h3>
                {selected.zones.length ? (
                  selected.zones.map((zone) => (
                    <div key={zone.id}>
                      <span className={`stage-chip ${zone.status}`}>
                        {zone.status.replace("_", " ")}
                      </span>
                      <strong>{zone.label}</strong>
                      <small>
                        {zone.assignee_name} · {zone.submission_count} observations ·{" "}
                        {zone.suggested_lane_ids.length} lanes
                      </small>
                      {zone.mismatch_review ? <b>GPS review needed</b> : null}
                    </div>
                  ))
                ) : (
                  <p className="muted">
                    No new zones.{" "}
                    {selected.status === "reused"
                      ? "Recent coverage met the reuse threshold."
                      : "Planning is pending."}
                  </p>
                )}
              </section>

              {selected.lane_suggestions.length && selected.zones.length ? (
                <section className="mapped-lane-status">
                  <h3>Mapped Lane Observations</h3>
                  {selected.lane_suggestions
                    .filter((lane) =>
                      selected.zones.some((zone) => zone.suggested_lane_ids.includes(lane.id))
                    )
                    .map((lane) => (
                      <div key={lane.id}>
                        <span>{lane.label}</span>
                        <strong>
                          {lane.observed ? (
                            <>
                              <CheckCircle2 size={15} /> Observed
                            </>
                          ) : (
                            "Unvisited"
                          )}
                        </strong>
                      </div>
                    ))}
                </section>
              ) : null}

              {selected.summary ? <CatchmentSummary summary={selected.summary} /> : null}
            </article>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function CatchmentSummary({ summary }: { summary: Record<string, unknown> }) {
  return (
    <section className="catchment-summary">
      <h3>Catchment Insights</h3>
      <p>
        <strong>
          {summary.evidence_kind === "demo" ? "Demo / simulated data" : "Field-survey data"}
        </strong>{" "}
        · {String(summary.source ?? "Submitted lane observations")}
      </p>
      <div>
        <span>
          <small>Lane observations</small>
          <b>{String(summary.observation_count ?? 0)}</b>
        </span>
        <span>
          <small>Residential units</small>
          <b>{String(summary.residential_units ?? 0)}</b>
        </span>
        <span>
          <small>Commercial units</small>
          <b>{String(summary.commercial_units ?? 0)}</b>
        </span>
        <span>
          <small>Coverage</small>
          <b>{String(summary.coverage_percent ?? 0)}%</b>
        </span>
      </div>
      <p>{String(summary.limitations ?? "Field observations require manager interpretation.")}</p>
      {summary.previous_score != null && summary.updated_score != null ? (
        <div className="score-change">
          <span>
            Before <b>{Number(summary.previous_score).toFixed(1)}</b>
          </span>
          <ArrowRight size={18} />
          <span>
            After <b>{Number(summary.updated_score).toFixed(1)}</b>
          </span>
          <small>Evaluation v{String(summary.evaluation_version)}</small>
        </div>
      ) : null}
    </section>
  );
}
