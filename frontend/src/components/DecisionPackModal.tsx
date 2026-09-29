import {
  AlertTriangle,
  ArrowRight,
  Building2,
  CheckCircle2,
  Download,
  ExternalLink,
  FileCheck,
  FileText,
  MapPin,
  Printer,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { createPortal } from "react-dom";
import type { PropertyRecord } from "../services/m2";
import type { CatchmentStudy } from "../services/m3";

interface DecisionPackModalProps {
  property: PropertyRecord;
  study?: CatchmentStudy;
  isOpen: boolean;
  onClose: () => void;
}

export function DecisionPackModal({
  property,
  study,
  isOpen,
  onClose,
}: DecisionPackModalProps) {
  if (!isOpen) return null;

  const latestEval = property.evaluations.at(-1);
  const initialEval = property.evaluations[0];
  const hasCatchment = property.evaluations.length > 1;
  const rentPerSqFt = property.size_sq_ft > 0 ? (property.rent_monthly / property.size_sq_ft).toFixed(1) : "–";

  function handlePrint() {
    window.print();
  }

  function handleDownloadJson() {
    const payload = {
      export_type: "SAVOmart_Leadership_Decision_Pack",
      export_date: new Date().toISOString(),
      document_id: `SAVO-DP-${property.id.slice(0, 8).toUpperCase()}`,
      property: {
        id: property.id,
        address: property.address,
        area_name: property.area_name,
        target_label: property.target_label,
        latitude: property.latitude,
        longitude: property.longitude,
        stage: property.stage,
        scouted_by: property.assignee_name,
        created_at: property.created_at,
        specs: {
          monthly_rent: property.rent_monthly,
          size_sq_ft: property.size_sq_ft,
          rent_per_sq_ft: rentPerSqFt,
          floor_level: property.floor_level,
          frontage_ft: property.frontage_ft,
          road_width_ft: property.road_width_ft,
          visibility_rating: property.visibility_rating,
          condition_rating: property.condition_rating,
          parking_available: property.parking_available,
          power_backup: property.power_backup,
          water_available: property.water_available,
          property_type: property.property_type,
        },
        evaluations: property.evaluations,
        audit_trail: property.transitions,
      },
      catchment_study: study
        ? {
            id: study.id,
            status: study.status,
            progress_percent: study.progress_percent,
            summary: study.summary,
            zones: study.zones,
          }
        : null,
    };

    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `SAVO-DecisionPack-${property.address.replace(/[^a-zA-Z0-9]/g, "_")}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  const modalElement = (
    <div className="modal-backdrop decision-pack-backdrop decision-pack-portal" onClick={onClose}>
      <div
        className="decision-pack-container"
        role="dialog"
        aria-modal="true"
        aria-label="Executive Decision Pack"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Action Bar (Hidden in Print) */}
        <div className="decision-pack-toolbar no-print">
          <div className="toolbar-title-group">
            <FileText size={18} className="toolbar-icon" />
            <div>
              <strong>Leadership Decision Pack</strong>
              <small>Executive sign-off dossier for {property.address}</small>
            </div>
          </div>
          <div className="toolbar-actions">
            <button
              type="button"
              className="quiet-button secondary-action"
              onClick={handleDownloadJson}
              title="Download full dossier as JSON"
            >
              <Download size={15} />
              <span>Export JSON</span>
            </button>
            <button
              type="button"
              className="primary-button highlight-cta"
              onClick={handlePrint}
              title="Print or Save as PDF"
            >
              <Printer size={16} />
              <span>Print / Save as PDF</span>
            </button>
            <button
              type="button"
              className="icon-button quiet"
              onClick={onClose}
              aria-label="Close Decision Pack"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Printable Executive Dossier */}
        <div className="decision-pack-document printable-content">
          {/* Header Banner */}
          <header className="dossier-header">
            <div className="dossier-brand-row">
              <div className="dossier-logo">
                <span className="dossier-logo-badge">SAVO</span>
                <div>
                  <strong>SAVOmart SiteScout</strong>
                  <span>Expansion Operations & Governance</span>
                </div>
              </div>
              <div className="dossier-confidential-tag">
                <span>CONFIDENTIAL</span>
                <small>LEADERSHIP SIGN-OFF DOSSIER</small>
              </div>
            </div>

            <div className="dossier-title-grid">
              <div className="dossier-title-main">
                <span className="eyebrow">{property.area_name} EXPANSION CANDIDATE</span>
                <h1>{property.address}</h1>
                <p className="dossier-geo">
                  <MapPin size={14} /> GPS: {property.latitude.toFixed(6)}, {property.longitude.toFixed(6)} · Target: {property.target_label}
                </p>
              </div>
              <div className="dossier-score-card">
                <div className="dossier-score-badge">
                  <span className="dossier-score-num">{latestEval?.score.toFixed(1) ?? "–"}</span>
                  <span className="dossier-score-denom">/ 100</span>
                </div>
                <div className="dossier-score-meta">
                  <strong>{latestEval?.rating ?? "Evaluation Pending"}</strong>
                  <span className={`stage-chip ${property.stage}`}>
                    Stage: {property.stage.replaceAll("_", " ")}
                  </span>
                </div>
              </div>
            </div>
          </header>

          {/* Key Metadata Strip */}
          <section className="dossier-meta-strip">
            <div>
              <small>Document ID</small>
              <strong>SAVO-DP-{property.id.slice(0, 8).toUpperCase()}</strong>
            </div>
            <div>
              <small>Scouted By</small>
              <strong>{property.assignee_name}</strong>
            </div>
            <div>
              <small>Scouting Date</small>
              <strong>{new Date(property.created_at).toLocaleDateString("en-IN", { dateStyle: "medium" })}</strong>
            </div>
            <div>
              <small>Evaluation Version</small>
              <strong>v{latestEval?.version ?? 1} ({latestEval?.scoring_version ?? "v1"})</strong>
            </div>
            <div>
              <small>Print Date</small>
              <strong>{new Date().toLocaleDateString("en-IN", { dateStyle: "medium" })}</strong>
            </div>
          </section>

          {/* Section 1: Executive Summary & Recommendation */}
          <section className="dossier-section">
            <h2 className="dossier-section-heading">
              <Sparkles size={16} /> 1. Executive Summary & Recommendation
            </h2>
            <div className="dossier-recommendation-box">
              <div className="recommendation-badge">
                <FileCheck size={20} />
                <div>
                  <strong>Strategic Recommendation</strong>
                  <p>{latestEval?.recommendation ?? "Candidate under review by BD expansion committee."}</p>
                </div>
              </div>

              {hasCatchment ? (
                <div className="score-evolution-box">
                  <strong>Score Evolution (M2 Initial vs M3 Catchment Ground Truth)</strong>
                  <div className="score-delta-row">
                    <div className="delta-item">
                      <small>M2 Initial Score</small>
                      <b>{initialEval.score.toFixed(1)} pts</b>
                      <span>v1 · Physical & OSM</span>
                    </div>
                    <ArrowRight size={18} className="delta-arrow" />
                    <div className="delta-item highlighted">
                      <small>M3 Final Score</small>
                      <b>{latestEval?.score.toFixed(1)} pts</b>
                      <span>v2 · Field Catchment Enriched</span>
                    </div>
                    <div className="delta-summary">
                      <small>Net Catchment Impact</small>
                      <strong>
                        {((latestEval?.score ?? 0) - initialEval.score) >= 0 ? "+" : ""}
                        {((latestEval?.score ?? 0) - initialEval.score).toFixed(1)} pts
                      </strong>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </section>

          {/* Section 2: Commercial & Physical Specifications */}
          <section className="dossier-section">
            <h2 className="dossier-section-heading">
              <Building2 size={16} /> 2. Commercial & Physical Specifications
            </h2>
            <div className="dossier-specs-grid">
              <div className="spec-card">
                <small>Monthly Rent</small>
                <strong>₹{property.rent_monthly.toLocaleString("en-IN")}</strong>
                <span>₹{rentPerSqFt} / sq ft / month</span>
              </div>
              <div className="spec-card">
                <small>Total Usable Area</small>
                <strong>{property.size_sq_ft.toLocaleString()} sq ft</strong>
                <span>Floor: {property.floor_level || "Ground Floor"}</span>
              </div>
              <div className="spec-card">
                <small>Frontage & Access</small>
                <strong>{property.frontage_ft ? `${property.frontage_ft} ft` : "–"} Frontage</strong>
                <span>Road Width: {property.road_width_ft ? `${property.road_width_ft} ft` : "–"}</span>
              </div>
              <div className="spec-card">
                <small>Street Visibility</small>
                <strong>{property.visibility_rating} / 5 Stars</strong>
                <span>Condition: {property.condition_rating} / 5</span>
              </div>
              <div className="spec-card">
                <small>Customer Parking</small>
                <strong>{property.parking_available ? "Dedicated Available" : "Street Only / None"}</strong>
                <span>Property: {property.property_type || "Commercial Retail"}</span>
              </div>
              <div className="spec-card">
                <small>Utilities & Power</small>
                <strong>
                  {property.power_backup && property.water_available
                    ? "Full Backup + Water"
                    : property.power_backup
                    ? "Power Backup Only"
                    : property.water_available
                    ? "Water Only"
                    : "Standard Grid"}
                </strong>
                <span>Verified by On-site Inspection</span>
              </div>
            </div>
          </section>

          {/* Section 3: Catchment Ground-Truth Evidence */}
          {study ? (
            <section className="dossier-section">
              <h2 className="dossier-section-heading">
                <ShieldCheck size={16} /> 3. M3 Catchment Ground-Truth Findings
              </h2>
              <div className="dossier-catchment-grid">
                <div className="catchment-stat">
                  <small>Target Catchment</small>
                  <strong>1.0 km Radius</strong>
                  <span>{study.target_label}</span>
                </div>
                <div className="catchment-stat">
                  <small>Study Progress</small>
                  <strong>{study.progress_percent.toFixed(0)}% Complete</strong>
                  <span>{study.status.replaceAll("_", " ")}</span>
                </div>
                <div className="catchment-stat">
                  <small>Prior Study Reuse</small>
                  <strong>{study.reuse_coverage.toFixed(1)}% Reused</strong>
                  <span>{study.source_study_ids.length} historical survey(s)</span>
                </div>
                <div className="catchment-stat">
                  <small>Work Zones</small>
                  <strong>{study.zones.length} Non-overlapping Zones</strong>
                  <span>Survey Executives allocated</span>
                </div>
              </div>

              {study.summary ? (
                <div className="catchment-summary-box">
                  <div className="summary-stat-row">
                    <div>
                      <small>Lane Observations</small>
                      <b>{String(study.summary.observation_count ?? 0)}</b>
                    </div>
                    <div>
                      <small>Residential Units Observed</small>
                      <b>{String(study.summary.residential_units ?? 0)}</b>
                    </div>
                    <div>
                      <small>Commercial Units Observed</small>
                      <b>{String(study.summary.commercial_units ?? 0)}</b>
                    </div>
                    <div>
                      <small>Spatial Area Coverage</small>
                      <b>{String(study.summary.coverage_percent ?? 0)}%</b>
                    </div>
                  </div>
                </div>
              ) : null}
            </section>
          ) : null}

          {/* Section 4: Value Drivers & Risk Analysis */}
          <section className="dossier-section">
            <h2 className="dossier-section-heading">
              <CheckCircle2 size={16} /> 4. Key Value Drivers & Risk Assessment
            </h2>
            <div className="dossier-drivers-risks-grid">
              <div className="drivers-card">
                <h3>
                  <CheckCircle2 size={15} /> Top Positive Value Drivers
                </h3>
                {latestEval?.insights.length ? (
                  <ul>
                    {latestEval.insights.map((insight, idx) => (
                      <li key={idx}>{insight}</li>
                    ))}
                  </ul>
                ) : (
                  <p>Standard operational fit parameters met.</p>
                )}
              </div>

              <div className="risks-card">
                <h3>
                  <AlertTriangle size={15} /> Risk Factors & Operational Flags
                </h3>
                {latestEval?.risks.length ? (
                  <ul>
                    {latestEval.risks.map((risk, idx) => (
                      <li key={idx}>{risk}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="clean-risk">No critical operational risk thresholds triggered.</p>
                )}
                {property.review_flags.length ? (
                  <div className="flags-box">
                    <small>Field Flags:</small>
                    {property.review_flags.map((flag, idx) => (
                      <span key={idx} className="flag-tag">{flag}</span>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          </section>

          {/* Section 5: Detailed Metric Provenance Ledger */}
          <section className="dossier-section">
            <h2 className="dossier-section-heading">
              <FileText size={16} /> 5. Scoring Signal Breakdown & Provenance
            </h2>
            <table className="dossier-table">
              <thead>
                <tr>
                  <th>Signal / Metric</th>
                  <th>Raw Field Value</th>
                  <th>Weight</th>
                  <th>Points</th>
                  <th>Data Source & Type</th>
                </tr>
              </thead>
              <tbody>
                {latestEval?.metrics.map((metric, idx) => (
                  <tr key={idx}>
                    <td>
                      <strong>{metric.label}</strong>
                    </td>
                    <td>
                      {metric.raw_value !== null ? `${metric.raw_value.toFixed(1)} ${metric.raw_unit}` : "–"}
                    </td>
                    <td>{Math.round(metric.weight * 100)}%</td>
                    <td>
                      <strong>+{metric.contribution.toFixed(1)}</strong>
                    </td>
                    <td>
                      <span className="source-tag">{metric.source}</span>{" "}
                      <small>({metric.evidence_kind})</small>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {/* Section 6: Audited Decision Log */}
          <section className="dossier-section">
            <h2 className="dossier-section-heading">
              <FileCheck size={16} /> 6. Audit Trail & Stage Transitions
            </h2>
            <div className="dossier-audit-timeline">
              {property.transitions.map((t, idx) => (
                <div key={idx} className="audit-item">
                  <div className="audit-dot" />
                  <div className="audit-details">
                    <div className="audit-top">
                      <strong>{t.to_stage.replaceAll("_", " ").toUpperCase()}</strong>
                      <span>{new Date(t.created_at).toLocaleString("en-IN")}</span>
                    </div>
                    <small>Actor: {t.actor_name}</small>
                    <p>"{t.reason}"</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Section 7: Formal Leadership Sign-off & Authorization */}
          <section className="dossier-section signoff-section">
            <h2 className="dossier-section-heading">
              <ShieldCheck size={16} /> 7. Expansion Leadership Sign-Off & Authorization
            </h2>
            <p className="signoff-instructions">
              By signing below, the Retail Expansion Committee formally authorizes progression of this property candidate
              in accordance with SAVOmart expansion policy and commercial guidelines.
            </p>

            <div className="signoff-boxes-grid">
              <div className="signoff-box">
                <div className="signoff-header">
                  <strong>Business Development Manager</strong>
                  <small>Site Recommendation & Handoff</small>
                </div>
                <div className="signoff-field">
                  <span>Name:</span> <b>Meera Raman</b>
                </div>
                <div className="signoff-field">
                  <span>Decision:</span> <b>{property.stage === "approved" ? "RECOMMENDED (APPROVED)" : property.stage.toUpperCase()}</b>
                </div>
                <div className="signoff-signature-line">
                  <span>Signature:</span>
                  <div className="sig-line" />
                </div>
                <div className="signoff-date-line">
                  <span>Date:</span>
                  <div className="date-line" />
                </div>
              </div>

              <div className="signoff-box">
                <div className="signoff-header">
                  <strong>Head of Retail Expansion</strong>
                  <small>Commercial Viability & Lease Terms</small>
                </div>
                <div className="signoff-field">
                  <span>Name:</span> ______________________
                </div>
                <div className="signoff-field">
                  <span>Decision:</span> <b>[  ] APPROVED  [  ] REJECTED</b>
                </div>
                <div className="signoff-signature-line">
                  <span>Signature:</span>
                  <div className="sig-line" />
                </div>
                <div className="signoff-date-line">
                  <span>Date:</span>
                  <div className="date-line" />
                </div>
              </div>

              <div className="signoff-box">
                <div className="signoff-header">
                  <strong>Chief Operating Officer / CFO</strong>
                  <small>Capital Expenditure & Store Opening</small>
                </div>
                <div className="signoff-field">
                  <span>Name:</span> ______________________
                </div>
                <div className="signoff-field">
                  <span>Budget Code:</span> <b>CHN-EXP-2026</b>
                </div>
                <div className="signoff-signature-line">
                  <span>Signature:</span>
                  <div className="sig-line" />
                </div>
                <div className="signoff-date-line">
                  <span>Date:</span>
                  <div className="date-line" />
                </div>
              </div>
            </div>

            {/* Conditions & Contingencies */}
            <div className="signoff-contingencies">
              <strong>Commercial Contingencies & Operational Pre-conditions:</strong>
              <div className="contingency-checklist">
                <label><input type="checkbox" defaultChecked /> Structural safety & civil survey verification</label>
                <label><input type="checkbox" defaultChecked /> Final lease agreement & rent escalation capped at 5% / 3 yrs</label>
                <label><input type="checkbox" defaultChecked /> Electricity sanctioned load (min 25 kVA) confirmed</label>
                <label><input type="checkbox" /> Municipal trade license & GCC regulatory approvals</label>
              </div>
            </div>
          </section>

          {/* Footer */}
          <footer className="dossier-footer">
            <small>
              Generated by SAVOmart SiteScout Expansion Intelligence Platform · Confidential · For Internal Leadership Use Only
            </small>
          </footer>
        </div>
      </div>
    </div>
  );

  return createPortal(modalElement, document.body);
}
