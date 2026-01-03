# LCARS Sound Effects

This directory contains audio files for the LCARS Computer voice assistant.

## Required Files

Place the following audio files in this directory:

| Filename | Purpose | Description |
|----------|---------|-------------|
| `lcars_chirp.wav` | Wake word acknowledgment | The distinctive "chirp" sound when the computer recognizes "Computer" |
| `lcars_processing.wav` | Processing indicator | Played while the system is thinking |
| `red_alert.wav` | Red Alert klaxon | Emergency alarm sound |
| `yellow_alert.wav` | Yellow Alert tone | Caution alert sound |
| `doorbell.wav` | Doorbell notification | Chime for door sensor triggers |
| `comm_open.wav` | Communication open | Intercom activation sound |
| `comm_close.wav` | Communication closed | Intercom deactivation sound |
| `confirm.wav` | Action confirmed | Success acknowledgment tone |
| `error.wav` | Error notification | Error/failure indication tone |

## File Format

All audio files should be:
- Format: WAV (PCM)
- Sample rate: 44100 Hz or 48000 Hz
- Channels: Mono or Stereo
- Bit depth: 16-bit

## Sources for Star Trek Sounds

Due to copyright, we cannot distribute official Star Trek sounds. You can:

1. **Create your own** - Use audio synthesis tools to create similar tones
2. **TrekCore** - https://trekcore.com/audio/ (for personal use reference)
3. **Freesound.org** - Search for "sci-fi computer" sounds with CC licenses
4. **Generate with TTS** - Use Piper to generate verbal confirmations

## Using with Home Assistant

These sounds can be played via shell commands or media players:

```yaml
# In configuration.yaml
shell_command:
  play_lcars_chirp: 'aplay /config/sounds/lcars_chirp.wav'

# Or via media_player
service: media_player.play_media
data:
  entity_id: media_player.living_room
  media_content_id: /config/sounds/lcars_chirp.wav
  media_content_type: audio/wav
```

## Chime TTS Integration

For a seamless experience, use the Chime TTS custom integration:

```yaml
service: chime_tts.say
data:
  chime_path: /config/sounds/lcars_chirp.wav
  message: "Acknowledged, Commander."
  tts_platform: piper
  media_player: media_player.living_room
```

This prepends the chirp sound before the TTS response, masking LLM processing time.
