# Savo SiteScout

Savo SiteScout is a Chennai expansion workspace for Savomart. This repository implements the complete **M1 Area Intelligence → M2 Property Scouting → M3 Catchment Study** loop. A BD Manager can carry a real Chennai area from virtual analysis through property scouting, field-survey operations, versioned evaluation, and an audited decision.

## Local startup

Requirements: Docker Desktop with Docker Compose.

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec api alembic upgrade head
```

Open `http://localhost:5173`, keep the demo role set to **BD Manager**, submit a search for `Velachery`, choose an OSM boundary (or an explicitly approximate radius when only a point is returned), and click **Start analysis**. The API is at `http://localhost:8000`; interactive API docs are at `http://localhost:8000/docs`.

For M2, open a saved report and use **Assign** beside a suggested scouting location. Switch to **BD Executive**, open the assignment, correct the map pin, fill the property form, and select **Save and evaluate**. Switch back to **BD Manager** to inspect the property in the pipeline and record a stage decision.

For M3, move a property to `survey_requested`, then use **Request field evidence** as BD Manager. Switch to **Survey Manager** to inspect the target and reuse coverage on the Chennai map, choose 1-8 zones, and assign survey executives. Switch to **Survey Executive** to submit lane observations and complete each zone. The final zone creates a catchment summary, appends a property evaluation version, and returns that property to `under_review`.

Useful checks:

```bash
curl http://localhost:8000/api/v1/health
curl "http://localhost:8000/api/v1/areas/search?q=Velachery&method=locality"
docker compose logs -f worker
backend/.venv/bin/python backend/scripts/verify_m1_flow.py
backend/.venv/bin/python backend/scripts/verify_m2_flow.py
backend/.venv/bin/python backend/scripts/verify_m3_flow.py
```

Stop with `docker compose down`. Data volumes are retained. Use `docker compose down -v` only when you deliberately want to erase the local database and Redis data.

## M1 flow

- Locality search is submitted explicitly to OpenStreetMap Nominatim and cached; there is no search-as-you-type or grid geocoding. OSM polygons retain their `osm_type`, `osm_id`, and category as a stable source ID.
- A Nominatim point is never treated as a boundary. The UI requires a clearly labeled 1, 2, or 3 km approximate PostGIS radius, or a user-selected map area.
- Six-digit PIN searches first inspect the configured Department of Posts OGD boundary file. A matching polygon is labeled official; if it is unavailable, any Nominatim result follows the same polygon/point rules as locality search.
- Select one or more 0.01-degree cells directly on the Leaflet map. The selected `MultiPolygon` is validated against Greater Chennai bounds and receives a stable SHA-256 source ID on the server.
- `POST /api/v1/areas/analyses` saves the area and job in PostgreSQL and returns `202 Accepted` with an analysis ID and job ID.
- The Redis/RQ worker records `queued -> fetching -> scoring -> completed` in PostgreSQL. Failures are saved with a useful message and can be retried up to three attempts.
- Reports, metric provenance, suggestions, source snapshots, and geometry are saved in PostgreSQL/PostGIS. Redis is only the queue and short-lived external-response cache.
- Saved reports can be reopened and compared. “Why this score?” exposes raw values, normalization, weight, contribution, source, fetch time, geography, evidence kind, cache age, and limitations.

Role-scoped requests require both `X-Demo-Role` and `X-Demo-User-Id`. Bundled identities are BD Manager `bd-manager-1`, BD Executives `bd-executive-1` / `bd-executive-2`, Survey Manager `survey-manager-1`, and Survey Executives `survey-executive-1` / `survey-executive-2`. The backend enforces role and assignment ownership; this remains lightweight hackathon identity, not production authentication.

## M2 flow

