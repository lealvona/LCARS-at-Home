# HACS (Home Assistant Community Store) - Installation Guide

**Purpose:** Install HACS to access the Extended OpenAI Conversation integration
**Difficulty:** ⭐⭐ Moderate (requires terminal access)
**Time Required:** 10 minutes
**Prerequisites:** Home Assistant running and accessible

---

## What is HACS?

HACS (Home Assistant Community Store) is a custom repository manager that gives you access to thousands of community-created integrations, themes, and add-ons for Home Assistant.

**Why you need it:** The Extended OpenAI Conversation integration (which allows the LLM to control your home) is not in the official Home Assistant store. It's only available through HACS.

---

## Installation Methods

### Method 1: Terminal & SSH Add-on (Recommended)

**Best for:** Users who prefer the Home Assistant UI

#### Step 1: Install Terminal & SSH Add-on

1. In Home Assistant, go to **Settings** (gear icon in sidebar)
2. Click **Add-ons**
3. Click **Add-on Store** (bottom right)
4. Search for: `Terminal & SSH`
5. Click on **Terminal & SSH** (official add-on by Home Assistant)
6. Click **Install**
7. Wait for installation to complete (~1-2 minutes)

#### Step 2: Start and Configure Terminal

1. After installation, click **Start**
2. Enable **Show in sidebar** (toggle switch)
3. Click **Open Web UI** or find **Terminal** in the sidebar

#### Step 3: Run HACS Installation Script

1. In the terminal window, paste this command:

```bash
wget -O - https://get.hacs.xyz | bash -
```

2. Press **Enter**
3. You'll see output like this:

```
Connecting to get.hacs.xyz...
Downloading HACS...
Installing HACS to /config/custom_components/hacs/
HACS installation complete!
```

4. Wait for "installation complete" message

#### Step 4: Restart Home Assistant

1. Go to **Settings → System**
2. Click **Restart** (top right button)
3. Confirm restart
4. Wait 2-3 minutes for Home Assistant to fully restart
5. Refresh your browser

#### Step 5: Verify Installation

1. Go to **Settings → Devices & Services**
2. Click **+ Add Integration** (bottom right)
3. Search for: `HACS`
4. If you see it, HACS is installed! ✅

---

### Method 2: Docker Exec Command (Advanced)

**Best for:** Users comfortable with command line

#### Step 1: Execute Installation in Container

Open your terminal/command prompt and run:

**Linux/macOS:**
```bash
docker exec -it LCARS-homeassistant bash -c "wget -O - https://get.hacs.xyz | bash -"
```

**Windows (PowerShell):**
```powershell
docker exec -it LCARS-homeassistant bash -c "wget -O - https://get.hacs.xyz | bash -"
```

#### Step 2: Restart Container

**From project directory:**
```bash
cd docker
docker compose restart homeassistant
```

**Or using Docker directly:**
```bash
docker restart homeassistant
```

#### Step 3: Wait for Restart

Wait 2-3 minutes for Home Assistant to fully start, then refresh your browser.

#### Step 4: Verify Installation

Same as Method 1, Step 5 above.

---

## Troubleshooting

### Issue: "wget: command not found"

**Cause:** Your Home Assistant container is missing wget

**Solution:**
```bash
docker exec -it LCARS-homeassistant bash -c "apk add wget && wget -O - https://get.hacs.xyz | bash -"
```

---

### Issue: "Permission denied" errors during installation

**Cause:** File permission issues in /config

**Solution:**
1. Check Home Assistant logs: `docker compose logs homeassistant`
2. Try running the installation again
3. If persistent, check volume permissions:
   ```bash
   ls -la docker/volumes/homeassistant/
   ```

---

### Issue: HACS doesn't appear after restart

**Possible causes:**
1. **Restart not complete** - Wait another 2 minutes and refresh
2. **Installation failed** - Check logs:
   ```bash
   docker compose logs homeassistant | grep -i hacs
   ```
3. **Cache issue** - Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)

---

### Issue: "Integration not found" when searching for HACS

**Solution:** HACS doesn't auto-configure. You need to add it manually:

1. Go to **Settings → Devices & Services**
2. Click **+ Add Integration**
3. Type exactly: `HACS` (case-sensitive)
4. Click on it when it appears
5. Follow the GitHub authentication flow
6. Authorize HACS to access your GitHub account (free)

---

## Post-Installation: Configure HACS

### First-Time Setup

1. Go to **Settings → Devices & Services**
2. Click **+ Add Integration**
3. Search for and select **HACS**
4. You'll be prompted to authenticate with GitHub:
   - Click the link to GitHub
   - Enter the code shown
   - Authorize HACS
5. Back in Home Assistant, check the boxes:
   - ✅ I have read and understand the above
   - ✅ I know how to access Home Assistant logs
6. Click **Submit**

### GitHub Account Requirement

HACS requires a GitHub account (free) to:
- Track which custom integrations you've installed
- Check for updates
- Download integration files

**Don't have a GitHub account?**
1. Go to https://github.com/signup
2. Create a free account (takes 2 minutes)
3. Return to HACS setup

---

## What's Next?

After HACS is installed and configured, you can:

1. **Install Extended OpenAI Conversation**
   - See: `docs/EXTENDED_OPENAI_SETUP.md`
   - This is the critical integration for LCARS Computer

2. **Explore other integrations**
   - HACS → Integrations
   - Browse thousands of community add-ons

3. **Keep HACS updated**
   - HACS will notify you of updates
   - Update from Settings → Devices & Services → HACS

---

## FAQ

### Q: Is HACS safe?

**A:** Yes. HACS is maintained by the community and used by hundreds of thousands of Home Assistant users. It doesn't execute code automatically - you choose what to install.

### Q: Will HACS slow down my Home Assistant?

**A:** No. HACS itself is lightweight. Only the integrations you install will affect performance.

### Q: Can I uninstall HACS later?

**A:** Yes, but you'll lose access to any integrations you installed through it (like Extended OpenAI Conversation). Those would stop working.

### Q: Do I need to keep the Terminal & SSH add-on running?

**A:** No. After installing HACS, you can stop the Terminal & SSH add-on if you don't need it for other purposes.

### Q: What if the installation script fails?

**A:** Check the troubleshooting section above, or install HACS manually:
- Manual installation guide: https://hacs.xyz/docs/setup/download

---

## Verification Checklist

Before proceeding to Extended OpenAI setup, verify:

- ✅ HACS appears in Settings → Devices & Services
- ✅ You can click on HACS and see the configuration panel
- ✅ HACS sidebar entry appears (looks like a shopping bag icon)
- ✅ You can browse HACS → Integrations without errors

If all checks pass, you're ready to install Extended OpenAI Conversation!

---

## Additional Resources

- Official HACS Documentation: https://hacs.xyz/docs/configuration/basic
- HACS GitHub: https://github.com/hacs/integration
- Home Assistant Community: https://community.home-assistant.io/c/third-party/hacs

---

**Next Step:** Install Extended OpenAI Conversation via HACS

See: `docs/EXTENDED_OPENAI_SETUP.md`

Live long and prosper. 🖖
