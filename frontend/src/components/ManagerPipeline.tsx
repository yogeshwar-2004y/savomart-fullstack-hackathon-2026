import {
  AlertCircle,
  ArrowRight,
  Building2,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  ClipboardPlus,
  Flag,
  HelpCircle,
  Info,
  LoaderCircle,
  MapPin,
  RefreshCw,
  Sparkles,
  FileText,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { PropertyPinMap } from "./PropertyPinMap";
import { DecisionPackModal } from "./DecisionPackModal";
import {
  changeStage,
  listProperties,
  loadPhoto,
  type PipelineStage,
  type PropertyPhoto,
  type PropertyRecord,
} from "../services/m2";
import { createCatchmentStudy, listCatchmentStudies, type CatchmentStudy } from "../services/m3";

const transitions: Record<PipelineStage, PipelineStage[]> = {
  scouted: ["shortlisted", "rejected"],
  shortlisted: ["survey_requested", "under_review", "rejected"],
  survey_requested: ["under_review", "rejected"],
  under_review: ["approved", "rejected", "shortlisted"],
  approved: [],
  rejected: ["shortlisted"],
};

export const stageExplanations: Record<PipelineStage, { title: string; desc: string }> = {
  scouted: {
    title: "Scouted",
    desc: "A BD Executive submitted a potential property for assessment.",
  },
  shortlisted: {
    title: "Shortlisted",
    desc: "The manager considers it promising enough for further investigation.",
  },
  survey_requested: {
    title: "Survey Requested",
    desc: "The manager wants field evidence about its catchment.",
  },
  under_review: {
    title: "Under Review",
    desc: "The manager is examining the available property and catchment evidence.",
  },
  approved: {
    title: "Approved",
    desc: "The manager has selected the property to advance within this application's decision workflow.",
  },
  rejected: {
    title: "Rejected",
    desc: "The manager has decided not to advance it and records a reason.",
  },
};

export function ManagerPipeline({ view = "pipeline" }: { view?: "pipeline" | "decisions" }) {
  const { propertyId } = useParams();
  const [properties, setProperties] = useState<PropertyRecord[]>([]);
  const [studies, setStudies] = useState<CatchmentStudy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pendingStage, setPendingStage] = useState<PipelineStage | null>(null);
  const [stageReason, setStageReason] = useState("");
  const [stageFilter, setStageFilter] = useState<string>("all");
  const [guideExpanded, setGuideExpanded] = useState(false);
  const [decisionPackOpen, setDecisionPackOpen] = useState(false);

  const selected = useMemo(() => properties.find((item) => item.id === propertyId), [properties, propertyId]);
  const selectedStudy = useMemo(() => studies.find((item) => item.property_id === propertyId), [studies, propertyId]);

  const stageCounts = useMemo(() => {
    const counts: Record<string, number> = {
      all: properties.length,
      scouted: 0,
      shortlisted: 0,
      survey_requested: 0,
      under_review: 0,
      approved: 0,
      rejected: 0,
    };
    for (const p of properties) {
      if (counts[p.stage] !== undefined) {
        counts[p.stage]++;
      }
    }
    return counts;
  }, [properties]);

  const filteredProperties = useMemo(() => {
    return properties.filter((item) => {
      if (view === "decisions" && item.transitions.length <= 1) return false;
      if (stageFilter !== "all" && item.stage !== stageFilter) return false;
      return true;
    });
  }, [properties, view, stageFilter]);

  async function refresh() {
    setLoading(true);
    try {
      const [propItems, studyItems] = await Promise.all([listProperties(), listCatchmentStudies()]);
      setProperties(propItems);
      setStudies(studyItems);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load properties");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function advance() {
    if (!selected || !pendingStage || !stageReason.trim()) return;
    try {
      const updated = await changeStage(selected.id, pendingStage, stageReason.trim());
      setProperties((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      if (pendingStage === "survey_requested") {
        try {
          const study = await createCatchmentStudy("property", selected.id);
          setStudies((items) => [study, ...items.filter((s) => s.id !== study.id)]);
        } catch (studyErr) {
          console.warn("Catchment study auto-creation notice:", studyErr);
        }
      }
      setPendingStage(null);
      setStageReason("");
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Stage change failed");
    }
  }

  async function handleRequestStudy() {
    if (!selected) return;
    try {
      const study = await createCatchmentStudy("property", selected.id);
      setStudies((items) => [study, ...items.filter((s) => s.id !== study.id)]);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not request catchment study");
    }
  }

  return (
    <section className="m2-workspace manager-pipeline">
      <header className="m2-heading">
        <div>
          <span className="eyebrow">M2 Property Operations</span>
          <h2>{view === "decisions" ? "Decisions and Audit History" : selected ? "Property Review & Evidence" : "Property Pipeline"}</h2>
          <p className="heading-sub">
            {view === "decisions"
              ? "Inspect completed property evaluation versions, reason audits, and governance history."
              : selected
              ? "Review property dimensions, rent efficiency, OSM features, and linked catchment evidence."
              : "Review captured sites, track stage progression, and request field survey operations."}
          </p>
        </div>
        <div className="heading-actions">
          <button
            type="button"
            className="secondary-button compact"
            onClick={() => setGuideExpanded((v) => !v)}
            title="Toggle Stage Definitions Guide"
          >
            <HelpCircle size={15} /> <span>Stage Guide</span>
            {guideExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          <button className="icon-button quiet" title="Refresh properties" onClick={refresh}>
            <RefreshCw size={18} />
          </button>
        </div>
      </header>

      {/* Expandable Pipeline Stage Definitions Guide */}
      {guideExpanded ? (
        <div className="stage-guide-box" role="region" aria-label="Pipeline Stage Definitions">
          <div className="stage-guide-header">
            <h4>
              <Info size={16} /> Pipeline Stage Meanings & Workflow Rules
            </h4>
            <small>Deterministic state machine transitions</small>
          </div>
          <div className="stage-guide-grid">
            {Object.entries(stageExplanations).map(([stageKey, item]) => (
              <div key={stageKey} className="stage-guide-card">
                <span className={`stage-chip ${stageKey}`}>{item.title}</span>
                <p>{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {error ? (
        <div className="inline-error" role="alert">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      {loading ? (
        <div className="state-panel">
          <LoaderCircle className="spin" size={24} /> Loading properties pipeline...
        </div>
      ) : null}

      {!loading && !properties.length ? (
        <div className="empty-panel">
          <Building2 size={36} />
          <h3>No properties captured yet</h3>
          <p>Assign a scouting hotspot from Saved Reports to BD Executive to capture on-site properties.</p>
          <Link className="primary-button" to="/manager/reports" style={{ marginTop: "12px" }}>
            View Saved Reports
          </Link>
        </div>
      ) : null}

      {propertyId ? (
        <Link className="secondary-button pipeline-back" to="/manager/properties">
          ← Back to full pipeline
        </Link>
      ) : null}

      {properties.length && !propertyId ? (
        <>
          {/* Stage Filter Bar */}
          <div className="pipeline-filter-bar" role="tablist" aria-label="Filter by stage">
            {[
              { id: "all", label: "All Properties" },
              { id: "scouted", label: "Scouted" },
              { id: "shortlisted", label: "Shortlisted" },
              { id: "survey_requested", label: "Survey Requested" },
              { id: "under_review", label: "Under Review" },
              { id: "approved", label: "Approved" },
              { id: "rejected", label: "Rejected" },
            ].map((tab) => {
              const count = stageCounts[tab.id] ?? 0;
              const isActive = stageFilter === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  className={`pipeline-filter-btn ${isActive ? "active" : ""}`}
                  onClick={() => setStageFilter(tab.id)}
                >
                  <span>{tab.label}</span>
                  <span className="filter-count-badge">{count}</span>
                </button>
              );
            })}
          </div>

          {filteredProperties.length === 0 ? (
            <div className="empty-panel" style={{ padding: "32px 16px" }}>
              <Building2 size={28} />
              <h3>No properties in "{stageFilter.replaceAll("_", " ")}"</h3>
              <p>Select another stage filter above or view All ({stageCounts.all}).</p>
            </div>
          ) : (
            <div className="pipeline-card-grid">
              {filteredProperties.map((item) => {
                const evaluation = item.evaluations.at(-1);
                const drivers = [...(evaluation?.metrics ?? [])]
                  .sort((a, b) => b.contribution - a.contribution)
                  .slice(0, 2);
                const next = transitions[item.stage][0];
                const linkedStudy = studies.find((s) => s.property_id === item.id);

                return (
                  <Link key={item.id} className="pipeline-card" to={`/manager/properties/${item.id}`}>
                    <div className="pipeline-card-top">
                      <span className={`stage-chip ${item.stage}`}>{item.stage.replaceAll("_", " ")}</span>
                      <strong className="pipeline-card-score">
                        {evaluation?.score.toFixed(1) ?? "–"}
                        <small className="score-ver-sub">v{evaluation?.version ?? 1}</small>
                      </strong>
                    </div>

                    <div className="pipeline-card-main">
                      <h3>{item.address}</h3>
                      <p className="pipeline-card-area">
                        {item.area_name} · {item.assignee_name}
                      </p>
                      <small className="pipeline-card-gps">
                        <MapPin size={12} /> {item.latitude.toFixed(5)}, {item.longitude.toFixed(5)}
                      </small>
                    </div>

                    {linkedStudy ? (
                      <div className="pipeline-card-catchment-chip">
                        <span className={`stage-chip compact ${linkedStudy.status}`}>
                          Catchment: {linkedStudy.status.replaceAll("_", " ")} ({linkedStudy.progress_percent.toFixed(0)}%)
                        </span>
                      </div>
                    ) : null}

                    <div className="pipeline-card-evidence">
                      <strong>Leading drivers</strong>
                      {drivers.map((metric) => (
                        <span key={metric.key}>
                          {metric.label} +{metric.contribution.toFixed(1)} · {metric.evidence_kind}
                        </span>
                      ))}
                      <strong>Risk Signal</strong>
                      <span>{evaluation?.risks[0] ?? "No automatic risk threshold triggered"}</span>
                    </div>

                    <footer>
                      <small>
                        Updated {new Date(item.transitions.at(-1)?.created_at ?? item.created_at).toLocaleDateString()}
                      </small>
                      <span>
                        {next ? `Next: ${next.replaceAll("_", " ")}` : "Review history"} <ChevronRight size={16} />
                      </span>
                    </footer>
                  </Link>
                );
              })}
            </div>
          )}
        </>
      ) : null}

      {selected ? (
        <PropertyReview
          key={selected.id}
          property={selected}
          study={selectedStudy}
          onStage={setPendingStage}
          onRequestStudy={handleRequestStudy}
          onOpenDecisionPack={() => setDecisionPackOpen(true)}
        />
      ) : null}

      {selected ? (
        <DecisionPackModal
          property={selected}
          study={selectedStudy}
          isOpen={decisionPackOpen}
          onClose={() => setDecisionPackOpen(false)}
        />
      ) : null}

      {pendingStage ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={() => setPendingStage(null)}>
          <section
            className="decision-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="decision-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <span className="eyebrow">Audited Stage Transition</span>
            <h2 id="decision-title">Move to {pendingStage.replaceAll("_", " ")}</h2>
            <div className="dialog-stage-definition">
              <span className={`stage-chip ${pendingStage}`}>{stageExplanations[pendingStage]?.title}</span>
              <p>{stageExplanations[pendingStage]?.desc}</p>
            </div>
            <p>Record a concise reason for the audit trail. It will remain permanently visible in property history.</p>
            <label htmlFor="stage-reason">Decision Reason</label>
            <textarea
              id="stage-reason"
              autoFocus
              value={stageReason}
              onChange={(event) => setStageReason(event.target.value)}
              rows={4}
              placeholder="Explain the commercial or operational rationale for this decision..."
            />
            <div className="dialog-actions">
              <button
                className="secondary-button"
                type="button"
                onClick={() => {
                  setPendingStage(null);
                  setStageReason("");
                }}
              >
                Cancel
              </button>
              <button
                className="primary-button"
                type="button"
                disabled={!stageReason.trim()}
                onClick={() => void advance()}
              >
                Confirm Stage Transition
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}

function PropertyReview({
  property,
  study,
  onStage,
  onRequestStudy,
  onOpenDecisionPack,
}: {
  property: PropertyRecord;
  study?: CatchmentStudy;
  onStage: (stage: PipelineStage) => void;
  onRequestStudy: () => void;
  onOpenDecisionPack: () => void;
}) {
  const latest = property.evaluations.at(-1);
  const [selectedVersion, setSelectedVersion] = useState(latest?.version ?? 1);
  const evaluation = property.evaluations.find((item) => item.version === selectedVersion) ?? latest;
  const catchmentMetric = evaluation?.metrics.find((metric) => metric.key === "catchment_observations");

  return (
    <article className="property-review">
      <header className="property-review-header">
        <div>
          <span className="eyebrow">
            {property.area_name} · {property.target_label}
          </span>
          <h2>{property.address}</h2>
          <p>
            {property.size_sq_ft.toLocaleString()} sq ft · ₹{property.rent_monthly.toLocaleString("en-IN")}/month ·{" "}
            Scouted by <strong>{property.assignee_name}</strong>
          </p>
        </div>
        <div className="property-header-actions">
          <button
            type="button"
            className="secondary-button highlight-cta"
            onClick={onOpenDecisionPack}
            title="Open printable Leadership Decision Pack"
          >
            <FileText size={16} />
            <span>Export Decision Pack</span>
          </button>
          <div className="property-score">
            <strong>{evaluation?.score.toFixed(1) ?? "–"}</strong>
            <span>{evaluation?.rating}</span>
            <small>
              Version {evaluation?.version} · {evaluation?.scoring_version}
            </small>
          </div>
        </div>
      </header>

      {property.review_flags.length ? (
        <div className="review-flags">
          <Flag size={18} />
          <div>
            <strong>Manager Review Flags</strong>
            {property.review_flags.map((flag) => (
              <p key={flag}>{flag}</p>
            ))}
          </div>
        </div>
      ) : null}

      <div className="review-grid">
        <div>
          <PropertyPinMap
            latitude={property.latitude}
            longitude={property.longitude}
            onChange={() => undefined}
            editable={false}
          />
          <small>
            <MapPin size={13} /> {property.latitude.toFixed(6)}, {property.longitude.toFixed(6)}
          </small>
        </div>
        <div className="property-facts">
          <span>
            <small>Frontage</small>
            <b>{property.frontage_ft ? `${property.frontage_ft} ft` : "Missing"}</b>
          </span>
          <span>
            <small>Road width</small>
            <b>{property.road_width_ft ? `${property.road_width_ft} ft` : "Missing"}</b>
          </span>
          <span>
            <small>Visibility</small>
            <b>{property.visibility_rating}/5</b>
          </span>
          <span>
            <small>Condition</small>
            <b>{property.condition_rating}/5</b>
          </span>
          <span>
            <small>Parking</small>
            <b>{property.parking_available ? "Yes" : "No"}</b>
          </span>
          <span>
            <small>Utilities</small>
            <b>
              {property.power_backup && property.water_available
                ? "Power + Water"
                : property.power_backup
                ? "Power only"
                : property.water_available
                ? "Water only"
                : "Missing"}
            </b>
          </span>
        </div>
      </div>

      {property.photos.length ? (
        <PhotoGallery photos={property.photos} />
      ) : (
        <p className="muted">No property photos were supplied.</p>
      )}

      {/* Version Selector */}
      {property.evaluations.length > 1 ? (
        <section className="evaluation-history" aria-label="Evaluation version history">
          <div>
            <span className="eyebrow">Versioned Evaluation History</span>
            <h3>Compare Evaluation Versions</h3>
          </div>
          <div>
            {property.evaluations.map((item) => (
              <button
                type="button"
                className={item.version === evaluation?.version ? "active" : ""}
                key={item.id}
                onClick={() => setSelectedVersion(item.version)}
              >
                <span>
                  <strong>Version {item.version}</strong>
                  {item.version === latest?.version ? <em>Latest</em> : null}
                </span>
                <b>{item.score.toFixed(1)} pts</b>
                <small>{item.scoring_version}</small>
                <small>{new Date(item.created_at).toLocaleString()}</small>
              </button>
            ))}
          </div>
        </section>
      ) : null}

      {/* Linked Catchment Study Status */}
      {study ? (
        <section className="catchment-evidence" aria-label="Linked Catchment Study">
          <div className="catchment-evidence-flex">
            <div>
              <span className="eyebrow">Linked M3 Catchment Study</span>
              <h3>
                Status: <span className={`stage-chip ${study.status}`}>{study.status.replaceAll("_", " ")}</span>
              </h3>
              <p>
                {study.progress_percent.toFixed(0)}% complete · {study.zones.length} zone(s) ·{" "}
                {study.reuse_coverage.toFixed(0)}% spatial reuse coverage
              </p>
            </div>
            <Link className="primary-button compact" to={`/manager/catchments/${study.id}`}>
              Open Study Details <ChevronRight size={16} />
            </Link>
          </div>
        </section>
      ) : property.stage === "survey_requested" ? (
        <section className="catchment-evidence" aria-label="Request Catchment Study">
          <div className="catchment-evidence-flex">
            <div>
              <span className="eyebrow">Field Survey Handoff</span>
              <h3>Survey Requested</h3>
              <p>Create a 1 km catchment study for Survey Manager to partition zones and collect lane density.</p>
            </div>
            <button className="primary-button" type="button" onClick={onRequestStudy}>
              <ClipboardPlus size={16} /> Request Field Evidence
            </button>
          </div>
        </section>
      ) : null}

      {catchmentMetric ? (
        <section className="catchment-evidence">
          <div>
            <span className="eyebrow">Linked Catchment Insights</span>
            <h3>Field Catchment Observations (Evaluation v{evaluation?.version})</h3>
          </div>
          <strong>
            {catchmentMetric.raw_value?.toFixed(0) ?? "0"} lane observations · {catchmentMetric.contribution.toFixed(2)} points
          </strong>
          <p>
            {catchmentMetric.source} · {new Date(catchmentMetric.fetched_at).toLocaleString()}
          </p>
          <small>
            {catchmentMetric.evidence_kind} evidence · {catchmentMetric.limitations}
          </small>
        </section>
      ) : null}

      {evaluation ? (
        <>
          <div className="decision-summary">
            <div>
              <h3>Recommendation</h3>
              <p>{evaluation.recommendation}</p>
            </div>
            <div>
              <h3>Top Positive Reasons</h3>
              {evaluation.insights.map((item) => (
                <p key={item}>{item}</p>
              ))}
            </div>
            <div>
              <h3>Risk Signals</h3>
              {evaluation.risks.length ? (
                evaluation.risks.map((item) => <p key={item}>{item}</p>)
              ) : (
                <p>No automatic risk threshold was triggered.</p>
              )}
            </div>
          </div>

          <details className="evaluation-ledger" open>
            <summary>Why this property score? (Detailed Metric Provenance)</summary>
            <div className="metric-table">
              <div className="metric-row metric-head">
                <span>Metric</span>
                <span>Raw Value</span>
                <span>Weight</span>
                <span>Points</span>
              </div>
              {evaluation.metrics.map((metric, index) => (
                <details className="metric-row" key={`${metric.key}-${index}`}>
                  <summary>
                    <span>
                      <b>{metric.label}</b>
                      <em>{metric.evidence_kind}</em>
                    </span>
                    <span>{metric.raw_value === null ? "Missing" : `${metric.raw_value.toFixed(2)} ${metric.raw_unit}`}</span>
                    <span>{Math.round(metric.weight * 100)}%</span>
                    <strong>{metric.contribution.toFixed(2)}</strong>
                  </summary>
                  <div className="metric-detail">
                    <p>
                      <b>Source:</b> {metric.source} · {new Date(metric.fetched_at).toLocaleString()}
                    </p>
                    <p>
                      <b>Transformation Rule:</b> {metric.transformation}
                    </p>
                    <p>
                      <b>Limitations:</b> {metric.limitations}
                    </p>
                  </div>
                </details>
              ))}
            </div>
            <div className="limitations">
              <strong>Limitations & Governance Notes</strong>
              {evaluation.limitations.map((item) => (
                <p key={item}>{item}</p>
              ))}
            </div>
          </details>
        </>
      ) : null}

      {/* Stage Actions */}
      <section className="pipeline-actions">
        <div>
          <span className="eyebrow">Current Stage</span>
          <strong className={`stage-chip ${property.stage}`}>{property.stage.replaceAll("_", " ")}</strong>
          <small className="stage-action-desc">{stageExplanations[property.stage]?.desc}</small>
        </div>
        <div className="stage-buttons-group">
          {transitions[property.stage].map((stage) => (
            <button
              key={stage}
              type="button"
              className={stage === "rejected" ? "secondary-button danger" : "primary-button"}
              onClick={() => onStage(stage)}
              title={stageExplanations[stage]?.desc}
            >
              Advance to {stage.replaceAll("_", " ")}
            </button>
          ))}
        </div>
      </section>

      {/* Stage History */}
      <details className="history">
        <summary>Audited Stage History ({property.transitions.length} transitions)</summary>
        {[...property.transitions].reverse().map((item) => (
          <div key={item.id}>
            <b>{item.to_stage.replaceAll("_", " ")}</b>
            <span>
              {item.actor_name} · {new Date(item.created_at).toLocaleString()}
            </span>
            <p>"{item.reason}"</p>
          </div>
        ))}
      </details>
    </article>
  );
}

function PhotoGallery({ photos }: { photos: PropertyPhoto[] }) {
  const [urls, setUrls] = useState<Record<string, string>>({});

  useEffect(() => {
    let active = true;
    const created: string[] = [];
    Promise.all(
      photos.map(async (photo) => {
        const url = await loadPhoto(photo.url);
        created.push(url);
        return [photo.id, url] as const;
      })
    )
      .then((items) => {
        if (active) setUrls(Object.fromEntries(items));
      })
      .catch(() => undefined);
    return () => {
      active = false;
      created.forEach(URL.revokeObjectURL);
    };
  }, [photos]);

  return (
    <div className="photo-gallery">
      {photos.map((photo) =>
        urls[photo.id] ? (
          <img key={photo.id} src={urls[photo.id]} alt={photo.filename} />
        ) : (
          <div key={photo.id} className="photo-loading">
            <LoaderCircle className="spin" />
          </div>
        )
      )}
    </div>
  );
}
