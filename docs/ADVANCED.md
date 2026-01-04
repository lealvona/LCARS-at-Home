# LCARS Computer - Advanced Configuration Guide

This guide covers advanced configuration, optimization, and troubleshooting for the LCARS Computer Star Trek voice assistant system.

## Table of Contents

1. [GPU Acceleration](#gpu-acceleration)
2. [Wake Word Customization](#wake-word-customization)
3. [Voice Persona Tuning](#voice-persona-tuning)
4. [Multi-Room Audio](#multi-room-audio)
5. [Fire-and-Forget Pattern](#fire-and-forget-pattern)
6. [RAG Knowledge Base](#rag-knowledge-base)
7. [Custom n8n Tools](#custom-n8n-tools)
8. [Security Hardening](#security-hardening)
9. [Performance Optimization](#performance-optimization)
10. [Troubleshooting](#troubleshooting)

---

## GPU Acceleration

GPU acceleration is critical for achieving sub-second response times. Without it, expect 5-10 second delays.

### NVIDIA GPU Setup

1. **Install NVIDIA Container Toolkit**:

```bash
# Add NVIDIA package repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# Install toolkit
sudo apt update && sudo apt install -y nvidia-container-toolkit

# Restart Docker
sudo systemctl restart docker
```

2. **Enable GPU in docker-compose.yml**:

Uncomment the GPU sections in the `ollama` and `whisper` services:

```yaml
ollama:
  # ... existing config ...
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
```

3. **Verify GPU access**:

```bash
docker exec LCARS-ollama nvidia-smi
```

### AMD GPU Setup (ROCm)

AMD GPU support requires the ROCm version of Ollama:

```yaml
ollama:
  image: ollama/ollama:rocm
  devices:
    - /dev/kfd
    - /dev/dri
  group_add:
    - video
```

---

## Wake Word Customization

### Training a Custom "Computer" Wake Word

The default openWakeWord model includes a "Computer" wake word, but you can train a custom model with your voice:

1. **Collect audio samples** (at least 100 recordings):

```bash
# Record samples using arecord
for i in {1..100}; do
  echo "Say 'Computer' (recording $i/100)..."
  arecord -f cd -t wav -d 2 computer_$i.wav
  sleep 1
done
```

2. **Use the openWakeWord training notebook** at:
   https://github.com/dscripka/openWakeWord/tree/main/notebooks

3. **Deploy the custom model**:

```yaml
openwakeword:
  volumes:
    - ./custom_wakewords:/custom
  command: >
    --custom-model-dir /custom
    --threshold 0.5
```

### Sensitivity Tuning

If you're getting false activations or missed triggers, adjust these parameters:

```yaml
command: >
  --preload-model ok_nabu
  --threshold 0.6       # Higher = fewer false positives (0.3-0.8)
  --trigger-level 2     # Consecutive detections required (1-3)
  --vad-threshold 0.5   # Voice activity detection sensitivity
```

---

## Voice Persona Tuning

### Creating Alternative Personas

The LCARS persona can be customized for different "crew members" or moods.

**Emergency Mode Persona** (for Red Alert):

```text
You are the Emergency Computer System. Situation critical.
- Speak in short, urgent phrases
- Prioritize crew safety information
- Prefix all responses with "ALERT:"
- Use phrases like "Recommend immediate", "Danger detected", "Evacuate"
```

**Night Mode Persona** (quieter, minimal):

```text
You are the Computer, currently in Night Mode.
- Keep responses under 20 words
- Whisper-friendly language (avoid sibilants)
- Only report critical information
- End responses with "Returning to standby."
```

### Configuring Multiple Personas in Open WebUI

1. Navigate to **Workspace → Models**
2. Create separate model configurations:
   - `lcars-standard` - Main persona
   - `lcars-emergency` - Red Alert mode
   - `lcars-night` - Night mode
3. Switch personas via n8n workflow based on `input_boolean` states

---

## Multi-Room Audio

### Room-Aware Responses

Configure the system to respond on the satellite that received the command:

1. **Pass device_id from satellite** (ESPHome config):

```yaml
voice_assistant:
  # ... existing config ...
  on_tts_end:
    - lambda: |-
        // The device_id is passed in the pipeline
```

2. **Map device to room in n8n**:

```javascript
// In the voice_command_handler workflow
const deviceRoomMap = {
  'satellite_kitchen': 'media_player.kitchen_speaker',
  'satellite_living_room': 'media_player.living_room',
  'satellite_bedroom': 'media_player.bedroom_echo'
};

const targetPlayer = deviceRoomMap[$json.device_id] || 'media_player.whole_house';
```

3. **Target TTS to specific room**:

```javascript
// HTTP Request to Home Assistant
POST http://host.docker.internal:8123/api/services/tts/speak
{
  "entity_id": "tts.piper",
  "media_player_entity_id": targetPlayer,
  "message": llmResponse
}
```

---

## Fire-and-Forget Pattern

For long-running tasks that exceed voice pipeline timeouts.

### Implementation

```
User: "Computer, analyze sensor anomalies from the last week"

Flow:
1. Webhook receives request
2. IMMEDIATELY return: {"response": "Processing analysis, Commander. Results will be announced when complete."}
3. Home Assistant speaks the acknowledgment
4. n8n continues background processing...
5. [10 seconds later] n8n calls HA to announce: "Analysis complete. 3 anomalies detected..."
```

### n8n Workflow Structure

```
[Webhook] → [Respond Immediately] ──────────────────────────────→ [End]
              │
              └→ [Continue Processing] → [Long Task] → [Call HA TTS]
```

**Key**: Use the "Respond to Webhook" node immediately, then continue the workflow asynchronously.

---

## RAG Knowledge Base

### Setting Up the Ship's Database

Upload documents to Open WebUI for knowledge retrieval:

1. **Navigate to Workspace → Knowledge**
2. **Create a collection**: "Ship's Database"
3. **Upload documents**:
   - Appliance manuals (PDF)
   - House procedures (Markdown)
   - Emergency contacts (CSV)
   - Family schedules (iCal export)

### Optimizing RAG Retrieval

For technical manuals, use smaller chunk sizes:

```
Chunk Size: 500 tokens (default 1000)
Chunk Overlap: 100 tokens
```

For conversational documents (procedures), use larger chunks:

```
Chunk Size: 1500 tokens
Chunk Overlap: 200 tokens
```

### Hybrid Search Configuration

Enable both keyword and semantic search in Open WebUI:

```yaml
environment:
  - RAG_EMBEDDING_MODEL=nomic-embed-text
  - RAG_TOP_K=5           # Number of chunks to retrieve
  - RAG_RELEVANCE_THRESHOLD=0.5
  - ENABLE_RAG_HYBRID_SEARCH=true
```

---

## Custom n8n Tools

### Creating a Lock Control Tool

```json
{
  "name": "control_lock",
  "description": "Lock or unlock a door. Requires verbal confirmation for unlock.",
  "parameters": {
    "entity_id": "string - The lock entity (e.g., lock.front_door)",
    "action": "string - 'lock' or 'unlock'"
  }
}
```

**Sub-workflow**:

```
[Webhook] → [Check Action]
              ├─ lock → [Call HA lock.lock] → [Respond Success]
              └─ unlock → [Check Authorization] → [Call HA lock.unlock] → [Respond Success]
```

### Creating a Calendar Query Tool

```javascript
// Code node to query Google Calendar via HA
const today = new Date().toISOString().split('T')[0];
const events = await $http.get({
  url: `http://host.docker.internal:8123/api/calendars/calendar.family`,
  headers: { 'Authorization': `Bearer ${HA_TOKEN}` },
  qs: { start: today, end: today }
});

// Format for LCARS response
return events.map(e => `${e.start.dateTime.slice(11,16)} hours: ${e.summary}`);
```

---

## Security Hardening

### Network Isolation

Keep services internal, expose only via reverse proxy:

```yaml
# docker-compose.override.yml
services:
  n8n:
    ports: []  # Remove external port
    networks:
      - lcars_network
      
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/nginx/certs
```

### Credential Management

Never store credentials in workflow JSON:

1. Use n8n's built-in credential store
2. Reference via `{{ $credentials.homeAssistant.token }}`
3. Encrypt the n8n database with a strong `N8N_ENCRYPTION_KEY`

### Rate Limiting

Protect webhooks from abuse:

```javascript
// Add to webhook handlers
const rateLimiter = new Map();
const MAX_REQUESTS = 60; // per minute

const clientIP = $json.headers['x-forwarded-for'] || 'unknown';
const count = rateLimiter.get(clientIP) || 0;

if (count > MAX_REQUESTS) {
  return { error: 'Rate limit exceeded' };
}

rateLimiter.set(clientIP, count + 1);
setTimeout(() => rateLimiter.delete(clientIP), 60000);
```

---

## Performance Optimization

### Model Selection

| Use Case | Recommended Model | VRAM Required |
|----------|------------------|---------------|
| Voice Commands | llama3.1:8b-q4_K_M | 6 GB |
| Complex Reasoning | llama3.1:70b-q4_K_M | 40 GB |
| Fast Responses | gemma2:2b | 3 GB |
| Code Generation | codellama:13b | 10 GB |

### Reducing Latency

1. **Keep models loaded**:
   ```yaml
   OLLAMA_KEEP_ALIVE=24h
   ```

2. **Use INT8 Whisper**:
   ```yaml
   WHISPER_MODEL=medium-int8  # Faster than full precision
   ```

3. **Enable streaming TTS**:
   Configure Piper to stream audio chunks as they're generated.

4. **Minimize context gathering**:
   Only fetch states for entities in the current room.

### Memory Management

Monitor VRAM usage:

```bash
watch -n 1 nvidia-smi
```

If VRAM fills up, the system falls back to CPU, causing massive latency.

---

## Troubleshooting

### Voice Pipeline Issues

**Problem**: Wake word not detected
- Check microphone levels: `arecord -l`
- Lower threshold in openwakeword config
- Verify audio stream reaches the container

**Problem**: STT returning gibberish
- Check Whisper language setting
- Ensure audio sample rate matches (16kHz)
- Try a larger Whisper model

**Problem**: TTS sounds robotic
- Adjust Piper settings:
  ```yaml
  PIPER_NOISE_SCALE=0.667
  PIPER_NOISE_W=0.8
  PIPER_LENGTH_SCALE=1.0
  ```

### n8n Workflow Issues

**Problem**: Webhook timeout
- Voice pipelines timeout after ~30s
- Implement fire-and-forget pattern
- Reduce LLM max_tokens

**Problem**: Home Assistant connection refused
- Verify HA is accessible: `curl http://host.docker.internal:8123/api/`
- Check Long-Lived Access Token validity
- Ensure network connectivity between containers

### LLM Issues

**Problem**: Hallucinating devices
- Limit exposed entities in Extended OpenAI config
- Add explicit "only use tools for devices that exist" in system prompt
- Enable tool confirmation before execution

**Problem**: Slow responses
- Check GPU is being used: `nvidia-smi`
- Use quantized models (Q4_K_M)
- Reduce context window size

### Container Health Checks

```bash
# Check all container status
docker compose ps

# View specific logs
docker compose logs -f ollama

# Restart unhealthy container
docker compose restart whisper

# Full stack restart
docker compose down && docker compose up -d
```

### Useful Debug Commands

```bash
# Test Whisper directly
curl -X POST http://localhost:10300/api/transcribe \
  -F "file=@test.wav"

# Test Piper directly
curl "http://localhost:10200/api/tts?text=Testing"

# Test Ollama directly
curl http://localhost:11434/api/generate \
  -d '{"model": "llama3.1:8b", "prompt": "Hello"}'

# Test n8n webhook
curl -X POST http://localhost:5678/webhook/voice-command \
  -H "Content-Type: application/json" \
  -d '{"text": "Computer, status report", "device_id": "test"}'
```

---

## Appendix: Environment Variables Reference

| Variable | Service | Description |
|----------|---------|-------------|
| `TIMEZONE` | All | System timezone |
| `N8N_ENCRYPTION_KEY` | n8n | Encryption for stored credentials |
| `POSTGRES_PASSWORD` | PostgreSQL | Database password |
| `WEBUI_SECRET_KEY` | Open WebUI | Session encryption |
| `HA_ACCESS_TOKEN` | n8n | Home Assistant API token |
| `WHISPER_MODEL` | Whisper | STT model size |
| `PIPER_VOICE` | Piper | TTS voice model |
| `OLLAMA_KEEP_ALIVE` | Ollama | Model unload timeout |

---

*Live long and prosper. 🖖*
