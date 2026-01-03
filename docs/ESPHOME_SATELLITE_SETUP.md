# ESPHome Voice Satellite Setup Guide

**Purpose:** Set up voice-controlled satellites with wake word detection
**Difficulty:** ⭐⭐⭐ Moderate (requires hardware and firmware flashing)
**Time Required:** 30-60 minutes per device
**Prerequisites:** ESP32 hardware, Home Assistant running, Assist Pipeline configured

---

## ⚠️ Important: This Step is Optional

Voice satellites are NOT required for LCARS Computer to function. You can:
- ✅ Control your home via Home Assistant web interface
- ✅ Use text commands in the Assist panel
- ✅ Use voice on your phone (Home Assistant Companion app)

**Only proceed if you want dedicated voice hardware with "Computer" wake word.**

---

## Supported Hardware

### Option 1: ESP32-S3-BOX-3 (Recommended)
**Price:** ~$45
**Pros:**
- High-quality microphone with AEC (echo cancellation)
- Built-in 2.4" touchscreen display
- Built-in speaker
- Easy setup

**Cons:**
- More expensive
- Larger footprint

**Where to buy:**
- Aliexpress, Amazon, Seeed Studio

---

### Option 2: M5Stack Atom Echo
**Price:** ~$15
**Pros:**
- Very affordable
- Compact (24x24mm)
- Good microphone
- Built-in RGB LED

**Cons:**
- Tiny speaker (needs external speaker for good audio)
- No display

**Where to buy:**
- M5Stack official store, Amazon

---

### Option 3: Raspberry Pi Zero 2W + ReSpeaker Hat
**Price:** ~$40
**Pros:**
- Flexible (can run additional services)
- Good microphone array (2-4 mic ReSpeaker)
- Can add any speaker

**Cons:**
- Requires assembly
- More complex setup
- Higher power consumption

---

## Part 1: Choose Your Method

### Method 1: Web Flasher (Easiest)
**Best for:** Beginners, one-time setup

**Use:** https://web.esphome.io

**Pros:**
- No software installation required
- Works in Chrome/Edge browser
- Fast

**Cons:**
- Can't customize config easily
- Must reflash for any changes

---

### Method 2: ESPHome Dashboard (Recommended)
**Best for:** Users who want to customize or manage multiple devices

**Use:** ESPHome add-on in Home Assistant or standalone

**Pros:**
- Full customization
- Easy updates
- Manage all devices in one place

**Cons:**
- Requires ESPHome installation
- Slightly more complex

---

## Part 2: Install ESPHome (If Using Dashboard Method)

### Option A: Via Home Assistant Add-on

1. In Home Assistant, go to **Settings → Add-ons**
2. Click **Add-on Store**
3. Search for: `ESPHome`
4. Click **ESPHome** (official add-on)
5. Click **Install**
6. After installation, click **Start**
7. Enable **Show in sidebar**
8. Click **Open Web UI**

### Option B: Via Docker (Standalone)

```bash
docker run -d \
  --name esphome \
  --restart unless-stopped \
  -p 6052:6052 \
  -v "${PWD}/esphome:/config" \
  ghcr.io/esphome/esphome
```

Then open: http://localhost:6052

---

## Part 3: Flash Your Device

### For ESP32-S3-BOX-3

#### Using Web Flasher (Easiest)

1. Go to https://web.esphome.io
2. Click **Connect**
3. Plug in ESP32-S3-BOX-3 via USB-C
4. Select the device from the dialog
5. Click **Install**
6. Choose **Voice Assistant** firmware
7. Wait 3-5 minutes for flash to complete
8. Device will restart

#### Using ESPHome Dashboard

