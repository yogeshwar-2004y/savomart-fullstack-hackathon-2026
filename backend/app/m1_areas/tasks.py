from datetime import UTC, datetime, timedelta
from uuid import UUID

from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point
from sqlalchemy import select

from app.db.models import (
    AnalysisJob,
    AreaAnalysis,
    AreaMetricEvidence,
    AreaReport,
    ExternalDataSnapshot,
    ScoutingSuggestion,
)
from app.db.session import SessionLocal
from app.m1_areas.adapters import fetch_osm_signals, fetch_store_signals
from app.m1_areas.data_sources import census_proxy_for_area
from app.scoring.area_v1 import SCORING_VERSION, deterministic_summary, score_area


def _progress(job: AnalysisJob, analysis: AreaAnalysis, status: str, progress: int, detail: str) -> None:
    job.status = status
    job.progress = progress
    job.status_detail = detail
    analysis.status = status


def run_area_analysis(job_id: str) -> str:
    identifier = UUID(job_id)
    db = SessionLocal()
    try:
        job = db.get(AnalysisJob, identifier)
        if not job or not job.analysis_id:
            raise ValueError("Analysis job not found")
        analysis = db.scalar(select(AreaAnalysis).where(AreaAnalysis.id == job.analysis_id))
        if not analysis:
            raise ValueError("Area analysis not found")
        if job.status == "completed":
            return str(job.report_id)
        geometry = to_shape(analysis.area.geometry)
        _progress(job, analysis, "fetching", 20, "Fetching mapped signals and store coverage")
        db.commit()

        osm = fetch_osm_signals(geometry, analysis.area.name)
        stores = fetch_store_signals(geometry)
        population_proxy = census_proxy_for_area(db, str(analysis.area_id))
        _progress(job, analysis, "scoring", 70, f"Applying {SCORING_VERSION}")
        db.commit()

        fetched_at = max(osm.fetched_at, stores.fetched_at)
        provenance = {
            "geography": f"Selected {analysis.area.selection_method} geometry for {analysis.area.name}",
            "osm_source": osm.source, "osm_url": osm.source_url, "osm_kind": osm.evidence_kind,
            "osm_limitations": osm.limitations, "store_source": stores.source,
            "store_kind": stores.evidence_kind, "store_limitations": stores.limitations,
            "cache_age_seconds": osm.cache_age_seconds,
            "store_cache_age_seconds": stores.cache_age_seconds,
        }
        score, rating, metrics = score_area(
            area_sq_km=analysis.area.area_sq_km, counts=osm.counts,
            nearest_store_km=stores.nearest_store_km, provenance=provenance, fetched_at=fetched_at,
            nearby_store_count=stores.nearby_store_count, population_proxy=population_proxy,
        )
        report = AreaReport(
            analysis_id=analysis.id, area_id=analysis.area_id,
            title=f"{analysis.area.name} Area Fitness Report", score=score, rating=rating,
            summary=deterministic_summary(score, rating, metrics), scoring_version=SCORING_VERSION,
            source_snapshot_at=fetched_at, used_cached_evidence=osm.evidence_kind == "cached",
            cache_age_seconds=osm.cache_age_seconds,
        )
        report.metrics = [AreaMetricEvidence(**metric) for metric in metrics]
        selected_hotspots = [candidate for candidate in osm.hotspots if geometry.covers(Point(candidate["lon"], candidate["lat"]))][:3]
        if not selected_hotspots:
            centroid = geometry.centroid
            selected_hotspots = [{"name": "Area centre validation point", "lat": centroid.y, "lon": centroid.x, "signals": 0}]
        report.suggestions = [ScoutingSuggestion(
            rank=index, label=item["name"], point=from_shape(Point(item["lon"], item["lat"]), srid=4326),
            rationale="Scout this mapped activity cluster and validate footfall, rents, visibility, and access on site.",
            evidence={"mapped_signal_strength": item["signals"], "evidence_kind": osm.evidence_kind, "source": osm.source},
        ) for index, item in enumerate(selected_hotspots, start=1)]
        db.add(report)
        if osm.cache_key:
            db.add(ExternalDataSnapshot(
                cache_key=osm.cache_key, source_name=osm.source,
                geography=provenance["geography"],
                payload={"counts": osm.counts, "hotspots": osm.hotspots, "evidence_kind": osm.evidence_kind},
                fetched_at=osm.fetched_at, expires_at=osm.fetched_at + timedelta(days=7),
            ))
        db.flush()
        now = datetime.now(UTC)
        _progress(job, analysis, "completed", 100, "Area Fitness Report saved")
        job.report_id = report.id
        job.retryable = False
        analysis.completed_at = now
        db.commit()
        return str(report.id)
    except Exception as exc:
        db.rollback()
        job = db.get(AnalysisJob, identifier)
        if job:
            job.status = "failed"
            job.progress = 0
            job.status_detail = (
                "OpenStreetMap enrichment is temporarily unavailable. Retry this job; an eligible cached snapshot "
                "will be used automatically."
                if isinstance(exc, RuntimeError) and "OpenStreetMap enrichment failed" in str(exc)
                else "Analysis failed. Retry after checking the worker and external services."
            )
            job.error_code = exc.__class__.__name__
            job.retryable = job.attempts < 3
            if job.analysis_id:
                analysis = db.get(AreaAnalysis, job.analysis_id)
                if analysis:
                    analysis.status = "failed"
            db.commit()
        raise
    finally:
        db.close()
