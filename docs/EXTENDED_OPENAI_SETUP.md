# Extended OpenAI Conversation - Complete Setup Guide

**Purpose:** Connect Home Assistant to your local LLM and enable voice/text control of your home
**Difficulty:** ⭐⭐⭐ Moderate (multiple configuration steps)
**Time Required:** 15-20 minutes
**Prerequisites:** HACS installed, Open WebUI running with a model pulled

---

## 🔴 Why This is Critical

**This is THE integration that makes your LCARS Computer functional.**

Without Extended OpenAI Conversation:
- ❌ LLM can't control lights
- ❌ LLM can't adjust climate
- ❌ LLM can't lock doors
- ❌ Voice commands don't work
- ❌ You just have a chatbot that can't do anything

With Extended OpenAI Conversation:
- ✅ LLM controls all Home Assistant devices
- ✅ Voice commands work end-to-end
- ✅ Function calling (12 LCARS tools)
- ✅ Natural language home control

---

## Part 1: Install via HACS

### Step 1: Add Custom Repository

1. In Home Assistant, click **HACS** in the sidebar
2. Click **Integrations** at the top
3. Click the **⋮** menu (three dots, top right)
4. Select **Custom repositories**
5. A dialog appears

**Enter these values:**
- **Repository:** `https://github.com/jekalmin/extended_openai_conversation`
- **Category:** Select **Integration** from dropdown
6. Click **Add**
7. Close the dialog

### Step 2: Download the Integration

1. Still in HACS → Integrations
2. Click **+ Explore & Download Repositories** (bottom right blue button)
3. Search for: `Extended OpenAI Conversation`
4. Click on it when it appears
5. Click **Download** (bottom right)
6. Click **Download** again to confirm
7. Wait for download to complete (~10 seconds)

### Step 3: Restart Home Assistant

**Critical:** The integration won't appear until you restart!

1. Go to **Settings → System**
2. Click **Restart** button (top right)
3. Confirm restart
4. Wait 2-3 minutes for full restart
5. Refresh your browser (F5)

---

## Part 2: Add the Integration

### Step 1: Navigate to Integrations

1. Go to **Settings → Devices & Services**
2. Click **+ Add Integration** (bottom right blue button)

### Step 2: Search and Add

1. In the search box, type: `Extended OpenAI Conversation`
2. Click on it when it appears
3. A configuration dialog opens

### Step 3: Initial Configuration

**Name the integration:**
- Enter: `LCARS Computer` (or any name you prefer)
- Click **Submit**

**You now have the integration added!** But it's not configured yet.

---

## Part 3: Configure API Connection

This connects Home Assistant to your local Ollama LLM.

### Step 1: Open Configuration

1. In Settings → Devices & Services
2. Find the **Extended OpenAI Conversation** card
3. Click **Configure** button

### Step 2: API Settings

Enter these exact values:

#### Base URL
```
http://host.docker.internal:3000/v1
```

⚠️ **Critical:**
- Use `host.docker.internal` NOT `localhost`
- Must end with `/v1`
- Don't forget the `http://`

#### API Key
```
(leave blank or type anything)
```

Local Ollama doesn't require authentication. The field may be required, so you can type any random text.

#### Model
```
llama3.1:8b
```

Or whatever model you pulled in Open WebUI. Must match exactly.

#### Max Tokens
```
2048
```

Maximum length of responses. 2048 is good for most commands.

#### Temperature
```
0.7
```

Controls randomness. 0.7 balances creativity and consistency.

#### Top P
```
0.95
```

Nuclear sampling parameter. Default works well.

### Step 3: Save

Click **Submit** to save API configuration.

**Test:** Try asking Home Assistant a simple question in the conversation panel to verify the LLM responds.

---

## Part 4: Add LCARS Control Tools

This is the MOST IMPORTANT step - it gives the LLM the ability to actually control your home through function calling.

### What are Tools?

Tools (aka function calling) allow the LLM to execute actions in Home Assistant:
- `control_light` - Turn lights on/off/dimming
- `get_entity_state` - Check status of devices
- `control_climate` - Adjust thermostat
- `control_lock` - Lock/unlock doors
- `activate_scene` - Trigger scenes
- ...and 7 more!

