from types import SimpleNamespace

import pytest

from app.jobs.service import JobRetryError, prepare_retry


def test_failed_retryable_job_is_requeued_and_attempt_incremented() -> None:
    job = SimpleNamespace(
        status="failed", retryable=True, attempts=1, progress=45,
        status_detail="provider timeout", error_code="TimeoutError",
    )

    prepare_retry(job)

    assert job.status == "queued"
    assert job.progress == 0
    assert job.attempts == 2
    assert job.error_code is None


@pytest.mark.parametrize(
    "status,retryable,attempts,message",
    [("scoring", True, 1, "Only failed"), ("failed", False, 1, "not retryable"), ("failed", True, 3, "limit")],
)
def test_retry_rejects_invalid_job_state(status: str, retryable: bool, attempts: int, message: str) -> None:
    job = SimpleNamespace(status=status, retryable=retryable, attempts=attempts)
    with pytest.raises(JobRetryError, match=message):
        prepare_retry(job)
