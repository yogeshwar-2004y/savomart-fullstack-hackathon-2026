from redis import Redis
from rq import Queue

from app.core.config import get_settings


def get_queue() -> Queue:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url)
    return Queue(settings.queue_name, connection=redis, is_async=not settings.rq_sync)


def enqueue_area_analysis(job_id: str, attempt: int = 1) -> None:
    get_queue().enqueue(
        "app.m1_areas.tasks.run_area_analysis",
        job_id,
        job_id=f"area-analysis-{job_id}-attempt-{attempt}",
        job_timeout=180,
        result_ttl=86400,
    )
