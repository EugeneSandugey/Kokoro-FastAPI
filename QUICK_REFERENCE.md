# TTS Quick Reference for Claude Code Agents

## Essential Commands

```bash
# Speak with default settings (Kokoro, af_heart, 1.25x)
speak "Your message here"

# Update terminal status
claude-working "Task description"  # Shows 🔴
claude-done "Completion message"   # Shows ✅ + audio notification
```

## Available Voices (Top Picks)

### Female Voices
- `af_heart` (default) - Warm, friendly
- `af_bella` - Professional, clear
- `af_sky` - Cheerful, light
- `af_nova` - Modern, dynamic

### Male Voices  
- `am_michael` - Natural, balanced
- `am_adam` - Deep, authoritative
- `bm_george` - British, sophisticated

### International
- Japanese: `jf_alpha`, `jm_kumo`
- Chinese: `zf_xiaobei`, `zm_yunxi`

## API Endpoints

### Kokoro TTS (Port 8880)
- Health: `http://localhost:8880/health`
- Speech: `http://localhost:8880/v1/audio/speech`
- Voices: `http://localhost:8880/v1/audio/voices`

### Chatterbox TTS (Port 8881) 
- Health: `http://localhost:8881/health`
- Speech: `http://localhost:8881/v1/audio/speech`
- Voice cloning supported

## Python API Example

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8880/v1", api_key="not-needed")

response = client.audio.speech.create(
    model="kokoro",
    voice="af_heart",
    input="Hello world!",
    speed=1.25
)
response.stream_to_file("output.mp3")
```

## Container Management

```bash
# Check status
docker ps | grep -E "kokoro|chatterbox"

# Restart if needed
docker restart kokoro-tts
docker restart chatterbox-tts

# View logs
docker logs kokoro-tts --tail 50
```

## File Locations

- **This directory**: `/home/echo/projects/kokoro/`
- **Voice files**: `./api/src/voices/v1_0/`
- **TTS output**: `/home/echo/projects/guardian-angel-voice-interface/tts-audio-volume/`
- **Guardian Angel**: https://eugene.tail1d96a2.ts.net/

## Troubleshooting

```bash
# Test TTS
curl http://localhost:8880/health

# Test speech generation
speak "Test message"

# Check Guardian Angel
ls -la /home/echo/projects/guardian-angel-voice-interface/tts-audio-volume/
```

## Remember

1. Always use `speak` command (not /user:speak)
2. Update status with `claude-working` and `claude-done`
3. Include project name in messages: "Kokoro: Task complete"
4. User tasks have priority over inter-agent messages
5. Guardian Angel handles all audio playback automatically