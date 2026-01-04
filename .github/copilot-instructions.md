# LCARS Computer – Copilot instructions

## Big picture (what talks to what)
- **Home Assistant = “Body”**: state machine + Assist Pipeline + Wyoming voice stack. Config lives in [homeassistant/config/configuration.yaml](../homeassistant/config/configuration.yaml).
- **n8n = “Nervous system”**: orchestration + “fire-and-forget” workflows. Import/export workflows in [n8n/workflows/](../n8n/workflows/).
- **Open WebUI + Ollama = “Mind”**: local LLM + persona + (optional) RAG. Wired in [docker/docker-compose.yml](../docker/docker-compose.yml).

Voice flow (high level): wake word → Whisper STT → HA Assist → n8n webhook → LLM/tooling → Piper TTS → playback (see [CLAUDE.md](../CLAUDE.md)).

## Critical networking convention (don’t break this)
- On Linux, HA runs `network_mode: host` (see [docker/docker-compose.yml](../docker/docker-compose.yml)), so **other containers cannot reach HA via Docker DNS**.
- Use **`http://host.docker.internal:8123`** for inter-container HA calls (never `http://homeassistant:8123`).
  - n8n workflows should build URLs as `{{$env.HA_URL + '/api/...'}}` (example in [n8n/workflows/voice_command_handler.json](../n8n/workflows/voice_command_handler.json)).
  - HA uses `rest_command` webhooks to n8n at `http://host.docker.internal:5678/...` (see [homeassistant/config/configuration.yaml](../homeassistant/config/configuration.yaml)).
- On Windows and macOS (Docker Desktop), use the bridge-network compose file: [docker/docker-compose.desktop.yml](../docker/docker-compose.desktop.yml).

## Dev workflows (commands this repo expects)
- This repo is **Linux-first** (Docker Engine + Compose plugin). Prefer Linux instructions unless a task explicitly targets Docker Desktop.
- Bring up stack:
  - Linux (primary): `cd docker && docker compose up -d`
  - Windows (Docker Desktop): `cd docker && docker compose -f docker-compose.desktop.yml up -d`
  - macOS (Docker Desktop): `cd docker && docker compose -f docker-compose.desktop.yml up -d`
- Generate secrets/env: `python3 scripts/setup.py --generate-env` (writes `docker/.env`; **never commit** it).
- Health check: `python3 scripts/health_check.py --verbose` (checks containers, ports, endpoints; uses `requests` if installed).
- Backup configs: `python3 scripts/backup.py --compress --output backups --keep 5`.
- Optional interactive installer: `streamlit run lcars_guide.py` (see [lcars_guide.py](../lcars_guide.py); deps in [requirements.txt](../requirements.txt)).

## Home Assistant + tool calling conventions
- LLM “tools” are specified for Extended OpenAI Conversation in [homeassistant/config/extended_openai.yaml](../homeassistant/config/extended_openai.yaml).
  - Specs are `- spec: {name, description, parameters}` + `function:` (often `script`/`template`).
- Reference/tool catalog lives in [prompts/tool_definitions.yaml](../prompts/tool_definitions.yaml).
- Persona is in [prompts/lcars_persona.txt](../prompts/lcars_persona.txt) (concise, 24-hour time, addresses “Commander”, avoids apologies).

## When editing n8n workflows
- Prefer environment-driven URLs (`$env.HA_URL`) and keep the **webhook paths** stable (e.g., `/webhook/voice-command`).
- Keep context injection compact (see “Build LLM Context” code node in [n8n/workflows/voice_command_handler.json](../n8n/workflows/voice_command_handler.json)).

## Repo layout (where to look first)
- Docker stack + env expectations: [docker/docker-compose.yml](../docker/docker-compose.yml)
- Operational commands and gotchas: [docs/OPS_RUNBOOK.md](../docs/OPS_RUNBOOK.md)
- HA main config + n8n webhook wiring: [homeassistant/config/configuration.yaml](../homeassistant/config/configuration.yaml)
