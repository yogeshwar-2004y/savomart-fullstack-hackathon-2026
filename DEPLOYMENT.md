# Savo SiteScout — Render & Production Deployment Guide

This guide describes how to deploy the complete **Savo SiteScout** platform to [Render](https://render.com) using the included `render.yaml` Blueprint or manual service setup.

---

## 1. Turnkey Blueprint Deployment via `render.yaml`

Render automatically detects `render.yaml` at the root of the repository to provision all 5 required services in one click:

1. **PostgreSQL Database** (`sitescout-postgres`): PostgreSQL 16 with PostGIS extensions for spatial queries.
2. **Redis Instance** (`sitescout-redis`): Job queue for RQ background enrichment workers and short-lived caching.
3. **FastAPI Web Service** (`sitescout-api`): Docker-based REST API with health check at `/api/v1/health`.
4. **RQ Background Worker** (`sitescout-worker`): Docker-based background worker executing `app.jobs.worker`.
5. **Static Frontend** (`sitescout-frontend`): High-performance static web app with SPA rewrite rules (`/*` → `/index.html`).

### Steps to Deploy:
1. Push your code to GitHub / GitLab.
2. Log into the [Render Dashboard](https://dashboard.render.com).
3. Click **New +** → **Blueprint**.
4. Connect your GitHub repository (`savo`).
5. Render will parse `render.yaml` and list the 5 services to create. Click **Apply**.
6. Once the database is ready, run initial migration & seed commands from the Render Shell or via Render CLI:
   ```bash
   alembic upgrade head
   python scripts/seed_chennai_data.py
   ```

---

## 2. Environment Variables Reference

### API & Worker Services:
| Variable | Description | Example / Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string with PostGIS | `postgresql+psycopg://user:pass@host:5432/sitescout` |
| `REDIS_URL` | Redis connection string | `redis://host:6379/0` |
| `ENVIRONMENT` | Runtime environment | `production` |
| `CORS_ORIGINS` | Permitted frontend origins | `*` or `https://sitescout.onrender.com` |
| `ALLOW_SIMULATED_SIGNAL_FALLBACK` | Fallback flag if external Overpass is unreachable | `true` |
| `PROPERTY_PHOTO_STORAGE_PATH` | Persistent disk directory for property photos | `/app/storage/property-photos` |

### Frontend Static Site:
| Variable | Description | Example |
|---|---|---|
| `VITE_API_BASE_URL` | URL of the deployed FastAPI backend | `https://sitescout-api.onrender.com` |

---

## 3. PostGIS Verification on Render

To verify PostGIS spatial indexing on your deployed database:
```sql
CREATE EXTENSION IF NOT EXISTS postgis;
SELECT postgis_full_version();
```

---

## 4. Live Health Check

Once deployed, visit your API's health check endpoint:
```bash
curl https://<your-api-domain>.onrender.com/api/v1/health
```

Expected JSON response:
```json
{
  "status": "healthy",
  "database": { "status": "ok" },
  "redis": { "status": "ok" },
  "stores": { "snapshot_stores": 11, "status": "available" }
}
```