- `scout_assignments` links a persisted M1 report and scouting suggestion to a named executive. The PostGIS hotspot point is copied as the assignment target so the field handoff remains stable.
- The phone-oriented executive form captures a corrected GPS pin, address, rent, size, frontage, road width, property/floor type, visibility, condition, utilities, notes, and up to eight photos.
- Rent must be greater than zero and no more than INR 10,000,000 per month. Property pins are validated within the configured Chennai bounds (`12.75..13.30` latitude, `80.05..80.35` longitude). Invalid form data and uploads return `422` with field-level details.
- JPEG, PNG, and WebP uploads are limited to 5 MB by default. Pillow inspects actual image content, declared MIME must match, and only server-generated filenames are stored. `PROPERTY_PHOTO_STORAGE_PATH` controls storage; Docker uses a dedicated volume.
- An assignment accepts one property capture. A repeat submission returns `409`; an executive accessing another executive's assignment or property receives `404` so object existence is not disclosed.
- PostGIS checks the property against the assigned M1 area, measures straight-line distance from the hotspot, and searches for a possible duplicate within 75 m. These checks create manager-review flags rather than silently rejecting legitimate field corrections.
- Property evaluation combines field inputs with OpenStreetMap features within 750 m and the configured Savomart store adapter. OSM or store fallback data retains the same live, cached, proxy, and demo labels used by M1.
- Evaluation rows are append-only and uniquely versioned per property. M2 creates version 1; the schema is ready for M3 to append version 2 without overwriting the original decision evidence, but M2 does not create later versions itself.
- Manager stages are `scouted`, `shortlisted`, `survey_requested`, `under_review`, `approved`, and `rejected`. Only documented transitions are accepted with `409` for an illegal move, and each accepted change stores actor, time, previous stage, next stage, and reason. `survey_requested` is the persisted handoff into an M3 request.

## M3 flow

- A BD Manager requests a catchment against a property or saved M1 area report. Property targets use a configurable 1 km PostGIS radius; area targets retain the saved M1 polygon.
- Before work is created, PostGIS finds completed studies intersecting the target. A study no more than **90 days** old and covering at least **80%** of the target is reused immediately. The new record links its source study, age, coverage, summary, and creates no survey zones.
- Partial overlap below 80% is recorded and removed from `survey_geometry`; only the uncovered remainder is assigned. Both thresholds are configurable with `CATCHMENT_REUSE_MAX_AGE_DAYS` and `CATCHMENT_REUSE_MIN_COVERAGE`.
- The Survey Manager reviews target, remaining geometry, reuse provenance, zones, assignments, and progress on OpenStreetMap. The server partitions the remaining polygon into 1-8 clipped, non-overlapping longitudinal work zones and assigns them round-robin to selected executives.
- Survey Executives capture lane/street, point location, GPS accuracy, observation time, residential and commercial unit counts, pedestrian and vehicle activity ratings, and notes. Points outside a zone by more than the greater of reported GPS accuracy or 100 m are retained but flagged for manager review.
- Every lane submission carries a browser-generated UUID. Retrying the same UUID returns the original record rather than creating a duplicate. Executives receive `404` for another executive's zone.
- Incomplete forms autosave to browser `localStorage` per zone, including the submission UUID and corrected map point. Refresh restores the draft. Submitted drafts are removed; this is lightweight recovery, not an offline synchronization engine.
- Completing every zone aggregates timestamped counts, ratings, spatial coverage, mismatch count, source, and limitations. For a property, the system appends evaluation version N+1 and moves `survey_requested` to `under_review` with an audit transition.

## Catchment scoring rules

The catchment ruleset is `property-fitness-v2-catchment`. It scales the previous property's metric weights and contributions to 90%, then adds a 10% field-observed catchment metric. That metric combines residential units per observation (40%), commercial units per observation (25%), pedestrian activity (20%), and vehicle activity (15%), with each component capped at 1. Scripted walkthrough observations are stored and displayed as `demo`; user submissions are `field-survey`. Counts are observations, not census population, household totals, income, or continuous footfall.

## Property scoring rules

The deterministic ruleset is `property-fitness-v1`. Every normalized value is clamped to `0..1`; contribution is `normalized * weight * 100`. No LLM calculates or invents property figures.