### Step 1: Open Configuration Again

1. Settings → Devices & Services
2. Extended OpenAI Conversation card
3. Click **Configure**

### Step 2: Find the Spec Field

Look for a section called:
- **Functions** or
- **Tools** or
- **Spec** or
- **Function Definitions**

This is where you paste the tool definitions.

### Step 3: Get the Tool Definitions

**Option A: From Streamlit Guide (Easiest)**
1. Run the LCARS installer: `streamlit run lcars_guide.py`
2. Go to the **Integration** section
3. Scroll to Step 7
4. Copy the YAML from the code box

**Option B: From File**
1. Open: `homeassistant/config/extended_openai.yaml`
2. Copy lines 54-353 (from first `- spec:` to `# --- END SPEC CONFIGURATION ---`)

### Step 4: Paste Tool Definitions

The YAML should look like this:

```yaml
- spec:
    name: control_light
    description: "Turn a light on, off, or adjust its brightness and color"
    parameters:
      type: object
      properties:
        entity_id:
          type: string
          description: "The light entity ID"
        action:
          type: string
          enum: ["on", "off", "toggle"]
          description: "The action to perform"
        brightness_pct:
          type: integer
          description: "Brightness percentage from 0 to 100"
        color_name:
          type: string
          description: "Color name"
      required:
        - entity_id
        - action
  function:
    type: script
    sequence:
      - service: script.control_light
        data:
          entity_id: "{{ entity_id }}"
          action: "{{ action }}"
          brightness_pct: "{{ brightness_pct | default(100) }}"
          color_name: "{{ color_name | default('') }}"

- spec:
    name: get_entity_state
    [... 11 more tools ...]
```

**Full list of 12 LCARS tools:**
1. `control_light` - Light control
2. `get_entity_state` - Query device state
3. `control_climate` - Thermostat control
4. `control_lock` - Door lock control
5. `activate_scene` - Scene activation
6. `get_weather` - Weather query
7. `control_media` - Media player control
8. `get_ship_status` - Comprehensive home status
9. `red_alert` - Emergency protocol
10. `make_announcement` - TTS announcements
11. `set_timer` - Voice timers
12. `call_n8n_workflow` - Complex workflow triggers

### Step 5: Submit

Click **Submit** to save the tool definitions.

**Verification:** The LLM can now see and use these tools!

---

## Part 5: Set as Conversation Agent

This makes Extended OpenAI the default for voice/text commands.

### Step 1: Navigate to Voice Assistants

1. Go to **Settings → Voice assistants**
2. Click **Assist** tab
3. You'll see your assistant (usually "Home Assistant")

### Step 2: Configure Conversation Agent

1. Click on your assistant name
2. Find **Conversation agent** dropdown
3. Select: **Extended OpenAI Conversation** (the one you just configured)
4. Click **Update**

**Done!** All conversation commands now go through your local LLM.

---

## Part 6: Verification

### Test 1: Simple Query

1. In Home Assistant, find the **Assist** button (top right, microphone or chat icon)
2. Type: "What time is it?"
3. Expect: LLM responds with current time in Star Trek style if LCARS persona is loaded

### Test 2: Entity Query (Tool Call)

1. Type: "What's the status of the living room light?"
2. Expect: LLM calls `get_entity_state` tool and reports the actual state

### Test 3: Control Command (Tool Call)

1. Type: "Turn on the living room light"
2. Expect: LLM calls `control_light` tool and the light actually turns on!

### Test 4: Function Calling Verification

**How to check if tools are working:**
1. Settings → Devices & Services
2. Extended OpenAI Conversation
3. Click the entity (e.g., "conversation.extended_openai_conversation")
4. Check **Attributes**
5. Look for `functions` array - should list your 12 tools

---

## Troubleshooting

### Issue: "Entity not found" or "Cannot connect"

**Cause:** Base URL is wrong

**Solution:**
- Verify URL is exactly: `http://host.docker.internal:3000/v1`
- NOT `http://localhost:3000/v1`
- Check Open WebUI is running: `docker ps | grep open-webui`

