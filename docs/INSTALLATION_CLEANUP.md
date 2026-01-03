# LCARS Computer - Installation Cleanup Guide

**Date:** 2026-01-02

## Overview

The LCARS Computer installation system now includes a comprehensive cleanup feature that allows you to completely remove the installation and roll back all changes. This is useful for:

- **Fresh Start**: Remove everything and reinstall from scratch
- **Troubleshooting**: Clear corrupted data or broken configurations
- **Testing**: Quickly reset between test installations
- **Complete Removal**: Uninstall LCARS Computer completely

## Access

Navigate to: **Operations** → **Common Operations** → **🗑️ Cleanup** tab

## Cleanup Options

The cleanup system offers granular control over what gets removed:

### 1. 🐳 Stop and Remove All LCARS Containers

**Default:** ✅ Checked

**What it does:**
- Stops all running LCARS containers
- Removes container instances
- Preserves images and volumes

**Command executed:**
```bash
docker compose down
```

**Safe?** Yes - containers can be recreated without data loss

---

### 2. 💾 Delete All Volumes (⚠️ ALL DATA LOSS)

**Default:** ❌ Unchecked

**What it does:**
- Removes ALL data stored in volumes
- Deletes the `docker/volumes/` directory
- **Permanent data loss** including:
  - Home Assistant configurations
  - n8n workflows
  - PostgreSQL databases
  - Ollama models (can be several GB)
  - Redis cache
  - All service configurations

**Commands executed:**
```bash
docker compose down -v
rm -rf docker/volumes/*
```

**Safe?** ⚠️ **NO** - This permanently deletes all your data!

**Use when:**
- You want to start completely fresh
- Testing and don't need to preserve data
- Troubleshooting corrupted databases

---

### 3. 🖼️ Remove Docker Images

**Default:** ❌ Unchecked

**What it does:**
- Removes all Docker images used by LCARS
- Frees up disk space (can be several GB)
- Images can be re-downloaded when needed

**Command executed:**
```bash
docker compose down --rmi all
```

**Safe?** Yes - images can be re-downloaded (takes time)

**Use when:**
- You need to free up disk space
- You're completely removing LCARS
- You want to force fresh image downloads

---

### 4. 🌐 Remove Docker Networks

**Default:** ❌ Unchecked

**What it does:**
- Removes the `lcars_network` Docker network
- Cleans up network configuration

**Command executed:**
```bash
docker network rm lcars_network
```

**Safe?** Yes - networks are recreated automatically

---

### 5. 🔐 Delete .env File

**Default:** ❌ Unchecked

**What it does:**
- Removes `docker/.env` file
- Deletes:
  - Database passwords
  - Encryption keys
  - API tokens
  - All environment variables

**Command executed:**
```bash
rm docker/.env
```

**Safe?** ⚠️ **NO** - You'll lose all secrets and need to regenerate them

**Use when:**
- Starting completely fresh
- Environment file is corrupted
- You want to regenerate all secrets

⚠️ **Warning:** If you have Home Assistant tokens or other manually-configured secrets, back them up first!

---

### 6. 📝 Delete Generated Config Files

**Default:** ❌ Unchecked

**What it does:**
- Removes `docker/deployment_config.json`
- Removes `docker/docker-compose.override.yml`
- Clears custom deployment configuration

**Commands executed:**
```bash
rm docker/deployment_config.json
rm docker/docker-compose.override.yml
```

**Safe?** Yes - these are regenerated during deployment

**Use when:**
- Switching from custom to standard deployment
- Custom configuration is broken
- Want to reconfigure services

---

### 7. 📄 Clear Installation Logs

**Default:** ❌ Unchecked

**What it does:**
- Removes all installation log files from `logs/install_*.log`
- Clears historical installation records

**Command executed:**
```bash
rm logs/install_*.log
```

**Safe?** Yes - logs are informational only

---

## How to Use

### Step 1: Select What to Remove

Check the boxes for items you want to remove. The default is to only remove containers (safest option).

**Recommended presets:**

**Quick Reset** (keep data):
- ✅ Containers
- ❌ Volumes
- ❌ Images
- ❌ Everything else

