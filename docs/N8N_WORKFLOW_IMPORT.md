# n8n Workflow Import Guide

**Purpose:** Import pre-built LCARS workflows for voice processing and automation
**Difficulty:** ⭐ Easy (straightforward file imports)
**Time Required:** 10 minutes
**Prerequisites:** n8n container running and accessible

---

## What is n8n?

n8n is a workflow automation tool that acts as the "nervous system" of your LCARS Computer. It:
- Orchestrates complex multi-step tasks
- Implements fire-and-forget patterns for long-running jobs
- Connects Home Assistant to the LLM
- Handles webhook triggers from Extended OpenAI Conversation

---

## The 4 LCARS Workflows

### 1. Voice Command Handler
**File:** `voice_command_handler.json`
**Purpose:** Main voice processing pipeline

**What it does:**
- Receives voice command text from Home Assistant
- Fetches current device states for context
- Sends request to LLM with LCARS persona
- Executes Home Assistant service calls
- Returns response for TTS

**Triggered by:** Extended OpenAI Conversation webhook

---

### 2. Red Alert Protocol
**File:** `red_alert_protocol.json`
**Purpose:** Emergency mode activation

**What it does:**
- Activates red flashing lights throughout home
- Plays alert sound (if configured)
- Locks all doors
- Sends notifications
- Sets emergency scene

**Triggered by:** Voice command "Computer, activate Red Alert" or manual

---

### 3. Status Report
**File:** `status_report.json`
**Purpose:** Comprehensive ship/home status query

