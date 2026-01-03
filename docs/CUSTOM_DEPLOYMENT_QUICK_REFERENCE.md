# Custom Deployment - Quick Reference Guide

## Service Configuration Cheat Sheet

### For Each Service in Custom Deployment

You'll see an expander with the service name. Inside, you have two options:

---

## Option 1: Connect to Existing/Remote Server

**When to use:** You have an existing database, LLM server, or other service running elsewhere.

**Steps:**

1. ✅ **Check** the box: "Connect to existing/remote [service] server"
2. See section header: **🌐 Remote/Existing Server Connection:**
3. Enter **Hostname/IP Address**:
   - Examples: `db.example.com`, `192.168.1.100`, `host.docker.internal`
   - ⚠️ Use `host.docker.internal` for services on the same machine (not `localhost`)
4. Enter **Port**: Default shown in help text
5. Click **🩺 Test Connection** to verify
6. If test fails but you want to proceed: Check "Use this service anyway"

**What happens:**
- LCARS will NOT deploy a container for this service
- LCARS will connect to your specified server
- Configuration saved to `.env` and `docker-compose.override.yml`

---

## Option 2: Deploy New Container

**When to use:** You want LCARS to run this service in a Docker container.

**Steps:**

1. ❌ **Uncheck** (or leave unchecked) the box: "Connect to existing/remote [service] server"
2. See section header: **🐳 New Container Deployment:**
3. See **Container Hostname**: (disabled field showing container name, e.g., `postgres`)
4. Enter **External Port**: Port to expose on host machine
   - Default shown in help text
   - Customize if you have port conflicts

**What happens:**
- LCARS will deploy a new Docker container
- Container accessible from other containers by name (e.g., `postgres:5432`)
- Accessible from host machine at `localhost:[external_port]`

---

## Service-by-Service Guide

### Home Assistant

**Can use existing:** ✅ Yes

**Common scenarios:**
- **New install**: Deploy new container (default port 8123)
- **Existing HA**: Connect to existing (use `host.docker.internal:8123` if on same machine)
- **Remote HA**: Connect to existing (e.g., `192.168.1.50:8123`)

### PostgreSQL

**Can use existing:** ✅ Yes

**Common scenarios:**
- **New install**: Deploy new container (default port 5432)
- **Existing DB server**: Connect to existing (e.g., `db.example.com:5432`)
- **RDS/Cloud DB**: Connect to existing (e.g., `mydb.us-east-1.rds.amazonaws.com:5432`)

⚠️ **Note:** If using existing, ensure database user has permissions to create tables.

### Redis

**Can use existing:** ✅ Yes
**Required:** ❌ No (optional for caching)

**Common scenarios:**
- **New install**: Deploy new container (default port 6379)
- **Existing Redis cluster**: Connect to existing

### Ollama (LLM Server)

**Can use existing:** ✅ Yes

**Common scenarios:**
- **New install**: Deploy new container (default port 11434)
- **Existing Ollama**: Connect to existing (e.g., `gpu-server.local:11434`)
- **GPU server**: Connect to existing remote server with GPU

💡 **Tip:** Use existing if you have a dedicated GPU server running Ollama.

### n8n (Workflow Automation)

**Can use existing:** ❌ **NO** (must deploy fresh)

**Why:** n8n requires specific LCARS configuration, custom workflows, and database schema.

**Configuration:**
- Only external port can be customized
- Default: 5678

### Open WebUI

**Can use existing:** ✅ Yes

**Common scenarios:**
- **New install**: Deploy new container (default port 3000)
- **Existing Open WebUI**: Connect to existing

### Whisper (Speech-to-Text)

**Can use existing:** ✅ Yes
**Required:** ❌ No (only if using voice satellites)

**Common scenarios:**
- **New install with voice**: Deploy new container (default port 10300)
- **Existing Whisper**: Connect to existing
- **No voice satellites**: Skip (not required)

### Piper (Text-to-Speech)

**Can use existing:** ✅ Yes
**Required:** ❌ No (only if using voice satellites)

**Common scenarios:**
- **New install with voice**: Deploy new container (default port 10200)
- **Existing Piper**: Connect to existing
- **No voice satellites**: Skip (not required)

### openWakeWord

**Can use existing:** ✅ Yes
**Required:** ❌ No (only if using voice satellites)

**Common scenarios:**
- **New install with voice**: Deploy new container (default port 10400)
- **Existing wake word**: Connect to existing
- **No voice satellites**: Skip (not required)

---

## Common Configurations

### Minimal Install (LLM Chat Only)

Deploy new:
- Home Assistant
- PostgreSQL
- Ollama
- Open WebUI

Use existing: *(none)*

Skip:
- Redis, Whisper, Piper, openWakeWord

---

### Full Voice Assistant

Deploy new:
- All services

---

### Hybrid (Existing Database, New LLM)

Use existing:
- PostgreSQL (e.g., `db.company.com:5432`)

Deploy new:
- Home Assistant
- Ollama
- n8n
- Open WebUI
- Voice services

---

### Remote GPU Server

Use existing:
- Ollama (e.g., `gpu-server.local:11434`)

Deploy new:
- All others

---

## Troubleshooting

### "Can't see hostname field"

**Solution:** Check the "Connect to existing/remote [service] server" checkbox first.

### "Connection test failing"

**Possible causes:**
- Service not running yet
- Firewall blocking connection
- Wrong hostname/port

**Solution:** Use "Use this service anyway" checkbox to proceed if you'll start the service later.

### "Localhost doesn't work"

**Cause:** Inside Docker containers, `localhost` refers to the container itself, not the host machine.

**Solution:** Use `host.docker.internal` for services on the same machine.

### "Port already in use"

**Solution:**
1. If using existing service: Specify the actual port in "Connect to existing" mode
2. If deploying new: Change the external port to an available port

---

## File Outputs

After clicking "💾 Save Configuration & Continue", the system generates:

1. **`docker/deployment_config.json`**
   - Full service configuration
   - Can be reloaded for future deployments

2. **`docker/docker-compose.override.yml`**
   - Disables services marked as "use existing"
   - Remaps custom ports
   - Auto-loaded by Docker Compose on Linux

3. **`docker/.env` updates**
   - `HA_URL`: Home Assistant endpoint
   - `OLLAMA_BASE_URL`: Ollama endpoint
   - `DB_POSTGRESDB_HOST`, `DB_POSTGRESDB_PORT`: PostgreSQL connection

---

## Next Steps After Configuration

1. Review deployment summary showing:
   - **Using Existing:** Services LCARS will connect to
   - **Deploying New:** Services LCARS will launch

2. Proceed to deployment execution:
   - **Automated (Linux):** Click deployment button
   - **Manual (all platforms):** Copy commands shown in UI

3. LCARS will:
   - Skip containers for "existing" services
   - Deploy only necessary containers
   - Configure all services to talk to correct endpoints

---

**Need help?** See full guide in `docs/CUSTOM_DEPLOYMENT.md`

Live long and prosper. 🖖