---

### Issue: LLM responds but can't control anything

**Cause:** Tools not loaded correctly

**Solution:**
1. Go back to Extended OpenAI configuration
2. Check the Spec field has all 12 tools
3. Verify YAML formatting is correct (no extra spaces, proper indentation)
4. Click Submit again
5. Restart Home Assistant

---

### Issue: "Service not found: script.control_light"

**Cause:** Tool definitions reference scripts that don't exist

**Solution:**
This means you're using the LCARS tool definitions but haven't set up the corresponding scripts in Home Assistant.

**Quick fix:**
1. Create dummy scripts in `homeassistant/config/scripts.yaml`
2. Or use simplified tool definitions that call services directly

**Better fix:**
Use the complete LCARS configuration from `homeassistant/config/` which includes all needed scripts.

---

### Issue: "Model not found: llama3.1:8b"

**Cause:** Model name doesn't match what's in Ollama

**Solution:**
1. Check what models you have:
   ```bash
  docker exec LCARS-ollama ollama list
   ```
2. Update the Model field in Extended OpenAI config to match exactly
3. Model names are case-sensitive!

---

### Issue: Responses are slow (>10 seconds)

**Possible causes:**
1. **No GPU** - CPU inference is slow
2. **Model too large** - Try a smaller model (llama3.2:3b)
3. **Max tokens too high** - Reduce to 1024 or 512

**Solutions:**
- Add GPU support: Use `docker-compose.gpu.yml`
- Use quantized models: Add `:Q4_K_M` suffix
- Reduce max tokens in configuration

---

### Issue: LLM gives wrong information about entities

**Cause:** Entity exposure not configured

**Solution:**
1. Settings → Devices & Services → Extended OpenAI
2. Click **Configure**
3. Look for **Exposed Entities** section
4. Select which entities the LLM can see:
   - ✅ Expose: `light.*`, `switch.*`, `climate.*`, `lock.*`
   - ❌ Don't expose: `automation.*`, `update.*`, `camera.*`

---

## Advanced Configuration

### Custom System Prompt

You can override the default prompt in Extended OpenAI configuration:

1. Find **System Prompt** or **Additional Instructions** field
2. Paste your LCARS persona (from `prompts/lcars_persona.txt`)
3. This makes the LLM respond in Star Trek computer style

**Note:** This may override the persona you set in Open WebUI. You can set it in either place.

### Exposed Entities Patterns

Use wildcards to expose groups:
- `light.*` - All lights
- `light.living_room_*` - Only living room lights
- `sensor.temperature_*` - All temperature sensors

### Context Injection

Add dynamic context to every request:

```
Current time: {{ now().strftime('%H%M hours') }}
Crew aboard: {{ states('sensor.home_status') }}
```

---

## Recommended Next Steps

1. **Import LCARS Persona** (if not already done)
   - Makes responses Star Trek-style
   - See Streamlit guide Integration Step 4

2. **Import n8n Workflows**
   - Enables complex tasks
   - See `docs/N8N_WORKFLOW_IMPORT.md`

3. **Configure Assist Pipeline**
   - Connect voice satellites
   - Enable wake word detection

4. **Test All 12 Tools**
   - Try each LCARS tool to verify it works
   - Check Home Assistant logs for errors

---

## Verification Checklist

Before proceeding, verify:

- ✅ Extended OpenAI Conversation installed via HACS
- ✅ Integration added to Home Assistant
- ✅ API configured with correct base URL
- ✅ All 12 LCARS tools loaded in Spec field
- ✅ Set as conversation agent
- ✅ Simple queries work
- ✅ Tool calls work (LLM can control devices)
- ✅ No errors in Home Assistant logs

---

## Additional Resources

- Extended OpenAI Conversation GitHub: https://github.com/jekalmin/extended_openai_conversation
- Home Assistant Conversation: https://www.home-assistant.io/integrations/conversation/
- Function Calling Guide: https://platform.openai.com/docs/guides/function-calling

---

**Status:** 🎉 If all checks pass, your LCARS Computer can now control your home!

**Next:** Import n8n workflows for advanced automation

Live long and prosper. 🖖
