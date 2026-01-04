# Home Assistant Voice Preview Edition (HAVPE) ESPHome configs

This repo includes example ESPHome YAMLs for the **Home Assistant Voice Preview Edition** hardware.

## Why these YAMLs are wrappers
The Voice Preview Edition uses:
- an XMOS “voice kit” module,
- an audio codec (AIC3204),
- on-device microWakeWord,
- a dial, button, LED ring, mute switch, and headphone jack.

The upstream project (maintained by ESPHome/Home Assistant) contains the correct pin mapping and required external components:
https://github.com/esphome/home-assistant-voice-pe

So the safest approach is to **consume the upstream package** and only override what must differ per device (name/friendly name).

## Files in this repo
- `esphome/home_assistant_voice_pe_SINGLE.yaml` – single device template
- `esphome/home_assistant_voice_pe_living_room.yaml` – example device #1
- `esphome/home_assistant_voice_pe_kitchen.yaml` – example device #2

## Using 2 devices
ESPHome requires **one YAML per device**.

For two Voice Preview Editions:
1. Flash `esphome/home_assistant_voice_pe_living_room.yaml` to device A
2. Flash `esphome/home_assistant_voice_pe_kitchen.yaml` to device B

The important part is each has a unique:
- `esphome.name`
- `esphome.friendly_name`

## Wake word notes
Upstream firmware uses **on-device microWakeWord** models such as:
- `okay_nabu`
- `hey_jarvis`
- `hey_mycroft`

If you want an actual wake word of **"Computer"**, you’ll need a **microWakeWord model** for that phrase.

## Installing a custom microWakeWord model ("Computer")

### What you need
- A microWakeWord model file in the format ESPHome expects (commonly distributed as a `computer.json` model descriptor hosted over HTTPS).
- A URL where the device can download the model at build time (GitHub release URL is common).

### Recommended approach (keep using wrappers): fork the upstream firmware package
Because these YAMLs use an upstream `packages:` include, you **cannot reliably “append”** a model to the upstream `micro_wake_word.models` list without overriding the entire `micro_wake_word:` block.

So the stable approach is:
1. Fork the upstream repository:
	- https://github.com/esphome/home-assistant-voice-pe
2. In your fork, edit the upstream config to add your model under `micro_wake_word:`.
	- In the upstream YAML, find the `micro_wake_word:` block and add something like:

	```yaml
	micro_wake_word:
	  models:
		 - model: https://example.com/releases/download/v1.0/computer.json
			id: computer
	```

	If you want ONLY “Computer”, remove the other models from the list.
3. Update your wrapper YAMLs in this repo to point to your fork instead of the upstream:

	```yaml
	packages:
	  havpe_factory: github://YOUR_GITHUB_USER/home-assistant-voice-pe/home-assistant-voice.factory.yaml@YOUR_BRANCH
	```

4. Flash as usual via ESPHome.

### Alternative approach (more maintenance): copy upstream YAML locally
If you don’t want to fork, you can copy the upstream YAML into your local ESPHome config directory and maintain it yourself. This gives you full control over `micro_wake_word:` but you must manually pull upstream fixes.

## Version requirements
The upstream config currently specifies a minimum ESPHome version (it’s quite new). If compilation fails, update ESPHome.