**Fresh Install** (delete everything):
- ✅ Containers
- ✅ Volumes
- ✅ Images
- ✅ Networks
- ✅ .env file
- ✅ Config files
- ✅ Logs

**Troubleshooting** (keep volumes):
- ✅ Containers
- ❌ Volumes (keep data)
- ✅ Images (force fresh download)
- ✅ Networks
- ✅ Config files

### Step 2: Preview Actions

Click on **📋 Preview Cleanup Actions** expander to see exactly what commands will be executed.

Example preview:
```bash
# Stop and remove all containers
docker compose down

# Remove all volumes (DATA LOSS)
docker compose down -v
rm -rf docker/volumes/*

# Remove Docker images
docker compose down --rmi all

# Remove .env file
rm docker/.env

# Remove generated config files
rm docker/deployment_config.json
rm docker/docker-compose.override.yml
```

### Step 3: Confirm Deletion

To prevent accidental data loss, you must type **exactly**:

```
DELETE EVERYTHING
```

in the confirmation field.

⚠️ **Case-sensitive!** Must be all caps.

### Step 4: Execute Cleanup

Click **🗑️ Execute Cleanup** button.

The system will:
1. Execute all selected cleanup operations
2. Show progress and results for each operation
3. Display success/failure status
4. Reset session state
5. Allow you to start fresh

### Step 5: Results

You'll see detailed results for each operation:

```
✅ Containers/Volumes/Images: Removed
✅ .env file: Removed
✅ Config files: Removed
✅ Log files: Cleared

🎉 Cleanup completed! LCARS Computer has been removed.
💡 You can now run the installation again from the beginning.
```

Each result has an expandable details section showing the command output.

---

## What Gets Preserved

The cleanup system **ONLY** removes items created by the LCARS installation. It **NEVER** touches:

✅ **Preserved:**
- Your git repository and source code
- `docker-compose.yml` and other Docker compose files
- `homeassistant/config/` source files
- `n8n/workflows/` source JSON files
- `scripts/` directory
- `docs/` directory
- Any files outside the `docker/volumes/` directory
- Any files you created manually
- Non-LCARS Docker containers
- Non-LCARS Docker networks
- Non-LCARS Docker images

❌ **Removed only if selected:**
- Docker containers created by LCARS
- Data in `docker/volumes/` (if "Delete all volumes" checked)
- Docker images pulled by LCARS (if "Remove Docker images" checked)
- `docker/.env` (if "Delete .env file" checked)
- Generated config files (if "Delete generated config files" checked)

---

## Common Scenarios

### Scenario 1: "I want to test the installation again"

**Solution:**
1. Check: Containers
2. Uncheck: Everything else
3. Confirm and execute
4. Re-run deployment

**Result:** Fresh containers, keeps all data (Home Assistant configs, n8n workflows, Ollama models)

---

### Scenario 2: "My database is corrupted"

**Solution:**
1. Check: Containers, Volumes
2. Uncheck: Images, Networks, .env, Config files
3. Confirm and execute
4. Re-run configuration and deployment

**Result:** Fresh database, fresh containers, regenerates schemas

---

### Scenario 3: "I want to start completely from scratch"

**Solution:**
1. Check: ALL options
2. Confirm and execute
3. Start installation from Welcome tab

**Result:** Complete fresh installation as if you never installed LCARS

---

### Scenario 4: "I'm running out of disk space"

