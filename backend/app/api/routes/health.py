from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db.session import engine

router = APIRouter()


class DependencyStatus(BaseModel):
    status: Literal["ok", "error"]
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    database: DependencyStatus
    redis: DependencyStatus


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    database = DependencyStatus(status="ok")
    redis_status = DependencyStatus(status="ok")

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        database = DependencyStatus(status="error", detail=exc.__class__.__name__)

    try:
        client = Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
    except RedisError as exc:
        redis_status = DependencyStatus(status="error", detail=exc.__class__.__name__)

    overall: Literal["ok", "degraded"] = (
        "ok" if database.status == "ok" and redis_status.status == "ok" else "degraded"
    )
    return HealthResponse(
        status=overall,
        service=settings.project_name,
        database=database,
        redis=redis_status,
    )
