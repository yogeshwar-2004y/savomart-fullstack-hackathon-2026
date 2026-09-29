import importlib.util
from datetime import UTC, datetime
from pathlib import Path

from app.db.models import OperationalStore, WardCensus

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "seed_chennai_data.py"
SPEC = importlib.util.spec_from_file_location("seed_chennai_data", SCRIPT_PATH)
assert SPEC and SPEC.loader
seed_chennai_data = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(seed_chennai_data)


def test_live_store_refresh_does_not_change_ward_snapshot_date(monkeypatch) -> None:
    records = []

    class Session:
        def merge(self, record) -> None:
            records.append(record)

        def commit(self) -> None:
            pass

        def close(self) -> None:
            pass

    monkeypatch.setattr(seed_chennai_data, "SessionLocal", Session)
    data = seed_chennai_data.DATA_DIR
    wards = data / "gcc_ward_boundaries.geojson"
    seed_chennai_data.seed(
        data / "savomart_operational_stores.json",
        data / "gcc_ward_population_census_2011.csv",
        wards,
        store_payload=[{"store_code": "TEST-001", "name": "Test", "latitude": 12.99, "longitude": 80.21}],
        store_status="live",
    )

    ward = next(record for record in records if isinstance(record, WardCensus))
    store = next(record for record in records if isinstance(record, OperationalStore))
    assert ward.retrieved_at == datetime.fromtimestamp(wards.stat().st_mtime, UTC)
    assert store.retrieved_at >= ward.retrieved_at
