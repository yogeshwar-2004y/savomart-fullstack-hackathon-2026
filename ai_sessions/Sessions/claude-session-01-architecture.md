# AI Chat Session Log — Claude (Sonnet)

**Project:** Savo SiteScout — Savomart Full Stack Hackathon 2026
**Tool:** Claude (claude.ai, web/desktop chat interface)
**Purpose of this session:** Reviewed the hackathon brief, evaluated two candidate architectural approaches, decided on a stack and design, and produced `docs/ARCHITECTURE.md`.
**Date exported:** 2026-09-29

---

## Message 1 — User

Uploaded `Savomart_FullStack_Hackathon_Task.pdf` (the hackathon brief) and wrote:

> i have a hackathon for the company savomart , the attached document is the documentation of the hackathon and i have readed the document use this for your reference of the context , i have 2 approaches where approach A focus Geospatial points,Weighted scoring and ranking areas and approach b focus on much more complex which use redis and check the approches suits with the project we are building and give your suggestions and stack we czn take fastapi , react , postgres . mostly for example the flow will be like bd manager analyzes Velachery → assigns a promising area → bd executive records a property → system scores it → survey manager assigns catchment surveys → survey rxecutives submit field data → bd manager reviews the updated score and decides , share your though on this

## Message 2 — Claude

Recommended **Approach A** (geospatial points + weighted scoring + ranking) as the core, with Redis treated as an optional later upgrade rather than a starting requirement. Reasoning:

- The brief rewards explainable scoring, a working M1–M3 loop, and grounded AI — a weighted, transparent score fits this better than added infrastructure complexity.
- Redis isn't needed for scoring or caching at Chennai scale; a Postgres-backed `analysis_jobs` table plus FastAPI `BackgroundTasks` covers the "analysis may take a while" requirement from M1 without extra services.
- Proposed stack: FastAPI + SQLAlchemy + GeoAlchemy2, Postgres + PostGIS, React + Vite + MapLibre/Leaflet + Tailwind, OSM/Overpass + Census data ingestion, an LLM behind a swappable provider config, Docker Compose for local run.
- Mapped the user's example flow (BD Manager analyses Velachery → assigns area → BD Executive records property → system scores it → Survey Manager assigns catchment surveys → Survey Executives submit field data → BD Manager reviews updated score) into a concrete data flow: area analysis → scout assignment → property creation → evaluation → catchment study → survey units → lane captures → roll-up re-score → pipeline decision.
- Suggested a scoring shape (area score, property score, confidence that rises with ground-truth survey data) and an hour-by-hour priority plan for the 48-hour window.
- Offered to sketch the PostGIS schema or scoring formula next.

## Message 3 — User

> create a design plan that plan should handle the architecture where the application should be scalable and maintainble and also the design should avoid smells in the code that we are coding

## Message 4 — Claude

Produced a full design plan covering:

1. **Architecture style:** modular monolith (one FastAPI codebase, strict module boundaries, API and worker as separate processes from the same image) instead of microservices, to balance scalability with 48-hour feasibility.
2. **Repository layout:** module-per-domain structure (`identity`, `areas`, `analysis`, `scouting`, `pipeline`, `survey`, `scoring`, `ai`, `ingestion`, `jobs`) with a consistent internal shape (`router`, `schemas`, `service`, `repository`, `models`) in each module.
3. **Data model:** core tables (`grid_cells`, `poi`, `stores`, `area_analyses`, `area_reports`, `analysis_jobs`, `scout_assignments`, `properties`, `property_evaluations`, `stage_transitions`, `catchment_studies`, `survey_units`, `lane_captures`), with append-only versioning for evaluations/reports and JSONB for evolving structured payloads.
4. **Scoring engine:** pure, side-effect-free signal classes with config-driven weights, versioned scoring config, and a confidence value that improves once ground-truth survey data exists.
5. **Grounded AI approach:** LLM only narrates a pre-computed facts payload; a validator rejects any number not present in that payload, with a templated fallback on repeated failure.
6. **Jobs and workflows:** a Postgres-backed job table with `SELECT ... FOR UPDATE SKIP LOCKED`, explicit pipeline and survey-unit state machines, and a concrete reuse rule for catchment studies (overlap and freshness thresholds).
7. **API design principles:** versioned routes, consistent error envelope, cursor pagination, one `require_role` dependency, idempotent field submissions via `client_id`.
8. **Frontend architecture:** feature-folder structure, role-based shell, TanStack Query for server state, an isolated map component, and an offline-draft hook (IndexedDB) for weak-network survey capture.
9. **A code-smell prevention table:** mapping common smells (god service, magic numbers, primitive obsession, shotgun surgery, switch-on-type, swallowed exceptions, hidden global state, etc.) to specific structural choices that prevent them.
10. **Quality gates:** ruff, mypy --strict, eslint, pre-commit, focused unit/integration tests, and a CI workflow.
11. **Trade-offs to state openly** in the README (monolith vs. microservices, Postgres queue vs. Redis, grid cells vs. arbitrary polygons, mocked rent/income data).
12. Mapped the plan back onto the hour-by-hour milestone build order from the earlier response.

