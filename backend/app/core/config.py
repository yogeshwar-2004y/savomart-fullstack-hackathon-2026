from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "Savo SiteScout"
    environment: str = "local"
    database_url: str = "postgresql+psycopg://sitescout:sitescout_dev_password@localhost:5432/sitescout"
    redis_url: str = "redis://localhost:6379/0"
    queue_name: str = "sitescout-jobs"
    nominatim_url: str = "https://nominatim.openstreetmap.org"
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    external_cache_ttl_seconds: int = 3600
    stale_cache_ttl_seconds: int = 604800
    store_service_url: str | None = None
    store_service_token: str | None = None
    rq_sync: bool = False
    cors_origins_raw: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias="CORS_ORIGINS",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
