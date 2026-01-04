# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The LCARS Computer is a Star Trek-inspired, self-hosted voice assistant that integrates Home Assistant (state machine), Open WebUI/Ollama (LLM inference), and n8n (workflow orchestration) to create a privacy-first, locally-run voice automation system.

## System Architecture

The system follows a **Separation of Concerns** pattern with three primary layers:

1. **Home Assistant** ("The Body"): Manages device states, handles Wyoming protocol voice satellites, and routes conversations to the LLM via Extended OpenAI Conversation integration
2. **n8n** ("The Nervous System"): Orchestrates complex workflows, implements the fire-and-forget pattern for long-running tasks, and bridges Home Assistant with the LLM
3. **Open WebUI + Ollama** ("The Mind"): Runs local LLM models with RAG capabilities and maintains the LCARS persona

### Key Integration Points

- **Home Assistant uses `network_mode: host`** in docker-compose.yml for device discovery (Zigbee, mDNS, Bluetooth)
- **n8n and other services cannot resolve `homeassistant` hostname** because host-networked containers don't participate in Docker bridge DNS
- **All inter-container communication to Home Assistant uses `http://host.docker.internal:8123`**
- **n8n has `extra_hosts: ["host.docker.internal:host-gateway"]`** to make this work on Linux (Docker Desktop provides this automatically on Windows/macOS)

### Voice Pipeline Flow

1. Voice satellite detects wake word "Computer" via openWakeWord
2. Audio streams to Whisper (faster-whisper) for STT
3. Text forwarded to Home Assistant's Assist Pipeline
4. Extended OpenAI Conversation routes to n8n webhook
5. n8n fetches device states and calls Open WebUI with LCARS persona
6. LLM generates response and executes Home Assistant tools
7. Piper synthesizes TTS audio with computer voice
8. Response plays on satellite speaker

## Development Commands

### Docker Stack Management

```bash
# Start all services (Linux with Docker Engine)
cd docker
docker compose up -d

# Start with GPU support
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

# Windows/macOS with Docker Desktop (no host networking support)
docker compose -f docker-compose.desktop.yml up -d

# View logs
docker compose logs -f [service_name]

# Restart a service
docker compose restart [service_name]

# Stop all services
docker compose down
```

### Deployment and Setup

```bash
# Automated deployment (Linux only)
./scripts/deploy.sh [--gpu] [--dev] [--no-pull]

# Generate secure .env file
python3 scripts/setup.py --generate-env

# System health check
python3 scripts/health_check.py [--verbose] [--json]

# Backup configurations
python3 scripts/backup.py

# Update all containers
./scripts/update.sh
```

### Ollama Model Management

```bash
# Pull a model
docker exec LCARS-ollama ollama pull llama3.1:8b

# List installed models
docker exec LCARS-ollama ollama list

# Remove a model
docker exec LCARS-ollama ollama rm model_name
```

### Home Assistant

```bash
# Check configuration validity
docker exec LCARS-homeassistant hass --script check_config

# Restart Home Assistant
docker compose restart homeassistant

# View Home Assistant logs
docker compose logs -f homeassistant
```

## Critical Configuration Details

### Environment Variables

The `docker/.env` file is **NOT committed to the repository** and must be generated:

- `POSTGRES_PASSWORD`: Database password for n8n
- `N8N_ENCRYPTION_KEY`: Critical for n8n credential storage (changing this breaks stored credentials)
- `WEBUI_SECRET_KEY`: Open WebUI session encryption
- `HA_ACCESS_TOKEN`: Home Assistant Long-Lived Access Token (added after HA initial setup)
- `TIMEZONE`: System timezone (e.g., `America/New_York`)

All required environment variables use `${VAR:?message}` syntax in docker-compose.yml, causing startup to fail if missing.

### Networking Architecture

**Critical**: Home Assistant's `network_mode: host` means:
- It cannot be reached at `http://homeassistant:8123` from other containers
- Must use `http://host.docker.internal:8123` instead
- Works on Linux because n8n has `extra_hosts` mapping
- n8n workflows read `HA_URL` environment variable (defaults to `http://host.docker.internal:8123`)

### Service Endpoints

