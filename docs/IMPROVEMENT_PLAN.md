# Improvement Plan

This plan is prioritized for reliability and security first, then maintainability and performance.

## Phase 0 — Immediate safety (done)

- Remove in-repo `docker/.env` and require secrets via environment variables.
- Fix Home Assistant reachability from containers (n8n workflows + docker compose host mapping).

Acceptance criteria:
- `docker compose up -d` fails fast if secrets missing.
- n8n can reach HA endpoints (states + service calls) using the configured credential.

## Phase 1 — Reliability and repeatability (1–2 days)

1) Pin container images
- Replace `:latest`/`stable` tags with pinned versions (or a documented update cadence).
- Add a documented update procedure for bumping versions.

Acceptance criteria:
- A fresh deployment today and a fresh deployment next month behave the same (until intentionally updated).

2) Add healthchecks + dependency ordering where missing
- Ensure key user-facing services expose a health endpoint or have an effective probe.
- Convert `depends_on` to include health conditions (Compose v2 supports `condition: service_healthy`).

Acceptance criteria:
- After `docker compose up -d`, services are healthy without manual restarts.

3) Make the HA base URL a single source of truth for n8n
- Use a single env/credential variable in n8n for HA base URL.
- Avoid hardcoded URLs inside workflows.

Acceptance criteria:
- Changing HA URL requires changing it in one place only.

## Phase 2 — Security hardening (1–2 days)

1) Reduce privilege surface
- Reassess `homeassistant: privileged: true` (keep only if required).
- Consider limiting host mounts (`/run/dbus`, etc.) based on hardware needs.

2) Lock down exposed ports
- Only expose what’s needed on LAN; consider binding to `127.0.0.1` for services that should be local.

3) Secrets workflow
- Add a documented secrets policy:
  - how to rotate `POSTGRES_PASSWORD`
  - how to rotate `N8N_ENCRYPTION_KEY` (or why you shouldn’t)

Acceptance criteria:
- Documented hardening steps and a reproducible “secure deployment” configuration.

## Phase 3 — Observability and operations (1 day)

- Add an ops runbook for:
  - common incidents
  - backup/restore
  - how to verify voice pipeline

- Add a minimal “smoke test” script (or extend `health_check.py`) that checks:
  - HA reachable
  - n8n webhook reachable
  - ollama responding
  - whisper/piper Wyoming sockets reachable

Acceptance criteria:
- One command to tell you “the system is healthy enough for voice.”

## Phase 4 — Workflow quality (1–2 days)

- Reduce context payload size from HA state list (currently pulls all `/api/states`).
- Prefer targeted entity queries or cached context snapshot.

Acceptance criteria:
- n8n workflows complete quickly and don’t time out on large HA instances.

## Notes

Effort estimates assume you already have the stack running and can test changes.