1. Open ESPHome Dashboard
2. Click **+ New Device**
3. Give it a name: `LCARS Voice Satellite - Living Room`
4. Click **Continue**
5. Select **ESP32-S3**
6. Click **Skip** (we'll use our config)
7. Click **Edit** on the new device
8. Delete all content
9. Paste the S3-BOX-3 configuration (see below)
10. Click **Save**
11. Click **Install**
12. Choose **Plug into this computer**
13. Select USB port
14. Click **Install**

**ESP32-S3-BOX-3 Configuration:**

```yaml
esphome:
  name: lcars-satellite-living-room
  friendly_name: LCARS Voice Satellite (Living Room)
  platformio_options:
    board_build.flash_mode: dio

esp32:
  board: esp32-s3-box-3
  framework:
    type: esp-idf

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

  ap:
    ssid: "LCARS Satellite Fallback"
    password: "fallback1234"

api:
  encryption:
    key: !secret api_encryption_key

ota:
  password: !secret ota_password

logger:

# Microphone
i2s_audio:
  - id: i2s_in
    i2s_lrclk_pin: GPIO45
    i2s_bclk_pin: GPIO17

microphone:
  - platform: i2s_audio
    id: box_mic
    adc_type: external
    i2s_din_pin: GPIO16
    channel: left
    sample_rate: 16000
    bits_per_sample: 32bit

# Speaker
speaker:
  - platform: i2s_audio
    id: box_speaker
    i2s_dout_pin: GPIO15
    dac_type: external

# Voice Assistant
voice_assistant:
  microphone: box_mic
  speaker: box_speaker
  use_wake_word: true
  on_listening:
    - light.turn_on:
        id: led
        effect: "Fast Pulse"
        blue: 100%
        red: 0%
        green: 0%
  on_stt_end:
    - light.turn_off: led
  on_end:
    - light.turn_off: led
  on_error:
    - light.turn_on:
        id: led
        effect: none
        red: 100%
        green: 0%
        blue: 0%

# LED indicator
light:
  - platform: esp32_rmt_led_strip
    id: led
    rgb_order: GRB
    pin: GPIO4
    num_leds: 1
    rmt_channel: 0
    chipset: ws2812
    effects:
      - pulse:
          name: "Fast Pulse"
          transition_length: 0.5s
          update_interval: 0.5s
```

---

### For M5Stack Atom Echo

**Configuration:**

```yaml
esphome:
  name: lcars-satellite-kitchen
  friendly_name: LCARS Voice Satellite (Kitchen)

esp32:
  board: m5stack-atom
  framework:
    type: arduino

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

api:
  encryption:
    key: !secret api_encryption_key

ota:
  password: !secret ota_password

logger:

# I2S Audio
i2s_audio:
  i2s_lrclk_pin: GPIO33
  i2s_bclk_pin: GPIO19

microphone:
  - platform: i2s_audio
    id: atom_mic
    i2s_din_pin: GPIO23
    adc_type: external
    pdm: true
    channel: left
    sample_rate: 16000
    bits_per_sample: 32bit

speaker:
  - platform: i2s_audio
    id: atom_speaker
    dac_type: external
    i2s_dout_pin: GPIO22
    channel: left

# Voice Assistant
voice_assistant:
  microphone: atom_mic
  speaker: atom_speaker
  use_wake_word: true
  on_listening:
    - light.turn_on:
        id: led
        effect: "Scan"
        blue: 100%
  on_end:
    - light.turn_off: led

# RGB LED
light:
  - platform: esp32_rmt_led_strip
    id: led
    rgb_order: GRB
    pin: GPIO27
    num_leds: 1
    rmt_channel: 0
    chipset: sk6812
    effects:
      - addressable_scan:
          name: "Scan"
```

---

## Part 4: Configure WiFi Credentials

### Using secrets.yaml

1. In ESPHome dashboard, click **Secrets** (top right)
2. Add these lines:

```yaml
wifi_ssid: "YourWiFiName"
wifi_password: "YourWiFiPassword"
api_encryption_key: "random32characterstring"
ota_password: "somepassword123"
```

3. Save

**Generate random API key:**
```bash
openssl rand -hex 32
```

---

## Part 5: Add to Home Assistant

### Auto-Discovery (Easiest)

1. After flashing, device connects to WiFi
2. Home Assistant auto-discovers it
3. Go to **Settings → Devices & Services**
4. You'll see "Discovered: ESPHome"
5. Click **Configure**
6. Enter the API encryption key from your secrets.yaml
7. Click **Submit**

### Manual Addition

1. Settings → Devices & Services
2. Click **+ Add Integration**
3. Search: `ESPHome`
4. Enter device IP address or hostname
5. Enter API encryption key
6. Submit

---

## Part 6: Configure Assist Pipeline

Now connect the satellite to your LCARS pipeline.

### Step 1: Go to Voice Assistants

1. Settings → Voice assistants
2. Click **Assist** tab

### Step 2: Create LCARS Pipeline (If Not Done)

1. Click **+ Add Pipeline**
2. Configure:
   - **Name:** `LCARS Voice Pipeline`
   - **Language:** `English`
   - **Wake Word:** `tcp://host.docker.internal:10400` (openWakeWord)
   - **Speech-to-Text:** `tcp://host.docker.internal:10300` (Whisper)
   - **Conversation:** `Extended OpenAI Conversation` (your LLM)
   - **Text-to-Speech:** `tcp://host.docker.internal:10200` (Piper)
3. Click **Create**

### Step 3: Assign Satellite to Pipeline

1. Settings → Devices & Services → ESPHome
2. Click on your satellite device
3. Find **Voice assistant** section
4. Select **LCARS Voice Pipeline**
5. Save

---

## Part 7: Test Your Voice Satellite

### Test 1: Wake Word Detection

1. Stand near the satellite
2. Say: **"Computer"** (clearly, not too fast)
3. Expect:
   - LED lights up (blue on S3-BOX, scan effect on Atom)
   - Device listens for command

### Test 2: Full Command

1. Say: "**Computer**" (wait for LED)
2. Say: "**Turn on the living room lights**"
3. Expect:
   - LED turns off
   - Whisper processes speech → text
   - Extended OpenAI + LLM processes command
   - Lights turn on
   - Piper generates TTS response
   - Response plays on satellite speaker

### Test 3: LCARS Persona

1. Say: "Computer, what time is it?"
2. Expect response in LCARS style:
   - "Current time: 1430 hours"
   - NOT: "It's 2:30 PM"

---

## Troubleshooting

### Issue: Wake word not detected

**Possible causes:**
1. **Too quiet** - Speak louder or move closer
2. **Background noise** - Reduce ambient noise
3. **Wrong wake word** - Say exactly "Computer"
4. **Microphone muted** - Check hardware

**Solutions:**
1. Adjust wake word sensitivity in ESPHome config:
   ```yaml
   voice_assistant:
     # ... other config
     sensitivity: 0.5  # Lower = more sensitive (0.0 - 1.0)
   ```
2. Check ESPHome logs:
   ```
   ESPHome Dashboard → Device → Logs
   ```

---

### Issue: Speech not transcribed correctly

**Cause:** Whisper model too small or network issues

**Solutions:**
1. Use larger Whisper model in Docker config
2. Check network latency to Whisper service
3. Speak more clearly and slowly

---

### Issue: No response audio

**Cause:** Piper not configured or speaker issue

**Solutions:**
1. Check Piper is running:
   ```bash
   docker ps | grep piper
   ```
2. Test Piper directly in Home Assistant:
   ```
   Developer Tools → Services → tts.speak
   ```
3. Check speaker volume on device

---

### Issue: Device keeps disconnecting

**Causes:**
1. **Weak WiFi signal**
2. **Power supply insufficient**
3. **Network stability**

**Solutions:**
1. Move device closer to WiFi router
2. Use better USB power supply (2A minimum)
3. Set static IP for device in router

---

### Issue: "Connection refused" in logs

**Cause:** Wrong pipeline endpoint URLs

**Solution:**
Verify in Assist Pipeline configuration:
- Wake Word: `tcp://host.docker.internal:10400` (NOT localhost)
- STT: `tcp://host.docker.internal:10300`
- TTS: `tcp://host.docker.internal:10200`

---

## Advanced Configuration

### Custom Wake Word

To use a different wake word (requires training):
1. Train model with Porcupine or openWakeWord
2. Replace wake word model file
3. Update ESPHome config

**Default:** "Computer" (Star Trek style)
**Alternatives:** "Jarvis", "Alexa", "OK Google" (if models available)

---

### Multiple Satellites

For whole-home coverage:

1. Flash multiple devices
2. Give each a unique name
3. Add all to Home Assistant
4. Assign all to same LCARS pipeline
5. Place strategically throughout home

**Recommended placement:**
- Living room
- Kitchen
- Bedroom
- Home office

---

### Voice Feedback Customization

Change LED colors/effects:

```yaml
voice_assistant:
  on_listening:  # Blue pulse
    - light.turn_on:
        id: led
        blue: 100%
        red: 0%
        green: 0%
  on_thinking:  # Yellow solid (while LLM processes)
    - light.turn_on:
        id: led
        red: 100%
        green: 100%
        blue: 0%
  on_tts_start:  # Green solid (while speaking)
    - light.turn_on:
        id: led
        green: 100%
        red: 0%
        blue: 0%
  on_end:  # Turn off
    - light.turn_off: led
```

---

## Performance Optimization

### Faster Wake Word Detection

1. Use lighter openWakeWord model
2. Reduce detection window
3. Use edge TPU if available

### Faster Speech Recognition

1. Use Whisper `tiny` model (less accurate but faster)
2. Ensure GPU acceleration for Whisper
3. Use lower sample rate

### Better Audio Quality

1. Use higher quality TTS voice
2. Increase speaker volume in ESPHome
3. Add equalizer settings

---

## Verification Checklist

Before considering setup complete:

- ✅ Device flashed with ESPHome firmware
- ✅ Connected to WiFi
- ✅ Added to Home Assistant
- ✅ Assigned to LCARS Voice Pipeline
- ✅ Wake word "Computer" detected consistently
- ✅ Voice commands processed correctly
- ✅ TTS responses play on satellite speaker
- ✅ LED feedback working
- ✅ No frequent disconnections

---

## Maintenance

### Update Firmware

1. Make changes to ESPHome config
2. Click **Install** → **Wirelessly**
3. Device updates over WiFi (OTA)

### Check Logs

- ESPHome Dashboard → Device → Logs
- Home Assistant → Settings → System → Logs (filter by ESPHome)

### Backup Configuration

Save your ESPHome YAML files:
```bash
cp esphome/*.yaml backup/
```

---

## Next Steps

1. **Test Thoroughly**
   - Try various commands
   - Test in different rooms
   - Verify response accuracy

2. **Add More Satellites**
   - Expand to other rooms
   - Create whole-home voice control

3. **Customize Persona**
   - Refine LCARS responses
   - Add ship-specific commands

---

## Additional Resources

- ESPHome Voice Assistant: https://esphome.io/components/voice_assistant.html
- Wyoming Protocol: https://www.home-assistant.io/integrations/wyoming/
- M5Stack Atom Echo Guide: https://www.home-assistant.io/voice_control/thirteen-usd-voice-remote/
- ESP32-S3-BOX-3 Docs: https://github.com/espressif/esp-box/tree/master/docs

---

**Status:** 🎤 With voice satellites set up, you can now command your LCARS Computer hands-free!

Live long and prosper. 🖖