- Home Assistant: `http://localhost:8123`
- n8n: `http://localhost:5678`
- Open WebUI: `http://localhost:3000`
- Ollama API: `http://localhost:11434`
- Whisper (Wyoming): `tcp://localhost:10300`
- Piper (Wyoming): `tcp://localhost:10200`
- openWakeWord (Wyoming): `tcp://localhost:10400`

## LCARS Persona Implementation

The LCARS persona is defined in `prompts/lcars_persona.txt` and should be configured in Open WebUI as a system prompt. Key characteristics:

- Logical, concise, professional responses
- Uses 24-hour time format ("1400 hours")
- Addresses user as "Commander"
- Acknowledgments: "Affirmative", "Acknowledged", "Processing", "Task complete"
- Never uses phrases like "I'm sorry, but..." or "As an AI language model..."
- Presents data in structured format with headers like `[SYSTEM]`, `[STATUS]`, `[DETAILS]`

## Extended OpenAI Conversation Tools

Tools (function definitions) are defined in `homeassistant/config/extended_openai.yaml` under the "spec" format. These allow the LLM to:

- Control lights, climate, locks, media players
- Query entity states and sensor data
- Activate scenes and scripts
- Get comprehensive ship status reports
- Trigger Red Alert protocol
- Make announcements via TTS
- Call n8n workflows for complex tasks

Each tool spec has:
- `name`: Function identifier
- `description`: What the function does
- `parameters`: JSON schema for arguments
- `function`: Either `script`, `template`, or `rest_command` type

## n8n Workflows

Core workflows in `n8n/workflows/`:

1. **voice_command_handler.json**: Main voice processing workflow
2. **red_alert_protocol.json**: Emergency lighting and sound effects
3. **status_report.json**: Ship status query
4. **deep_research_agent.json**: Long-running research tasks using fire-and-forget pattern

### Fire-and-Forget Pattern

For tasks exceeding Home Assistant's timeout (30s default):
1. n8n webhook immediately returns acknowledgment
2. Home Assistant speaks acknowledgment
3. n8n continues processing in background
4. On completion, n8n calls HA REST API to announce results via TTS

## Platform Support

- **Primary target**: Linux (Ubuntu/Debian/Linux Mint) with Docker Engine
- **Also supported**: Windows/macOS with Docker Desktop (use `docker-compose.desktop.yml`)
- **GPU acceleration**: NVIDIA GPUs only (requires NVIDIA Container Toolkit on Linux)

## File Organization

- `docker/`: Docker Compose files, volumes, and environment configuration
- `homeassistant/config/`: HA configuration files (YAML)
- `n8n/workflows/`: Importable workflow JSON files
- `esphome/`: Voice satellite firmware configurations
- `prompts/`: LCARS persona and tool definitions
- `scripts/`: Deployment, health check, backup utilities
- `docs/`: Extended documentation

## Security Considerations

- Never commit `docker/.env` to version control
- Home Assistant Long-Lived Access Tokens should be rotated periodically
- n8n encryption key must remain stable (changing it breaks stored credentials)
- Exposed entities in Extended OpenAI should be limited to prevent LLM from accessing sensitive data
- Do not expose high-frequency sensors or camera/person entities to the LLM

## Common Issues

### "Computer" wake word not detected
- Check openWakeWord container logs
- Adjust sensitivity threshold in ESPHome config
- Verify microphone not muted on satellite

### Slow LLM response times
- Monitor GPU VRAM: `nvidia-smi`
- Use quantized models (Q4_K_M)
- Check model is kept loaded (`OLLAMA_KEEP_ALIVE=24h`)

### n8n cannot reach Home Assistant
- Verify `HA_URL` environment variable is `http://host.docker.internal:8123`
- Check n8n has `extra_hosts` configured with `host.docker.internal:host-gateway`
- Never use `http://homeassistant:8123` in n8n workflows

### LLM hallucinating devices
- Review entity exposure in Extended OpenAI config
- Limit exposed entities to critical items only
- Avoid exposing system entities like `automation.*`, `update.*`

## Testing

```bash
# Test Home Assistant REST API
curl http://localhost:8123/api/

# Test Ollama API
curl http://localhost:11434/api/tags

# Test n8n health
curl http://localhost:5678/healthz

# Full system health check
python3 scripts/health_check.py --verbose
```
