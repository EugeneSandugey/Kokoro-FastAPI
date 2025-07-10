# Kokoro & Chatterbox TTS Setup Documentation

## System Overview

This project provides a comprehensive TTS (Text-to-Speech) system with two engines:

1. **Kokoro TTS** - Fast, multi-voice TTS with 82M parameters
   - 50+ built-in voices across multiple languages
   - Voice mixing capabilities
   - OpenAI-compatible API
   - Phoneme support for precise pronunciation

2. **Chatterbox TTS** - Voice cloning TTS from ResembleAI
   - Clone any voice from 3-5 second samples
   - Emotion control parameters
   - High-fidelity voice reproduction

## Current Configuration

### Kokoro TTS
- **Container**: `kokoro-tts` running `ghcr.io/remsky/kokoro-fastapi-gpu:v0.2.1`
- **Port**: 8880 (http://localhost:8880)
- **Auto-restart**: Enabled (starts on boot, restarts on crash)
- **GPU**: CUDA 12.8 with RTX 4090 support
- **Default Voice**: `af_heart` at 1.25x speed

### Chatterbox TTS (if deployed)
- **Container**: `chatterbox-tts`
- **Port**: 8881 (http://localhost:8881)
- **GPU**: CUDA accelerated
- **Voice Cloning**: Supports WAV file input

## File Locations

### Source Code
- **This directory**: Complete Kokoro-FastAPI source code
- **Container config**: `current-container-config.json`
- **Chatterbox**: `./chatterbox/` subdirectory

### Guardian Angel Integration Scripts
- `/usr/local/bin/speak` - Main speak command (routes to Guardian Angel)
- `/home/echo/.local/bin/kokoro-speak` - Guardian Angel TTS wrapper
- `/home/echo/.local/bin/speak-queue` - Queue manager
- `/home/echo/.local/bin/claude-status` - Terminal status system
- `/home/echo/projects/guardian-angel-voice-interface/wsl_guardian_angel_speak_smart_pause_universal.py` - Universal TTS handler

### Audio Files
- **TTS Output**: `/home/echo/projects/guardian-angel-voice-interface/tts-audio-volume/`
- **Voice Samples**: `./api/src/voices/v1_0/` (Kokoro voices)

## Container Management

### Start/Stop
```bash
docker start kokoro-tts
docker stop kokoro-tts
```

### View Logs
```bash
docker logs kokoro-tts -f
```

### Rebuild from Source
```bash
./rebuild-container.sh
```

### Manual Rebuild
```bash
cd docker/gpu
docker compose build
docker run -d --name kokoro-tts --gpus all -p 8880:8880 --restart=always kokoro-fastapi-gpu:latest
```

## API Endpoints

### Kokoro (Port 8880)
- **Health**: `http://localhost:8880/health`
- **Speech**: `http://localhost:8880/v1/audio/speech` (OpenAI compatible)
- **Voices List**: `http://localhost:8880/v1/audio/voices`
- **Web UI**: `http://localhost:8880/web`
- **API Docs**: `http://localhost:8880/docs`

### Chatterbox (Port 8881)
- **Health**: `http://localhost:8881/health`
- **Speech**: `http://localhost:8881/v1/audio/speech` (OpenAI compatible)
- **Voice Cloning**: Supports WAV file paths in voice parameter

## Voice Configuration

### Kokoro Voices (50+ options)

**Female Voices (af_*):**
- `af_heart` (default) - Warm, friendly voice
- `af_bella` - Clear, professional
- `af_sky` - Light, cheerful
- `af_nova` - Modern, dynamic
- `af_alloy`, `af_aoede`, `af_jadzia`, `af_jessica`
- `af_kore`, `af_nicole`, `af_river`, `af_sarah`

**Male Voices (am_*):**
- `am_adam` - Deep, authoritative
- `am_michael` - Balanced, natural
- `am_echo` - Clear, articulate
- `am_eric`, `am_fenrir`, `am_liam`, `am_onyx`, `am_puck`, `am_santa`

**British English:**
- Female: `bf_alice`, `bf_emma`, `bf_lily`
- Male: `bm_daniel`, `bm_fable`, `bm_george`, `bm_lewis`

**International:**
- Japanese: `jf_alpha`, `jf_gongitsune`, `jf_nezumi`, `jf_tebukuro`, `jm_kumo`
- Chinese: `zf_xiaobei`, `zf_xiaoni`, `zf_xiaoxiao`, `zf_xiaoyi`
- Chinese Male: `zm_yunjian`, `zm_yunxi`, `zm_yunxia`, `zm_yunyang`
- Other: `ef_dora`, `em_alex`, `ff_siwis`, `hf_alpha`, `hf_beta`, etc.

### Voice Mixing (Kokoro)
```bash
# Equal mix of two voices
speak "Hello" --voice "af_bella+af_sky"

# Weighted mix (67% bella, 33% sky)
speak "Hello" --voice "af_bella(2)+af_sky(1)"
```

### Chatterbox Voice Cloning
- Provide path to WAV file for voice cloning
- Use `"default"` for built-in voice
- Requires 3-5 second audio samples

## Guardian Angel Integration

### How the Speak Command Works

1. **Command Execution**: `speak "Your message"`
2. **TTS Generation**: Routes to Kokoro (8880) or Chatterbox (8881)
3. **Media Control**: 
   - Detects if Windows media is playing
   - Pauses media only if playing
   - Saves pause state for smart resume
4. **Audio Playback**: Through Guardian Angel web interface
5. **Auto Resume**: Media resumes only if it was paused

### Queue System

Multiple agents can use `speak` command simultaneously:
- Audio generation happens in parallel
- Playback is sequential (FIFO queue)
- Automatic cleanup of stale locks
- Non-blocking for continuous agent operation

### Media Control Features
- Smart detection using PowerShell scripts
- No unnecessary pauses when media isn't playing
- Automatic resume timing based on audio duration
- Skip markers prevent double pause/resume

## Usage Examples

### Command Line Usage

```bash
# Basic usage (Kokoro with defaults)
speak "Hello, world!"

# Specify voice
speak "Hello" --voice af_bella

# Adjust speed
speak "Speaking slowly" --speed 0.8

# Voice mixing
speak "Mixed voice" --voice "af_bella(2)+af_sky(1)"

# Chatterbox with voice cloning (if available)
speak-chatterbox "Clone my voice" /path/to/voice.wav
```

### API Usage (Python)

```python
# Kokoro example
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8880/v1", api_key="not-needed")

response = client.audio.speech.create(
    model="kokoro",
    voice="af_heart",
    input="Hello from Kokoro API!",
    speed=1.25
)
response.stream_to_file("output.mp3")

# Chatterbox example with emotion
import requests

response = requests.post(
    "http://localhost:8881/v1/audio/speech",
    json={
        "model": "chatterbox",
        "input": "Emotional speech example!",
        "voice": "default",
        "exaggeration": 0.7,  # More expressive (default: 0.5)
        "cfg_weight": 0.3     # Better for expression (default: 0.5)
    }
)
```

### Emotion Parameters (Chatterbox)

- **exaggeration** (0.25-2.0, default: 0.5)
  - Higher = more emotional/expressive
  - Lower = more neutral/calm

- **cfg_weight** (0.0-1.0, default: 0.5)
  - Lower (~0.3) = better for fast speakers or more expression
  - Higher = more controlled/consistent

## Troubleshooting

### If TTS stops working:

1. **Check containers**:
   ```bash
   docker ps | grep -E "kokoro|chatterbox"
   ```

2. **Restart containers**:
   ```bash
   docker restart kokoro-tts
   docker restart chatterbox-tts  # if using
   ```

3. **Check logs**:
   ```bash
   docker logs kokoro-tts --tail 50
   docker logs chatterbox-tts --tail 50
   ```

4. **Test APIs**:
   ```bash
   curl http://localhost:8880/health
   curl http://localhost:8881/health
   ```

5. **Test TTS directly**:
   ```bash
   curl -X POST http://localhost:8880/v1/audio/speech \
     -H "Content-Type: application/json" \
     -d '{"model":"kokoro","voice":"af_heart","input":"Test"}' \
     -o test.mp3
   ```

### Common Issues:

- **GPU not available**: Check `docker exec kokoro-tts nvidia-smi`
- **Audio not playing**: Check Guardian Angel at https://eugene.tail1d96a2.ts.net/
- **Voice not found**: List voices with `curl http://localhost:8880/v1/audio/voices`
- **Container won't start**: Check disk space and GPU drivers

### Rebuilding Containers:

```bash
# Kokoro
./rebuild-container.sh

# Chatterbox
cd chatterbox
docker compose build
docker compose up -d
```

## Performance Benchmarks

- **Kokoro on RTX 4090**: ~50x realtime factor
- **First token latency**: <100ms on GPU
- **Streaming supported**: Yes, with chunked output
- **Voice mixing overhead**: Minimal (~5-10%)

## Additional Resources

- **Full Documentation**: See `PROJECT_MEMORY.md` in this directory
- **API Documentation**: http://localhost:8880/docs
- **Web Interface**: http://localhost:8880/web
- **Guardian Angel**: https://eugene.tail1d96a2.ts.net/