**Solution:**
1. Check: Containers, Images
2. Check: Volumes (if you don't need the data)
3. Confirm and execute

**Result:** Frees up several GB of disk space

---

### Scenario 5: "I want to switch from Custom to Standard deployment"

**Solution:**
1. Check: Containers, Config files
2. Uncheck: Volumes (to keep data), Images, .env
3. Confirm and execute
4. Select Standard Deployment mode
5. Re-deploy

**Result:** Standard deployment with existing data preserved

---

## Safety Features

### Confirmation Required

You **MUST** type `DELETE EVERYTHING` exactly to enable the cleanup button. This prevents:
- Accidental clicks
- Fat-finger mistakes
- Confusion with other actions

### Default = Safest

By default, only "Stop and remove containers" is checked. This is the safest option and won't cause data loss.

### Preview Before Execute

The preview expander shows exactly what will happen. Review this before confirming!

### Detailed Results

After cleanup, you see exactly what succeeded and what failed, with full command output.

### Session State Reset

After cleanup, your Streamlit session state is reset, preventing stale configuration from interfering with a fresh installation.

---

## Troubleshooting

### "Permission denied when removing volumes"

**Cause:** Some volume files are owned by root

**Solution:**
```bash
# Run manual cleanup with sudo
cd docker
sudo rm -rf volumes/*
```

### "Network is in use"

**Cause:** Other containers are using the network

**Solution:**
```bash
# Check what's using it
docker network inspect lcars_network

# Stop those containers first
docker stop <container_name>

# Then run cleanup again
```

### "Cannot remove image: image is being used"

**Cause:** Container still exists using the image

**Solution:** Enable "Stop and remove containers" before removing images

### "Cleanup completed but data still exists"

**Cause:** Volume deletion may fail silently on Windows

**Solution:**
```bash
# Manually remove on Windows
cd docker
rmdir /s volumes
mkdir volumes
```

---

## Best Practices

### 1. Backup Before Cleanup

If you have important data (Home Assistant configs, n8n workflows), back them up first:

```bash
# Backup script
python scripts/backup.py
```

Or manually:
```bash
cp -r docker/volumes/homeassistant backup/
cp -r docker/volumes/n8n backup/
cp docker/.env backup/
```

### 2. Check What's Running

Before cleanup, verify what's actually running:

```bash
docker compose ps
docker volume ls
docker images
```

### 3. Incremental Cleanup

Try the minimal cleanup first:
1. Just containers
2. If problem persists, add config files
3. If still broken, add volumes
4. Last resort: everything

### 4. Note Your Secrets

If deleting `.env`, save important values:
- Home Assistant access token
- Any manually-configured API keys
- Custom passwords you want to reuse

### 5. Verify Cleanup

After cleanup, verify it worked:

```bash
docker compose ps       # Should show nothing
docker volume ls        # Should not show LCARS volumes (if deleted)
docker images          # Should not show LCARS images (if deleted)
ls docker/volumes      # Should be empty (if deleted)
```

---

## After Cleanup

Once cleanup completes:

1. **Session State Reset**: Your installation progress is cleared
2. **Fresh Start**: Navigate to "Welcome" tab to start over
3. **Or Exit**: Close the installer if you're done

You can immediately start a new installation without restarting the Streamlit app.

---

## Cleanup Command Reference

For manual cleanup outside the UI:

```bash
# Full cleanup (everything)
cd docker
docker compose down -v --rmi all
docker network rm lcars_network
rm .env
rm deployment_config.json
rm docker-compose.override.yml
rm -rf volumes/*
rm ../logs/install_*.log

# Minimal cleanup (containers only)
cd docker
docker compose down

# Cleanup with data preservation
cd docker
docker compose down --rmi all
rm deployment_config.json
rm docker-compose.override.yml
```

---

## Frequently Asked Questions

### Q: Will this delete my code?

**A:** No! Cleanup only removes Docker containers, volumes, images, and generated config files. Your git repository and source code are never touched.

### Q: Can I recover deleted volumes?

**A:** No, volume deletion is permanent. Always backup important data first.

### Q: Do I need to delete everything to reinstall?

**A:** No! Usually just removing containers is enough. Only delete volumes if you want to start fresh with no data.

### Q: Will this affect other Docker projects?

**A:** No, cleanup is scoped to LCARS-specific resources only.

### Q: How much disk space will I free up?

**A:**
- Containers: ~100 MB
- Images: 2-5 GB
- Volumes: 5-20 GB (depending on Ollama models)
- Total: Up to 25 GB

### Q: Can I cancel after clicking "Execute Cleanup"?

**A:** No, once execution starts, it runs to completion. Double-check your selections first!

---

## Status

✅ **IMPLEMENTED** - Complete installation cleanup system is production-ready.

**Location:** `lcars_guide.py` → Operations → Common Operations → Cleanup tab

---

Live long and prosper. 🖖
