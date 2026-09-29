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
    ogd_pincode_boundaries_path: str | None = None
    chennai_pincode_feature_url: str | None = "https://services7.arcgis.com/8phUg7DrlXpKgLyA/ArcGIS/rest/services/Chennai_MarketVisualization_WFL1/FeatureServer/11"
    location_cache_ttl_seconds: int = 86400
    external_cache_ttl_seconds: int = 3600
    stale_cache_ttl_seconds: int = 604800
    allow_simulated_signal_fallback: bool = True
    store_service_url: str | None = None
    store_service_token: str | None = None
    store_snapshot_path: str | None = "data/savomart_operational_stores.json"
    property_photo_storage_path: str = "storage/property-photos"
    property_photo_max_bytes: int = 5_242_880
    property_nearby_radius_m: int = 750
    property_duplicate_radius_m: int = 75
    property_assignment_distance_m: int = 3000
    catchment_radius_m: int = 1000
    catchment_reuse_max_age_days: int = 90
    catchment_reuse_min_coverage: float = 0.80
    survey_location_tolerance_m: int = 100
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
