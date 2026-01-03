# LCARS Computer: Star Trek Voice Assistant for Home Automation

A complete, self-hosted, privacy-first voice assistant that transforms your home into the USS Enterprise. This system integrates **Home Assistant** (the "body"), **Open WebUI with Ollama** (the "mind"), and **n8n** (the "nervous system") to create a voice-controlled environment that responds to natural language commands.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Hardware Requirements](#hardware-requirements)
3. [Quick Start](#quick-start)
4. [Component Installation](#component-installation)
5. [Voice Pipeline Configuration](#voice-pipeline-configuration)
6. [LCARS Persona Setup](#lcars-persona-setup)
7. [n8n Workflow Configuration](#n8n-workflow-configuration)
8. [Advanced Features](#advanced-features)
9. [Troubleshooting](#troubleshooting)

---

## System Architecture

The LCARS Computer follows a **Separation of Concerns** pattern where each component has a distinct responsibility:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                          VOICE SATELLITES                               │
│    (ESP32-S3-BOX-3 / M5Stack Atom Echo / Raspberry Pi + ReSpeaker)     │
│                              │                                          │
│                    Wake Word: "Computer"                                │
│                              │                                          │
│                              ▼                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                        HOME ASSISTANT                                   │
│                    (The Body / State Machine)                           │
│                              │                                          │
│   ┌──────────────────────────┼──────────────────────────────────┐      │
│   │                          │                                   │      │
│   ▼                          ▼                                   ▼      │
│ Wyoming          Extended OpenAI              Assist            │      │
│ Protocol         Conversation                 Pipeline          │      │
│ (Whisper/Piper)  Integration                                    │      │
│                          │                                             │
│                          ▼                                             │
├─────────────────────────────────────────────────────────────────────────┤
│                          n8n                                            │
│                 (The Nervous System / Orchestrator)                     │
│                              │                                          │
│   ┌──────────────────────────┼──────────────────────────────────┐      │
│   │                          │                                   │      │
│   ▼                          ▼                                   ▼      │
│ Webhooks              AI Agent Node                Tool Workflows│      │
│ (Fire-and-Forget)     (ReAct Pattern)              (HA Services) │      │
│                          │                                             │
│                          ▼                                             │
├─────────────────────────────────────────────────────────────────────────┤
│                    OPEN WEBUI + OLLAMA                                  │
│                 (The Mind / Cognitive Engine)                           │
│                              │                                          │
│   ┌──────────────────────────┼──────────────────────────────────┐      │
│   │                          │                                   │      │
│   ▼                          ▼                                   ▼      │
│ Local LLM           RAG / Knowledge Base          LCARS Persona │      │
│ (Llama 3.1/Mistral) (Ship's Database)             (System Prompt)│      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Flow for a Voice Command

1. **Wake Word Detection**: Satellite hears "Computer" via openWakeWord
2. **Speech-to-Text**: Audio streamed to Whisper (faster-whisper with GPU)
3. **Intent Routing**: Home Assistant receives text, forwards to n8n webhook
4. **Context Gathering**: n8n fetches current device states from Home Assistant
5. **LLM Reasoning**: Open WebUI processes request with LCARS persona
6. **Tool Execution**: n8n executes Home Assistant service calls
7. **Response Generation**: LLM generates response text
8. **Text-to-Speech**: Piper synthesizes audio with computer voice
9. **Audio Playback**: Response played on satellite speaker

---

## Hardware Requirements

### Server (Running Docker Stack)

| Component | Minimum | Recommended | Notes |
| --- | --- | --- | --- |
| CPU | Intel i5 (8th Gen) / Ryzen 5 | Intel i7 (12th Gen) / Ryzen 7 | High core count benefits containers |
| RAM | 16 GB DDR4 | 32-64 GB DDR4/5 | LLMs are memory-intensive |
| GPU | None (CPU inference) | NVIDIA RTX 3060 12GB | Critical for sub-second response |
| Storage | 500GB SSD | 1TB NVMe SSD | Fast I/O for databases |

### Voice Satellites

| Device | Price Range | Features | Best For |
| --- | --- | --- | --- |
| ESP32-S3-BOX-3 | ~$45 | Screen, AEC, high-quality mic | Primary satellite |
| M5Stack Atom Echo | ~$15 | Compact, budget-friendly | Secondary rooms |
| Raspberry Pi Zero 2W + ReSpeaker | ~$40 | Flexible, Linux-based | DIY enthusiasts |

---

## Quick Start

### Platform support

- Primary target: **Linux Mint Xia** (Ubuntu-based) using Docker Engine + Compose plugin.
- Also documented: **Windows/macOS** using Docker Desktop.

### Prerequisites

Install Docker + Docker Compose depending on your OS (see [docs/DOCKER_INSTALL.md](docs/DOCKER_INSTALL.md) for full detail).

Linux Mint Xia (recommended):

```bash
# Docker Engine + Compose plugin
# Recommended: use Docker's apt repository method (see docs/DOCKER_INSTALL.md)

# Python 3.10+ and venv
sudo apt update && sudo apt install -y python3 python3-pip python3-venv

# Verify
docker --version
docker compose version
python3 --version
```

Windows:

- Install Docker Desktop (WSL 2 recommended): <https://docs.docker.com/desktop/install/windows-install/>

macOS:

- Install Docker Desktop: <https://docs.docker.com/desktop/install/mac-install/>

### One-Command Deployment

```bash
# Clone and deploy
cd /opt
git clone <your-repo-url> lcars-computer
cd lcars-computer
./scripts/deploy.sh
```

Or follow the step-by-step guide below.

### Windows / macOS (Docker Desktop) notes

This repo’s default compose file runs Home Assistant with `network_mode: host` for discovery.
On Docker Desktop, host networking for Linux containers is limited or unsupported.

Use the Docker Desktop override file instead:

```bash
cd docker
docker compose -f docker-compose.desktop.yml up -d
```

---

## Component Installation

### Step 1: Create the Docker Network

All services communicate over a dedicated Docker network for security and DNS resolution.

```bash
docker network create lcars_network
```

### Step 2: Deploy the Stack

Navigate to the docker directory and start all services:

```bash
cd docker
docker compose up -d
```

This starts:

- **Home Assistant** on port 8123
- **n8n** on port 5678
- **Open WebUI** on port 3000
- **Ollama** on port 11434
- **Whisper (faster-whisper-server)** on port 10300
- **Piper TTS** on port 10200
- **openWakeWord** on port 10400
- **PostgreSQL** (internal)
- **Redis** (internal)

### Step 3: Initial Configuration

Access each service and complete initial setup:

1. **Home Assistant**: <http://localhost:8123>
   - Create admin account
   - Configure location and units
   
2. **Open WebUI**: <http://localhost:3000>
   - Create admin account
   - Pull a model: `llama3.1:8b` (recommended)
   
3. **n8n**: <http://localhost:5678>
   - Create admin account
   - Note your API key for later

---

## Voice Pipeline Configuration

### Step 4: Configure Home Assistant Voice

Add the following to your Home Assistant configuration:

```yaml
# configuration.yaml additions - see homeassistant/config/ directory
```

Install required custom components via HACS:

- **Extended OpenAI Conversation**
- **Chime TTS** (for response sounds)

### Step 5: Configure the Assist Pipeline

In Home Assistant:

1. Go to **Settings → Voice assistants**
2. Click **Add Assistant**
3. Configure:
   - **Name**: LCARS Computer
   - **Language**: English
   - **Conversation agent**: Extended OpenAI Conversation
   - **Speech-to-text**: Whisper (local)
   - **Text-to-speech**: Piper (local)
   - **Wake word**: openWakeWord (Computer)

---

## LCARS Persona Setup

### Step 6: Configure Open WebUI System Prompt

In Open WebUI, create a new Model with the LCARS persona:

1. Go to **Workspace → Models**
2. Click **Create a Model**
3. Use the system prompt from `prompts/lcars_persona.txt`

### Step 7: Configure Extended OpenAI Conversation

In Home Assistant, add the integration configuration:

```yaml
# See homeassistant/config/extended_openai.yaml for full configuration
```

---

## n8n Workflow Configuration

### Step 8: Import Core Workflows

Import the provided workflows from `n8n/workflows/`:

1. **voice_command_handler.json** - Main voice processing
2. **red_alert_protocol.json** - Emergency lighting/sounds
3. **status_report.json** - Ship status query
4. **deep_research_agent.json** - Long-running research tasks

### Step 9: Configure Home Assistant Connection

In n8n:

1. Go to **Settings → Credentials**
2. Add **Home Assistant** credential:
   - Host: `http://host.docker.internal:8123`
   - Access Token: Your Long-Lived Access Token

Note: Workflows read the base URL from `HA_URL` inside the n8n container. The default is `http://host.docker.internal:8123`.

---

## Advanced Features

### Fire-and-Forget Pattern

For long-running tasks that exceed Home Assistant's timeout:

```text
User: "Computer, analyze sensor data for anomalies"

Flow:
1. n8n receives webhook
2. Immediately returns: "Processing your request, Commander"
3. Home Assistant speaks acknowledgment
4. n8n continues analysis in background
5. On completion, n8n calls HA REST API to announce results
```

### RAG / Ship's Database

Upload documents to Open WebUI for knowledge retrieval:

- Appliance manuals
- House procedures
- Family schedules
- Emergency protocols

### Multi-Room Audio

Configure room-aware responses by:

1. Passing `device_id` from satellite to n8n
2. Looking up room from Home Assistant area registry
3. Targeting TTS output to specific media players

---

## Troubleshooting

### Common Issues

### "Computer" wake word not detected

- Check openWakeWord container logs
- Adjust sensitivity in ESPHome config
- Verify microphone is not muted

### Slow response times

- Monitor GPU VRAM usage (`nvidia-smi`)
- Use quantized models (Q4_K_M)
- Check network latency between containers

### LLM hallucinating devices

- Review entity exposure in Extended OpenAI config
- Limit exposed entities to critical items only

### Health Check

Run the health check script:

```bash
./scripts/health_check.py
```

### Logs

View combined logs:

```bash
docker compose logs -f
```

View specific service:

```bash
docker compose logs -f homeassistant
docker compose logs -f n8n
docker compose logs -f ollama
```

---

## File Structure

```text
lcars-computer/
├── docker/
│   ├── docker-compose.yml          # Main stack definition
│   ├── .env                        # Environment variables
│   └── volumes/                    # Persistent data
├── homeassistant/
│   ├── config/
│   │   ├── configuration.yaml      # Main HA config
│   │   ├── extended_openai.yaml    # LLM integration
│   │   ├── automations.yaml        # Voice automations
│   │   └── scripts.yaml            # HA scripts for tools
│   └── custom_components/          # HACS components
├── n8n/
│   └── workflows/
│       ├── voice_command_handler.json
│       ├── red_alert_protocol.json
│       ├── status_report.json
│       └── deep_research_agent.json
├── esphome/
│   ├── voice_satellite_s3box.yaml
│   └── voice_satellite_atom.yaml
├── prompts/
│   ├── lcars_persona.txt
│   └── tool_definitions.yaml
├── scripts/
│   ├── deploy.sh                   # Automated deployment
│   ├── health_check.py             # System health monitor
│   ├── backup.py                   # Configuration backup
│   └── update.sh                   # Update all containers
└── docs/
    └── ADVANCED.md                 # Advanced configuration
```

---

## License

This project is open source under the MIT License.

## Acknowledgments

- Home Assistant community
- n8n.io team
- Open WebUI developers
- Ollama team
- The creators of Wyoming Protocol

Live long and prosper.
