from app.db.models import AnalysisJob


class JobRetryError(ValueError):
    pass


def prepare_retry(job: AnalysisJob) -> AnalysisJob:
    if job.status != "failed":
        raise JobRetryError("Only failed jobs can be retried")
    if not job.retryable:
        raise JobRetryError("This failure is not retryable")
    if job.attempts >= 3:
        raise JobRetryError("Retry limit reached")
    job.status = "queued"
    job.progress = 0
    job.status_detail = "Queued for retry"
    job.error_code = None
    job.attempts += 1
    return job
