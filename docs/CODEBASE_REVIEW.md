# Codebase Review (Jan 2026)

This document summarizes issues found in the repository, why they matter, and recommended remediations.

## Executive summary

The project is well-structured and the architecture described in README is coherent. The main issues identified are:

- **Networking mismatch:** Home Assistant runs with `network_mode: host`, but multiple docs and n8n workflows referenced `http://homeassistant:8123`, which is not resolvable from other containers.
- **Secrets hygiene:** A `docker/.env` file existed in-repo. Even if it contained placeholders, this is a high-risk pattern (it tends to drift into real credentials).
- **Unsafe defaults:** `docker-compose.yml` had fallback secret defaults (e.g., `changeme`, `your-secret-key-here`) which can lead to accidental insecure deployments.

## Findings and notes

### 1) Container networking / service discovery

**What I found**
- `homeassistant` uses `network_mode: host` in [docker/docker-compose.yml](../docker/docker-compose.yml).
- n8n workflows used URLs like `http://homeassistant:8123/...`.
- README and `docker/.env.template` also suggested `http://homeassistant:8123`.

**Why it matters**
- When a container uses host networking, it does not participate in the compose bridge DNS, so other containers generally cannot resolve `homeassistant`.
- Result is broken tool calls / state reads from n8n to Home Assistant.

**Fix applied**
- Updated n8n workflows to use `http://host.docker.internal:8123`.
- Added `extra_hosts: ["host.docker.internal:host-gateway"]` to `n8n` so this works on Linux too.
- Updated docs and templates to match.

### 2) Secrets and configuration safety

**What I found**
- A `docker/.env` file existed in the repo.
- Compose used insecure fallback defaults:
  - `POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changeme}`
  - `N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY:-your-encryption-key-here}`
  - `WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY:-your-secret-key-here}`

**Why it matters**
- It’s easy to forget to set these, especially in “quick start” paths.
- n8n encryption key stability is critical; changing it can break stored credentials.

**Fix applied**
- Removed `docker/.env` from repo.
- Changed compose env vars to **required** (`${VAR:?message}`) so startup fails fast until configured.

### 3) Cross-platform reality (Windows vs Linux)

**What I found**
- Repo targets Linux for deployment scripts (`deploy.sh`, `update.sh`), but the workspace is on Windows.

**Notes**
- The docker stack can still run on Windows Docker Desktop, but:
  - `network_mode: host` behaves differently on Docker Desktop.
  - `host.docker.internal` is the standard way to reach the host from containers on Docker Desktop.

Recommendation: document the “supported deployment OS” (Linux) explicitly and provide a Windows notes section.

## Risk register (short)

- **High:** Accidental insecure secrets (fixed by required env vars + removing `.env`)
- **Medium:** Host networking dependencies (fixed by host.docker.internal + host-gateway)
- **Medium:** Updates pulling `:latest` images can introduce breaking changes (recommended pinning)

## Next suggested improvements

See [docs/IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md) for a phased roadmap.
