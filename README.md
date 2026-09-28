# Savo SiteScout

Savo SiteScout is a Chennai expansion workspace for Savomart. This repository currently implements **M1: Area Intelligence**: a BD Manager selects a locality, pincode, or map cells; starts a background analysis; follows durable progress; and revisits or compares saved Area Fitness Reports.

M2 property scouting and M3 catchment operations are intentionally not implemented yet.

## Local startup

Requirements: Docker Desktop with Docker Compose.

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec api alembic upgrade head
```

Open `http://localhost:5173`, keep the demo role set to **BD Manager**, search for `Velachery`, select the result, and click **Start analysis**. The API is at `http://localhost:8000`; interactive API docs are at `http://localhost:8000/docs`.

Useful checks:

```bash
curl http://localhost:8000/api/v1/health
curl "http://localhost:8000/api/v1/areas/search?q=Velachery&method=locality"
docker compose logs -f worker
backend/.venv/bin/python backend/scripts/verify_m1_flow.py
```

Stop with `docker compose down`. Data volumes are retained. Use `docker compose down -v` only when you deliberately want to erase the local database and Redis data.

## M1 flow

- Search Chennai through OpenStreetMap Nominatim by locality or six-digit pincode. Velachery/600042 has a bundled, simplified OSM-derived boundary fallback for offline demos.
- Select one or more 0.01-degree cells directly on the Leaflet map. The selected `MultiPolygon` is validated against Greater Chennai bounds.
- `POST /api/v1/areas/analyses` saves the area and job in PostgreSQL and returns `202 Accepted` with an analysis ID and job ID.
- The Redis/RQ worker records `queued -> fetching -> scoring -> completed` in PostgreSQL. Failures are saved with a useful message and can be retried up to three attempts.
- Reports, metric provenance, suggestions, source snapshots, and geometry are saved in PostgreSQL/PostGIS. Redis is only the queue and short-lived external-response cache.
- Saved reports can be reopened and compared. “Why this score?” exposes raw values, normalization, weight, contribution, source, fetch time, geography, evidence kind, cache age, and limitations.

The demo role header is `X-Demo-Role: bd-manager`. This is intentionally lightweight hackathon access control, not production authentication.

## Data sources and evidence labels

- **OpenStreetMap Nominatim** supplies live locality and pincode search geometry, subject to its usage policy and contributor coverage.
- **OpenStreetMap Overpass API** supplies mapped buildings, shops, offices, amenities, transit features, and competitors inside the selected geometry. The worker filters bounding-box responses against the selected polygon.
- **Savomart operational store service** is supported only when `STORE_SERVICE_URL` and `STORE_SERVICE_TOKEN` are supplied server-side in ignored `.env`. No credentials are committed or exposed to the browser.
- **Bundled demo evidence** keeps the Velachery walkthrough usable if Overpass or the store service is unavailable. It is labeled `demo` in every metric and suggestion. Bundled store points are illustrative, not current operational-store claims.
- **Redis cache** keeps successful OSM responses for one hour and an eligible stale snapshot for seven days. If an upstream failure causes stale evidence to be used, the report is labeled `cached` and shows its age.

OpenStreetMap counts are mapped-feature coverage signals. They are **not** population, household, footfall, income, or complete business counts. M1 records people data as unavailable with zero scoring weight. Residential-building density is labeled as a homes proxy, never converted into people.

## Scoring rules

The deterministic ruleset is versioned as `area-fitness-v1`. Each normalized value is clamped to `0..1`; contribution is `normalized * weight * 100`.

| Signal | Normalization | Weight |
|---|---|---:|
| Mapped residential buildings | `min(features_per_km2 / 60, 1)` | 25% |
| Mapped shops and offices | `min(features_per_km2 / 40, 1)` | 20% |
| Mapped daily-life amenities | `min(features_per_km2 / 20, 1)` | 20% |
| Mapped transit access | `min(features_per_km2 / 25, 1)` | 15% |
| Competition headroom | `1 - min(competitors_per_km2 / 8, 1)` | 10% |
| Savomart coverage gap | `min(nearest_store_km / 5, 1)` | 10% |

If store data is unavailable, coverage gap uses a documented neutral normalized value of `0.5`. Scores are labeled Strong fit (`>=70`), Promising (`>=55`), Needs validation (`>=40`), or Low evidence fit (`<40`). The explanation is generated deterministically from saved evidence; no LLM key or provider is required, and no LLM determines the score.

## Architecture and schema

- `frontend`: React, TypeScript, Vite, React Leaflet, and OpenStreetMap tiles.
- `api`: FastAPI validation, role guard, search, jobs, reports, comparison, and health endpoints.
- `worker`: separate Python RQ process for enrichment and scoring.
- `postgres`: PostgreSQL 16/PostGIS is authoritative for area geometry, job progress, reports, evidence, and source snapshots.
- `redis`: RQ queue plus bounded external-data cache.

Core M1 tables are `areas`, `area_analyses`, `analysis_jobs`, `area_reports`, `area_metric_evidence`, `scouting_suggestions`, and `external_data_snapshots`. Area polygons and suggestion points use SRID 4326 with GiST spatial indexes. See [ARCHITECTURE.md](ARCHITECTURE.md) and [Decisions.md](Decisions.md) for the agreed M1-M3 direction.

## Development checks

```bash
cd backend
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest -q

cd ../frontend
npm install
npm run build
```

## Current limitations

- OSM completeness differs by neighborhood, Overpass can be slow, and pincode boundary availability varies. Retry is explicit; Velachery has the only bundled area/evidence fallback.
- Map cells are geographic squares rather than a city-wide precomputed grid. This is deliberate: there is no mandatory H3 heatmap.
- Straight-line store distance is used instead of routing time. Scouting suggestions are mapped activity clusters that require field validation.
- No approved Census/OGD demographic dataset has been normalized to the selected boundary yet, so people metrics are unavailable and excluded from scoring.
- Demo role switching is not production authentication. M2, M3, advanced cannibalisation, PDF export, full offline sync, and a conversational analyst remain out of scope.

## AI usage

The repository was built with Codex in the Codex desktop app for architecture interpretation, implementation, tests, and documentation. The runtime product does not require or call an LLM. The final submission should add a shared/exported AI session link and demo-video link here when available.