| Signal | Normalization | Weight |
|---|---|---:|
| Rent efficiency | `1 - min(rent per sq ft / 150, 1)` | 20% |
| Store size fit | `1.0` for 1,200-3,000 sq ft; `0.6` for 800-4,000; otherwise `0.2` | 15% |
| Frontage | `min(frontage ft / 30, 1)`; missing is `0` | 10% |
| Road access | `min(road width ft / 40, 1)`; missing is `0` | 10% |
| Street visibility | field rating divided by `5` | 10% |
| Property condition | field rating divided by `5` | 7% |
| Access and utilities | parking, backup power, and water available divided by `3` | 8% |
| Nearby mapped activity | `min((shops + amenities + access within 750 m) / 60, 1)` | 10% |
| Competition headroom | `1 - min(mapped competitors within 750 m / 10, 1)` | 5% |
| Savomart coverage gap | `min(nearest store km / 5, 1)`; unavailable uses neutral `0.5` | 5% |

Scores are labeled Strong candidate (`>=70`), Promising (`>=55`), Needs review (`>=40`), or Weak candidate (`<40`). Public mapped features are context signals, not population, footfall, or complete business counts. Field values are self-reported until manager validation. Bundled simulated evidence is visibly labeled and does not become real because it is combined with a real GPS point.

## Data sources and evidence labels

