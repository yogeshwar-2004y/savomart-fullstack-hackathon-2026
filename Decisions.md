# Savo SiteScout — Project Decision Reference

**Date:** 28 September 2026  
**Source:** Savomart Full Stack Hackathon brief and our planning discussion  
**Decision:** Build **Approach A**, the focused end-to-end M1–M3 product, with selected ideas from Approach B. Include Redis for background analysis jobs and cached external data. This is the working direction for subsequent design and implementation chats.

**Detailed design:** [ARCHITECTURE.md](ARCHITECTURE.md). Both files describe the agreed plan, not completed implementation.

## Product and example

Savo SiteScout helps Savomart decide **which Chennai area to scout, which property to advance, and whether its catchment supports a store**. The four role-specific users are BD Manager, BD Executive, Survey Manager, and Survey Executive. Use real Chennai geography and Savomart purple `#782B90` and yellow `#FFF200`.

Keep one connected demo story: a BD Manager selects **Velachery** on the map, reviews a saved, timestamped Area Fitness Report and its evidence, then assigns a promising hotspot. A BD Executive visits it, captures GPS, property details, rent and photos on a phone. The system scores the property and records a manager decision. The BD Manager requests a catchment study; the Survey Manager divides and assigns zones; Survey Executives collect lane-level observations. The resulting catchment data updates the property evaluation, with a visible score history and explanation. Velachery is an illustrative scenario, not a claim that its score or a particular property is real.

## Chosen approach and scope

| Priority | Decision |
|---|---|
| Core: M1 | Interactive Chennai area selection; public-data and existing-store enrichment; deterministic, explainable area scoring; saved reports, timestamps and scouting suggestions. |
| Core: M2 | Scouting assignment; mobile GPS/property/photo capture; deterministic property evaluation; manager review, statuses and action history. |
| Core: M3 | Catchment request for a property or analysed area; non-overlapping map-based work split and assignment; mobile lane survey; progress and aggregated results; reuse a sufficiently fresh, overlapping completed study before assigning duplicate work. |
| Selected from B | **Data provenance** behind each metric and a “Why this score?” view; **background-job progress**; **lightweight offline survey drafts**; **versioned property scores** when evidence changes. |
| Deferred | City-wide H3 heatmap, advanced routing/cannibalisation, full offline photo sync and conflict resolution, conversational analyst, PDF exports and other bonuses until the complete loop works. |

## Technical direction

Use **React + TypeScript** for role-specific desktop and mobile interfaces, **FastAPI** for the API and scoring logic, and **PostgreSQL/PostGIS** for properties, zones, reports, stores and spatial queries. Use Leaflet or MapLibre with OpenStreetMap for a real Chennai map. A locality, pincode or selected cells resolve to an analysis polygon; a precomputed city-wide grid is optional. Ingest available public POIs/geocoding and the supplied operational-store data on the server; cache results and label source, query time, geography, transformation, missing signals and any simulated fields. Treat store-service credentials and LLM keys as secrets.

**Redis is included from the start** for two bounded needs: a worker-backed queue for longer M1 enrichment/analysis jobs, and short-lived caching of external results. An analysis request returns a job ID; the UI polls durable job status such as queued → fetching → scoring → completed/failed and offers a retry or eligible cached result. Keep authoritative job progress, reports, assignments, surveys and audit history in Postgres, not Redis. If Redis or an upstream provider fails, show a clear state and preserve existing reports and field drafts.

All numeric scores are computed with documented rules from validated evidence. An optional, swappable LLM receives a structured facts packet only to explain strengths, risks and missing evidence; it never supplies invented statistics or determines the score. The deterministic report remains usable if AI is unavailable.

## Delivery rules for later chats

1. Make the M1 → M2 → M3 loop work before adding extras. Each milestone must be independently demoable and connect to the next.
2. Show source, timestamp, weights, contributions and limitations for important scores. Distinguish real evidence, cached data, missing inputs and demo data.
3. Shape field screens for phones: short forms, large controls, GPS/camera, local draft recovery and clear sync state. Begin with simple draft recovery, not a full offline sync engine.
4. Enforce backend role and object ownership checks; validate coordinates and uploads; isolate secrets; keep an append-only action history; flag suspicious GPS discrepancies for review. Ground and validate AI output.
5. Keep architecture and README honest: state data sources, scoring, trade-offs, known failures, AI usage and session history. Preserve meaningful incremental commits and demonstrate the complete product on real Chennai geography.

**Data structures and algorithms:** relational records; PostGIS points/polygons with spatial indexes; metric evidence records; weighted scoring and hotspot ranking; spatial overlap for catchment reuse; pipeline state transitions; append-only evaluations and action history; Redis queue and TTL cache; local draft and idempotent submission.

**Success criterion:** a reviewer can follow one believable Chennai expansion decision across all four personas, inspect the evidence for every major rating, and complete the workflow even when an optional AI explanation is unavailable.