**What it does:**
- Gathers data from all systems:
  - Environmental (temperature, humidity)
  - Lighting (which lights are on)
  - Security (locks, doors, windows)
  - Occupancy (who's home)
  - Energy usage
- Formats as Star Trek-style status report
- Returns to LLM for voice response

**Triggered by:** Voice command "Computer, ship status" or "status report"

---

### 4. Deep Research Agent
**File:** `deep_research_agent.json`
**Purpose:** Long-running research tasks with fire-and-forget pattern

**What it does:**
- Receives research query
- Immediately returns acknowledgment (prevents timeout)
- Continues processing in background
- Performs web searches, data analysis
- When complete, announces results via TTS

**Triggered by:** Extended OpenAI tool call `call_n8n_workflow`

**Fire-and-Forget:**
- User asks: "Research the best smart thermostat for my home"
- Workflow responds: "Acknowledged. Beginning research. I will announce findings when complete."
- User continues using the system
- 5 minutes later: "Research complete. Based on analysis of 12 sources..."

---

## Part 1: Access n8n

### Step 1: Open n8n Web Interface

**Default URL:** http://localhost:5678

If using custom deployment, check your configuration:
```bash
# Check n8n port
docker ps | grep n8n
```

### Step 2: Create Account (First Time)

1. Enter your email address
2. Choose a password
3. Click **Sign up**

**Note:** First user becomes admin. This is a local install, so use any credentials you'll remember.

### Step 3: Skip Onboarding

1. n8n may show a tutorial
2. Click **Skip** or **Get Started**
3. You'll arrive at an empty workflow canvas

---

## Part 2: Import Workflows

You'll import all 4 workflows using the same process.

### Workflow Locations

**Full paths:**
- `D:\Documents\python_projects\lcars-computer\n8n\workflows\voice_command_handler.json`
- `D:\Documents\python_projects\lcars-computer\n8n\workflows\red_alert_protocol.json`
- `D:\Documents\python_projects\lcars-computer\n8n\workflows\status_report.json`
- `D:\Documents\python_projects\lcars-computer\n8n\workflows\deep_research_agent.json`

**Relative from project root:**
```
n8n/workflows/
  ├── voice_command_handler.json
  ├── red_alert_protocol.json
  ├── status_report.json
  └── deep_research_agent.json
```

### Import Process (Repeat for Each File)

#### Step 1: Open Import Dialog

1. Click **Workflows** in the left sidebar (if not already there)
2. Click the **⋮** menu (three dots at top right)
3. Select **Import from File**

#### Step 2: Select File

1. File browser opens
2. Navigate to `n8n/workflows/` in your LCARS Computer project directory
3. Select one of the JSON files
4. Click **Open**

#### Step 3: Review Workflow

1. n8n loads the workflow onto the canvas
2. You'll see nodes (boxes) connected by lines
3. Don't worry about understanding it all yet!

#### Step 4: Save Workflow

1. Click **Save** button (top right)
2. Workflow is now saved in your n8n database

#### Step 5: Activate Workflow

1. Find the toggle switch at top (usually shows "Inactive")
2. Click it to set to **Active**
3. The workflow is now running and listening for triggers!

#### Step 6: Repeat

Go back to Step 1 and import the next workflow. Repeat until all 4 are imported.

---

## Part 3: Verify Imports

### Check Workflow List

1. Click **Workflows** in sidebar
2. You should see 4 workflows listed:
   - Voice Command Handler (Active)
   - Red Alert Protocol (Active)
   - Status Report (Active)
   - Deep Research Agent (Active)

### Check for Errors

1. Click on each workflow name
2. Look for red error indicators on nodes
3. If you see errors, see Troubleshooting section below

---

## Part 4: Configuration (If Needed)

Most workflows work out-of-the-box, but you may need to configure:

### Voice Command Handler

**May need to update:**
- **Home Assistant URL:** Should be `http://host.docker.internal:8123`
- **Access Token:** Automatically loaded from environment variable

**To check:**
1. Open workflow
2. Find "Home Assistant" node (usually orange)
3. Click on it
4. Verify **Base URL** is correct
5. Verify **Access Token** shows `={{$env.HA_ACCESS_TOKEN}}`

### Deep Research Agent

**May need to configure:**
- **TTS settings:** Which media player to announce on
- **Search API:** If using external search services

---

## Part 5: Testing

### Test 1: Voice Command Handler

**Via Home Assistant Assist:**
1. In Home Assistant, open Assist (microphone icon)
2. Type: "Turn on the living room lights"
3. LLM should process and execute the command

**Expected flow:**
- Home Assistant → Extended OpenAI → n8n webhook → Voice Command Handler → Ollama → Execute action

### Test 2: Status Report

1. In Home Assistant Assist, type: "Computer, ship status"
2. Expect detailed status report

**Check n8n execution:**
1. In n8n, click **Executions** (left sidebar)
2. You should see "Status Report" execution
3. Click on it to see the flow

### Test 3: Red Alert

1. Say: "Computer, activate Red Alert"
2. Expect lights to turn red (if configured)
3. Check Executions in n8n

### Test 4: Deep Research (Advanced)

**Note:** This requires additional configuration for web search APIs.

---

## Troubleshooting

### Issue: "Credentials not found" errors

**Cause:** Workflow references credentials that don't exist in your n8n instance

**Solution:**
1. Click on the erroring node
2. Click **Select Credential**
3. Click **Create New**
4. Enter your credentials (e.g., Home Assistant token)
5. Save

---

### Issue: "Cannot connect to Home Assistant"

**Cause:** Wrong URL or missing access token

**Solution:**
1. Verify Home Assistant is running:
   ```bash
   docker ps | grep homeassistant
   ```
2. Check n8n can reach it:
   ```bash
   docker exec n8n ping -c 1 host.docker.internal
   ```
3. Verify `HA_ACCESS_TOKEN` environment variable is set:
   ```bash
   docker exec n8n env | grep HA_ACCESS_TOKEN
   ```

---

### Issue: Workflow shows "Active" but doesn't trigger

**Possible causes:**
1. **Webhook URL not configured in Home Assistant**
2. **Extended OpenAI not calling the webhook**
3. **Firewall blocking**

**Solution:**
1. Check webhook trigger node
2. Copy the webhook URL (usually `http://localhost:5678/webhook/voice-command`)
3. Verify this URL is configured in Extended OpenAI Conversation tools

---

### Issue: "Function not found" in workflow nodes

**Cause:** Workflow uses JavaScript code that's not compatible with your n8n version

**Solution:**
1. Update n8n to latest version:
   ```bash
   docker compose pull n8n
   docker compose up -d n8n
   ```
2. Or edit the workflow and update the function code

---

## Advanced: Customizing Workflows

### Edit a Workflow

1. Click **Workflows** → Select workflow
2. Click on any node to edit it
3. Modify settings
4. Click **Save**
5. Test the changes

### Common Customizations

#### Change TTS Voice

In announcement nodes:
1. Find "Piper TTS" or "TTS" node
2. Change voice model
3. Adjust speech rate

#### Add/Remove Devices from Status Report

1. Open "Status Report" workflow
2. Find "Gather Device States" node
3. Add/remove entity queries
4. Update formatting logic

#### Customize Red Alert Behavior

1. Open "Red Alert Protocol" workflow
2. Find scene activation or light control nodes
3. Change colors, effects, or which lights flash
4. Add/remove notification steps

---

## Workflow Maintenance

### Check Execution History

1. Click **Executions** in sidebar
2. See all workflow runs
3. Click on any execution to debug
4. Green = success, Red = error

### View Logs

```bash
docker compose logs n8n
```

### Update Workflows

When LCARS Computer releases new workflow versions:
1. Download new JSON files
2. Import them (will create new versions)
3. Deactivate old versions
4. Activate new versions

---

## Integration with Extended OpenAI

### How Workflows are Triggered

**Method 1: Webhook (Voice Command Handler)**
- Extended OpenAI calls n8n webhook URL
- Passes voice command text
- n8n processes and returns result

**Method 2: Function Call (Deep Research)**
- Extended OpenAI tool: `call_n8n_workflow`
- Triggers specific workflow by name
- Returns immediately, continues in background

### Webhook Configuration

**In Extended OpenAI tool spec:**
```yaml
- spec:
    name: call_n8n_workflow
    ...
  function:
    type: rest_command
    rest_command: n8n_async_task
    data:
      task: "{{ workflow }}"
      callback_entity: "tts.piper"
```

**n8n webhook URL format:**
```
http://host.docker.internal:5678/webhook/<workflow-name>
```

---

## Verification Checklist

Before proceeding, verify:

- ✅ n8n accessible at http://localhost:5678
- ✅ All 4 workflows imported
- ✅ All workflows showing "Active" status
- ✅ No error indicators on nodes
- ✅ Voice Command Handler responds to test command
- ✅ Executions appearing in history
- ✅ Home Assistant can reach n8n webhooks

---

## Next Steps

1. **Test Each Workflow**
   - Try voice commands that trigger each one
   - Verify they execute correctly

2. **Configure Assist Pipeline**
   - Connect voice satellites
   - Enable wake word detection
   - See `docs/ESPHOME_SATELLITE_SETUP.md`

3. **Customize for Your Home**
   - Edit workflows to match your devices
   - Add custom scenes and automations

---

## Additional Resources

- n8n Documentation: https://docs.n8n.io
- n8n Community: https://community.n8n.io
- Workflow Templates: https://n8n.io/workflows

---

**Status:** 🎉 With workflows imported, your LCARS Computer can now handle complex automation tasks!

Live long and prosper. 🖖
