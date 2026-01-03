# Hostname Field Visibility Fix

**Date:** 2026-01-02

## Issue

User reported inability to specify server addresses for custom deployment configuration:

> "I'm sorry, but still there is no area to enter the server address for my custom configuration. I only have port entry fields."

The user needed to specify:
- Hostname/IP address for remote servers
- Full connection information for 3rd-party servers
- All necessary configuration to fit into docker compose files

## Root Cause

The previous UI design only displayed hostname/port fields when the "Use existing" checkbox was checked. This created confusion because:

1. Users didn't realize they needed to check the box first to see the fields
2. The checkbox label "Use existing [service]" wasn't clear that it also applied to remote/3rd-party servers
3. When deploying new containers, only port fields were shown (hostname fields were hidden)

## Solution

### 1. Improved Checkbox Label

**Before:**
```python
st.checkbox(f"Use existing {service.name}", ...)
```

**After:**
```python
st.checkbox(f"Connect to existing/remote {service.name} server", ...)
```

**Help Text:**
```
Check this to connect to an existing {service.name} instance (local, remote, or 3rd-party).
Uncheck to deploy a new container.
```

### 2. Always Show Connection Fields

**Before:** Fields only appeared when checkbox was checked

**After:** Fields always visible for services that support existing infrastructure, with clear section headers:

- When **checked**: "🌐 Remote/Existing Server Connection:"
  - Editable hostname/IP field
  - Editable port field
  - Test connection button

- When **unchecked**: "🐳 New Container Deployment:"
  - Disabled container name field (shows Docker container name)
  - External port mapping field

### 3. Enhanced Field Labels and Help Text

**Hostname field (when using existing):**
```python
st.text_input(
    "Hostname/IP Address:",
    help="Hostname or IP address of the existing server (e.g., 'db.example.com', '192.168.1.100', 'host.docker.internal')",
)
```

**Container name field (when deploying new):**
```python
st.text_input(
    "Container Hostname:",
    value=key,  # e.g., 'postgres', 'ollama'
    disabled=True,
    help=f"This service will run in a Docker container named '{key}' (accessible from other containers at this hostname)",
)
```

**Port field (when using existing):**
```python
st.number_input(
    "Port:",
    help=f"Port number on the remote/existing server (default: {service.default_port})",
)
```

**Port field (when deploying new):**
```python
st.number_input(
    "External Port:",
    help=f"Port to expose on host machine (default: {service.default_port})",
)
```

## Code Changes

### File: `lcars_guide.py`

**Lines 1117-1268:** Complete restructure of service configuration UI

**Key improvements:**

1. **Checkbox** (lines 1118-1125): Updated label and help text
2. **Always show fields** (line 1137): Moved field display outside of conditional
3. **Section headers** (lines 1138-1141): Clear indication of deployment mode
4. **Hostname field logic** (lines 1145-1177):
   - Editable when using existing
   - Shows container name when deploying new
5. **Port field logic** (lines 1179-1208):
   - Different labels and help text based on mode
6. **Health check** (lines 1210-1237): Only shown when using existing

## User Experience Flow

### Scenario 1: Connect to Remote PostgreSQL

1. Open "PostgreSQL" expander
2. See checkbox: "Connect to existing/remote PostgreSQL server"
3. **Check the box**
4. See "🌐 Remote/Existing Server Connection:" header
5. Enter hostname: `db.example.com`
6. Enter port: `5432`
7. Click "🩺 Test Connection"
8. Save configuration

### Scenario 2: Deploy New Ollama Container

1. Open "Ollama" expander
2. See checkbox: "Connect to existing/remote Ollama server"
3. **Leave unchecked**
4. See "🐳 New Container Deployment:" header
5. See disabled field "Container Hostname: ollama"
6. Enter external port: `11434` (or customize)
7. Save configuration

### Scenario 3: Use Existing Local Service

1. Open "Home Assistant" expander
2. Check "Connect to existing/remote Home Assistant server"
3. Enter hostname: `host.docker.internal` (for services on Docker host)
4. Enter port: `8123`
5. See warning about using `host.docker.internal` instead of `localhost`
6. Test connection
7. Save configuration

## Benefits

1. **No hidden fields**: All configuration options always visible
2. **Clear mode indication**: Section headers show what you're configuring
3. **Better labels**: "Hostname/IP Address" vs "Container Hostname" vs "External Port"
4. **Comprehensive help text**: Examples provided for each field
5. **Support for all server types**: Local, remote, 3rd-party clearly supported
6. **No confusion**: User can see exactly what will happen in each mode

## Validation

All code compiles without errors:

```bash
python -m py_compile lcars_guide.py
# No errors
```

## Documentation Updates

- `CUSTOM_DEPLOYMENT.md`: Updated "Step 2: Service Configuration" section to reflect new UI flow
- Added examples for hostname/IP addresses
- Clarified difference between existing/remote vs new container deployment

## Status

✅ **RESOLVED** - User can now see and configure hostname/IP address for all services in custom deployment mode.

---

Live long and prosper. 🖖