- **OpenStreetMap Nominatim** supplies submitted locality lookup results. Polygon results are labeled `osm-derived`; point results require a radius or map selection. The public endpoint is configurable, results are cached for 24 hours, stale entries can be used for seven days after an upstream failure, and requests identify this application. See the [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/) and [search API](https://nominatim.org/release-docs/latest/api/Search/).
- **OGD India / Department of Posts** is the preferred pincode-boundary source. Download `All India Pincode Boundary Geo JSON` from the [official OGD catalog](https://www.data.gov.in/catalog/all-india-pincode-boundary-geo-json), place the GeoJSON or GeoJSONL file in `backend/data/`, and set `OGD_PINCODE_BOUNDARIES_PATH=/app/data/<filename>`. The source is released under the Government Open Data License - India. The app does not silently substitute a geocoded point for a PIN polygon.
- **Public Chennai pincode feature layer** provides configurable fallback coverage, including `600042`. It is labeled `third-party` and non-official because its publisher metadata does not establish Department of Posts authority. Set `CHENNAI_PINCODE_FEATURE_URL=` to disable it. A configured, matching OGD file always wins.
- **OpenStreetMap Overpass API** supplies mapped buildings, shops, offices, amenities, transit features, and competitors inside the selected geometry. The worker filters bounding-box responses against the selected polygon.
- **Savomart operational store service** is supported only when `STORE_SERVICE_URL` and `STORE_SERVICE_TOKEN` are supplied server-side in ignored `.env`. No credentials are committed or exposed to the browser.
- **Bundled demo evidence** keeps the Velachery scoring walkthrough usable if Overpass or the store service is unavailable. It is labeled `demo/simulated` beside affected values. Bundled store points are illustrative, not current operational-store claims. There is no bundled demo geography fallback.
- **Simulated signal fallback** keeps arbitrary map-cell workflows usable when Overpass and Redis cache are both unavailable. It uses fixed density baselines, is labeled `demo/simulated` on every affected metric, and explicitly says it is not an observation about the selected area. Set `ALLOW_SIMULATED_SIGNAL_FALLBACK=false` to make these jobs fail instead.
- **Redis cache** keeps successful OSM responses for one hour and an eligible stale snapshot for seven days. If an upstream failure causes stale evidence to be used, the report is labeled `cached` and shows its age.

The UI legend distinguishes real geography, real sourced data, proxy data, and demo/simulated data. OpenStreetMap counts are mapped-feature coverage signals. They are **not** population, household, footfall, income, or complete business counts. M1 records people data as unavailable with zero scoring weight. Residential-building density is labeled as a homes proxy, never converted into people. A real boundary does not make simulated business or store inputs real.

## Scoring rules

The deterministic ruleset is versioned as `area-fitness-v1`. Each normalized value is clamped to `0..1`; contribution is `normalized * weight * 100`.

| Signal | Normalization | Weight |
|---|---|---:|
| Mapped residential buildings | `min(features_per_km2 / 60, 1)` | 25% |
| Mapped shops and offices | `min(features_per_km2 / 40, 1)` | 20% |
| Mapped daily-life amenities | `min(features_per_km2 / 20, 1)` | 20% |
| Mapped transit access | `min(features_per_km2 / 25, 1)` | 15% |
| Competition headroom | `1 - min(competitors_per_km2 / 8, 1)` | 10% |
| Savomart coverage gap | `min(nearest_store_km / 3, 1)` | 10% |

If store data is unavailable, coverage gap uses a documented neutral normalized value of `0.5`. Scores are labeled Strong fit (`>=70`), Promising (`>=55`), Needs validation (`>=40`), or Low evidence fit (`<40`). The explanation is generated deterministically from saved evidence; no LLM key or provider is required, and no LLM determines the score.

## Architecture and schema

- `frontend`: React, TypeScript, Vite, React Leaflet, and OpenStreetMap tiles.
- `api`: FastAPI validation, role and ownership guards, area search/jobs/reports, assignments, property capture, image delivery, evaluation, pipeline, and health endpoints.
- `worker`: separate Python RQ process for enrichment and scoring.
- `postgres`: PostgreSQL 16/PostGIS is authoritative for area geometry, job progress, reports, evidence, and source snapshots.
- `redis`: RQ queue plus bounded external-data cache.

Core M1 tables are `areas`, `area_analyses`, `analysis_jobs`, `area_reports`, `area_metric_evidence`, `scouting_suggestions`, and `external_data_snapshots`. M2 adds `scout_assignments`, `properties`, `property_photos`, `property_evaluations`, and `property_stage_transitions`. M3 adds `catchment_studies`, `survey_zones`, and `lane_captures`. Area, catchment, zone, assignment, suggestion, property, and lane geometries use SRID 4326 with GiST spatial indexes. See [ARCHITECTURE.md](ARCHITECTURE.md) and [Decisions.md](Decisions.md) for the agreed design.

## Development checks

```bash
cd backend
.venv/bin/python -m pip install --upgrade 'pip>=26.2'
.venv/bin/pip install -e '.[dev]'
.venv/bin/ruff check app tests scripts
.venv/bin/bandit -r app scripts -q
.venv/bin/pytest -q
.venv/bin/pip-audit

cd ../frontend
npm install
npm run build
npm audit
```

## Current limitations

- OSM locality boundaries reflect contributor coverage and may represent neighborhoods inconsistently. Nominatim point-only results require an explicitly approximate radius or map selection.
- PIN boundaries require a locally configured official OGD file because the OGD portal download flow is not a stable anonymous runtime API. Unsupported or missing PIN polygons are reported rather than invented.
- Location cache entries live for 24 hours; stale cached lookups are eligible for seven days only after an upstream failure, and their age is shown. Overpass signal cache remains one hour with the same seven-day stale ceiling.
- Map cells are geographic squares rather than a city-wide precomputed grid. This is deliberate: there is no mandatory H3 heatmap.
- Straight-line store distance is used instead of routing time. Scouting suggestions are mapped activity clusters that require field validation.
- No approved Census/OGD demographic dataset has been normalized to the selected boundary yet, so people metrics are unavailable and excluded from scoring.
- Demo role switching is not production authentication. Property photos use local/Docker-volume storage rather than production object storage, distances are straight-line rather than routed, and field details are not independently verified.
- M2 performs evaluation during property submission, so a slow public Overpass request can delay the save; the configured cache and labeled demo fallback keep the hackathon walkthrough available. A production deployment should move enrichment to a durable job.
- M3 uses straight longitudinal polygon strips clipped to the target rather than road-network workload balancing. Managers cannot manually redraw vertices in this version.
- Draft recovery is device-local. It does not sync drafts across devices, merge conflicts, cache map tiles, or upload photos offline.
- Completed zones require at least one observation, but this version does not impose a statistically representative lane sample size. Managers must inspect coverage and limitations.
- Advanced cannibalisation, OSRM routing, PDF export, full offline sync, and a conversational analyst remain out of scope.

## AI usage

The repository was built with Codex in the Codex desktop app for architecture interpretation, implementation, tests, and documentation. The runtime product does not require or call an LLM. The final submission should add a shared/exported AI session link and demo-video link here when available.