Offered to turn this into `docs/ARCHITECTURE.md`, or go deeper on the PostGIS schema or the scoring signal list with starting weights.

## Message 5 — User

> create ARCHITECTURE.md

## Message 6 — Claude

Created `docs/ARCHITECTURE.md` as a complete architecture document, expanding the design plan from Message 4 into a committable Markdown file. Contents:

- Goals and non-goals for v1.
- Persona-to-home-view table.
- System overview diagram (Mermaid `flowchart`): client, API, worker, Postgres/PostGIS, photo storage, and external adapters (Overpass, Stores API, LLM).
- Layering and dependency rules (`api → services → domain ← repositories`, with `ports`/`adapters` for external systems), plus a note to enforce this with `import-linter` in CI.
- Full repository layout for `backend/`, `frontend/`, `scripts/`, `docs/`.
- Data model with an ER diagram (Mermaid `erDiagram`) and a full core-table reference, plus modelling principles (append-only versions, `scoring_version`/`data_snapshot` provenance, JSONB usage, spatial indexing with EPSG:32644 for metre-based distance).
- Spatial strategy: grid cells as the shared unit across area selection, scoring, hotspots, survey splitting, study reuse, and the city-wide bonus map.
- Scoring engine design (pure `Signal` protocol, versioned config, confidence value, mock-data labelling).
- Grounded AI flow diagram: facts payload → prompt builder → LLM → validator → retry → templated fallback.
- Jobs and workflows: job runner state diagram, pipeline state diagram, survey unit lifecycle, reuse-rule function signature, and a full sequence diagram of the end-to-end core loop across all four personas.
- API design conventions, frontend architecture details, and a cross-cutting-concerns table (config, secrets, logging, errors, migrations, data provenance, mock data, external API etiquette).
- Code-smell prevention table, quality gates, a scalability-path table (traffic, job volume, geography, spatial reads, photo storage, city-wide map, multiple LLM providers), a decisions/trade-offs table, known limitations, and a "what we'd do next" section.

File delivered as `/mnt/user-data/outputs/ARCHITECTURE.md` for the user to place at `docs/ARCHITECTURE.md` in the repository. Flagged three follow-ups before committing: the specific numeric thresholds (grid size, duplicate radius, reuse overlap/freshness) are starting points to tune against real data; the CI/lint tooling described should actually be set up or the doc trimmed to match; and the doc references `docs/scoring.md` and `docs/adr/`, which still need to be created.

Offered to draft `docs/scoring.md` (signal list, starting weights, normalisation approach) or the initial PostGIS schema as Alembic migrations next.

## Message 7 — User

> create this chat session file

## Message 8 — Claude

Generated this transcript file (`ai-sessions/claude-session-01-architecture.md`) for the hackathon's AI-disclosure deliverable.

---

## Disclosure notes for the README

- **Tool used:** Claude (Anthropic), web chat interface.
- **How it was used:** brainstorming and evaluating two architectural approaches, deciding on tech stack and data flow, producing the full `ARCHITECTURE.md` design document (module layout, data model, scoring engine design, job/workflow state machines, API and frontend conventions, code-smell prevention table).
- **What was not AI-generated:** actual implementation code, the specific scoring weights tuned against real Chennai data, and any project-specific decisions made after this session (to be logged in further session files as they happen).
- **Human review:** all AI output in this session was reviewed and adapted to the team's judgement before being committed; numeric thresholds and config values are flagged in the architecture doc itself as starting points requiring tuning.
