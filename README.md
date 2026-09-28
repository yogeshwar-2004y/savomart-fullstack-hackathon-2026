# Savo SiteScout

Runnable foundation for the Savomart full-stack hackathon. This first step sets up the repository only: React + TypeScript frontend, FastAPI backend, PostgreSQL/PostGIS, Redis, a Python worker process, migrations, and an end-to-end health check.

The agreed product direction is Approach A: a complete M1 -> M2 -> M3 workflow, with selected additions for score provenance, background-job progress, lightweight survey drafts, and versioned property scores. M1 scoring and later workflows are intentionally not implemented yet.

## Local Startup

1. Copy the local environment template:

   ```bash
   cp .env.example .env
   ```

2. Start all services:

   ```bash
   docker compose up --build
   ```

3. In another terminal, run the initial migration:

   ```bash
   docker compose exec api alembic upgrade head
   ```

4. Open the app:

   ```text
   http://localhost:5173
   ```

5. Verify the API directly:

   ```bash
   curl http://localhost:8000/api/v1/health
   ```

## Services

- `frontend`: React, TypeScript and Vite role-aware shell using Savomart purple `#782B90` and yellow `#FFF200`.
- `api`: FastAPI app with configuration, database engine, Redis connection, and `/api/v1/health`.
- `worker`: separate Python process wired to Redis/RQ for future background M1 analysis jobs.
- `postgres`: PostgreSQL 16 with PostGIS extension.
- `redis`: queue and short-lived external-data cache.

## Module Map

- `backend/app/m1_areas`: future area selection, enrichment jobs, reports, evidence snapshots.
- `backend/app/m2_properties`: future scouting assignments, property intake, evaluations, stage history.
- `backend/app/m3_surveys`: future catchment requests, survey zones, lane captures, draft/idempotency support.
- `backend/app/scoring`: future deterministic scoring versions and score provenance.
- `backend/app/jobs`: Redis queue and durable job progress integration.

## Secrets

Never commit API keys, store-service tokens, LLM keys, or credentials copied from the task brief. Use `.env` locally and deployment secret stores later. The checked-in `.env.example` uses only development placeholders.

## Current Limits

- No M1 scoring, data ingestion, maps, property workflow, or survey workflow yet.
- No auth system yet; the frontend shell uses a role switcher for demo navigation only.
- The health check proves frontend -> backend, backend -> PostgreSQL, and backend -> Redis connectivity.

## AI Usage

This repository was scaffolded with Codex in the Codex desktop app. Future build sessions should be linked or exported under an `ai-sessions/` folder or referenced here before submission.
