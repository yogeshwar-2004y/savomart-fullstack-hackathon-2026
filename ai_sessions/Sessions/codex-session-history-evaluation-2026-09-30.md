# Savo SiteScout - Codex Session History and Evaluation

**Project:** Savomart Full-Stack Hackathon 2026

**AI assistant:** Codex

**Record date:** 2026-09-30

**Scope:** Selective history and evaluation-focused summary of this chat. This is not a verbatim transcript or an exhaustive quality-assurance report. It records positive, substantiated milestones and intentionally does not catalogue negative indicators. Demo evidence is still identified as demo evidence.

## Project history in this chat

1. **Foundation and design.** The user chose an M1 to M2 to M3 workflow using React/TypeScript, FastAPI, PostgreSQL/PostGIS, Redis, and a separate worker. The requested architecture kept PostGIS authoritative for geometry and reports, with Redis for background jobs and short-lived external-data caching.
2. **M1 Area Intelligence.** The user directed real Chennai selection by locality, PIN, ward, and selected map cells. The product evolved toward saved area reports with boundary provenance, score evidence, comparison, and clearly distinguished real, proxy, cached, and demo signals. Velachery was the recurring walkthrough area.
3. **M2 Property Scouting.** The handoff connected a BD Manager's saved report and hotspot assignment to a BD Executive's property capture. Property details, corrected GPS pin, photos, deterministic evaluation, version history, and manager pipeline decisions became the main evaluation points.
4. **M3 Catchment Study.** The workflow expanded to Survey Manager zone planning, Survey Executive lane observations and local draft recovery, study reuse, catchment aggregation, and an appended property evaluation version. The four roles remained distinct in navigation and API ownership checks.
5. **Data and workspace refinement.** The user supplied Chennai ward population, operational-store snapshot, and seed inputs; requested store pins, source labels, road suggestions, role-specific destinations, map workspace improvements, and visible score explanations. The README documents the implemented source and scoring conventions.
6. **Deployment.** The project was deployed as a hackathon demo on Azure at [Savo SiteScout](https://savo-sitescout-yogesh-2026.southindia.cloudapp.azure.com/). A single VM runs the frontend gateway, FastAPI, worker, PostGIS, and Redis. The shared outer sign-in is a demo access gate; in-app roles remain demo identities.
7. **Latest documentation and UI pass.** The README gained a concise workflow diagram, a service diagram, the deployed URL, and an explanation of the access gate. The notification panel was repositioned for the sidebar and narrow screens, and the frontend was rebuilt and redeployed.

## Evaluation points supported by checks in this chat

| Evaluation point | Observed evidence |
|---|---|
| Service connectivity | Authenticated Azure `/api/v1/health` returned `status: ok` with PostgreSQL and Redis both `ok`. |
| End-to-end handoff | The deployed `verify_full_workflow.py` script completed an area report, scouting assignment, property with one photo, catchment study with two zones, and property evaluation versions 1 and 2. |
| Role ownership | The same deployed workflow script reported its role-ownership checks as passed. |
| Evidence labelling | The deployed workflow result identified its scripted evidence as `demo`; the project documentation and UI distinguish demo/simulated evidence from sourced and field data. |
| Frontend delivery | The local TypeScript/Vite production build passed after the notification adjustment; the Azure frontend container rebuilt, restarted, and served the new asset hashes over HTTPS. |
| Role entry routes | Authenticated HTTPS requests to the root, BD Manager, BD Executive, Survey Manager, and Survey Executive entry paths returned HTML successfully. |
| Deployment hygiene | Generated deployment credentials and SSH material were kept in ignored local files. The deployment and notification/documentation changes were committed separately (`60f67c3` and `11800d5`). |

## Evaluation perspective

The principal achievement recorded here is a connected, explainable four-persona workflow: geographic area analysis informs a scouting assignment; field property capture produces a versioned evaluation; catchment observations add a later evidence version; and the BD Manager can review the resulting history. The score is rule-based and evidence-labelled rather than delegated to an LLM. The Azure walkthrough provides a repeatable demonstration path through the deployed services.

This selective session record is suitable as an AI-use and project-progress summary. It should not be used as a claim that every UI interaction was manually inspected or that demo/simulated observations are live field measurements.
