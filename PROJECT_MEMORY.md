# Kokoro & Chatterbox TTS Project Memory

## Overview
This directory contains a complete TTS (Text-to-Speech) API system with dual TTS engine support:
1. **Kokoro TTS** - Primary TTS engine with 82M parameters and 50+ voices
2. **Chatterbox TTS** - Voice cloning TTS engine from ResembleAI

Both systems are integrated with Guardian Angel for unified voice output and media control.

## System Architecture

### Docker Containers
- **Kokoro TTS**: Port 8880, GPU-accelerated, auto-restart enabled
- **Chatterbox TTS**: Port 8881, GPU-accelerated, voice cloning support

### Integration Points
- **Guardian Angel**: Central voice interface at https://eugene.tail1d96a2.ts.net/
- **Speak Command**: `/usr/local/bin/speak` - Routes to appropriate TTS engine
- **Media Control**: Smart pause/resume for Windows media during TTS playback

## Quick Start Guide

### 1. Check System Status
```bash
# Check if containers are running
docker ps | grep -E "kokoro|chatterbox"

# Test Kokoro
curl http://localhost:8880/health

# Test Chatterbox
curl http://localhost:8881/health
```

### 2. Basic Usage

#### Command Line (Human Users)
```bash
# Default (Kokoro with af_heart voice at 1.25x speed)
speak "Hello, world!"

# Chatterbox with voice cloning
speak-chatterbox "Hello from cloned voice" /path/to/voice.wav

# With custom parameters
speak-kokoro "Custom message" --voice af_bella --speed 1.5
```

#### For Claude Code Agents
```bash
# Use the speak command directly
/usr/local/bin/speak "Agent kokoro reporting: Task completed"

# Or use Guardian Angel messaging
/home/echo/bin/msg-send guardian "Status update: Processing complete"
```

### 3. Voice Options

#### Kokoro Voices (50+ options)
**Female Voices (af_*):**
- `af_heart` - Default, warm and friendly (1.25x speed recommended)
- `af_bella` - Clear and professional
- `af_sky` - Light and cheerful
- `af_nova` - Modern and dynamic
- `af_alloy`, `af_aoede`, `af_jadzia`, `af_jessica`, `af_kore`, `af_nicole`, `af_river`, `af_sarah`

**Male Voices (am_*):**
- `am_adam` - Deep and authoritative
- `am_michael` - Balanced and natural
- `am_echo` - Clear and articulate
- `am_eric`, `am_fenrir`, `am_liam`, `am_onyx`, `am_puck`, `am_santa`

**British Voices:**
- Female: `bf_alice`, `bf_emma`, `bf_lily`
- Male: `bm_daniel`, `bm_fable`, `bm_george`, `bm_lewis`

**International Voices:**
- Japanese: `jf_alpha`, `jf_gongitsune`, `jf_nezumi`, `jf_tebukuro`, `jm_kumo`
- Chinese: `zf_xiaobei`, `zf_xiaoni`, `zf_xiaoxiao`, `zf_xiaoyi`, `zm_yunjian`, `zm_yunxi`, `zm_yunxia`, `zm_yunyang`
- Others: `ef_dora`, `em_alex`, `em_santa`, `ff_siwis`, `hf_alpha`, `hf_beta`, `hm_omega`, `hm_psi`, `if_sara`, `im_nicola`, `pf_dora`, `pm_alex`, `pm_santa`

#### Chatterbox Voice Cloning
- Provide a WAV file path for voice cloning
- Default voice uses built-in model
- Supports emotion control via exaggeration parameter

### 4. API Usage

#### Kokoro API (OpenAI-compatible)
```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8880/v1", api_key="not-needed")

# Basic usage
response = client.audio.speech.create(
    model="kokoro",
    voice="af_heart",
    input="Hello from Kokoro!",
    speed=1.25
)
response.stream_to_file("output.mp3")

# Voice mixing
response = client.audio.speech.create(
    model="kokoro",
    voice="af_bella(2)+af_sky(1)",  # 67% bella, 33% sky
    input="Mixed voice example"
)
```

#### Chatterbox API
```python
import requests

# With emotion control
response = requests.post(
    "http://localhost:8881/v1/audio/speech",
    json={
        "model": "chatterbox",
        "input": "Hello with emotion!",
        "voice": "/path/to/voice.wav",  # or "default"
        "exaggeration": 0.7,  # 0.25-2.0, default 0.5
        "cfg_weight": 0.3,    # 0.0-1.0, default 0.5
        "speed": 1.0
    }
)

with open("output.mp3", "wb") as f:
    f.write(response.content)
```

### 5. Emotion Parameters (Chatterbox)

**Default Settings:**
- `exaggeration`: 0.5 (range: 0.25-2.0)
- `cfg_weight`: 0.5 (range: 0.0-1.0)

**Tuning Guide:**
- **Fast speakers**: Lower cfg_weight to ~0.3
- **More expression**: Lower cfg_weight to ~0.3, raise exaggeration to ~0.7+
- **Natural/calm**: Keep defaults (0.5/0.5)

## Container Management

### Start/Stop Containers
```bash
# Kokoro
docker start kokoro-tts
docker stop kokoro-tts
docker restart kokoro-tts

# Chatterbox
docker start chatterbox-tts
docker stop chatterbox-tts
docker restart chatterbox-tts
```

### View Logs
```bash
docker logs kokoro-tts -f --tail 100
docker logs chatterbox-tts -f --tail 100
```

### Rebuild from Source
```bash
# Kokoro (in this directory)
./rebuild-container.sh

# Chatterbox
cd chatterbox
docker compose build
docker compose up -d
```

## Guardian Angel Integration

### How It Works
1. **Speak Command**: Routes text to TTS engine (Kokoro/Chatterbox)
2. **Audio Generation**: TTS generates MP3 file
3. **Media Control**: Pauses Windows media if playing
4. **Guardian Angel Playback**: Audio plays through web interface
5. **Media Resume**: Automatically resumes media after TTS completes

### Media Control Features
- Smart detection of playing media
- Only pauses if media is actually playing
- Automatic resume after TTS playback
- Non-blocking for multiple agents

### File Locations
- **TTS Audio**: `/home/echo/projects/guardian-angel-voice-interface/tts-audio-volume/`
- **Control Scripts**: `/home/echo/bin/windows-media-control.ps1`
- **Status Detection**: `/home/echo/bin/windows-detect-media.ps1`

## Advanced Features

### Voice Mixing (Kokoro)
```bash
# Equal mix
speak "Hello" --voice "af_bella+af_sky"

# Weighted mix (67% bella, 33% sky)
speak "Hello" --voice "af_bella(2)+af_sky(1)"

# Three-way mix
speak "Hello" --voice "af_bella+af_sky+af_nova"
```

### Streaming Audio
```python
# Kokoro streaming
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8880/v1", api_key="not-needed")

with client.audio.speech.with_streaming_response.create(
    model="kokoro",
    voice="af_heart",
    input="Streaming example"
) as response:
    # Process chunks as they arrive
    for chunk in response.iter_bytes():
        # Handle audio chunk
        pass
```

### Phoneme Generation (Kokoro)
```python
# Generate phonemes for precise pronunciation
response = requests.post(
    "http://localhost:8880/v1/audio/speech",
    json={
        "model": "kokoro",
        "voice": "af_heart",
        "input": "[IPA phoneme string]",
        "response_format": "mp3"
    }
)
```

## Troubleshooting

### Common Issues

**1. TTS Not Responding**
```bash
# Check container status
docker ps -a | grep -E "kokoro|chatterbox"

# Restart containers
docker restart kokoro-tts
docker restart chatterbox-tts

# Check health endpoints
curl http://localhost:8880/health
curl http://localhost:8881/health
```

**2. GPU Issues**
```bash
# Check GPU availability
docker exec kokoro-tts nvidia-smi

# Check CUDA in container
docker exec kokoro-tts python -c "import torch; print(torch.cuda.is_available())"
```

**3. Audio Not Playing**
- Check Guardian Angel web interface: https://eugene.tail1d96a2.ts.net/
- Verify audio files in TTS directory
- Check Windows media control permissions

**4. Voice Not Found**
```bash
# List all available voices
curl http://localhost:8880/v1/audio/voices | jq
```

### Debug Commands
```bash
# Test Kokoro directly
curl -X POST http://localhost:8880/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"kokoro","voice":"af_heart","input":"Test"}' \
  -o test.mp3

# Test Chatterbox
curl -X POST http://localhost:8881/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"model":"chatterbox","voice":"default","input":"Test"}' \
  -o test.mp3

# Check queue status
ls -la /home/echo/projects/guardian-angel-voice-interface/tts-audio-volume/
```

## Performance Notes

### Kokoro Performance
- **GPU (RTX 4090)**: ~50x realtime factor
- **First token latency**: <100ms on GPU
- **Supports**: Streaming, voice mixing, phonemes
- **Languages**: English, Japanese, Chinese

### Chatterbox Performance
- **Voice cloning**: 3-5 second samples sufficient
- **Quality**: High-fidelity voice reproduction
- **Emotion control**: Real-time parameter adjustment
- **Best for**: Custom voices, emotional speech

## Security Notes
- Both APIs run locally only (localhost binding)
- No authentication required for local access
- Audio files auto-cleanup after playback
- Containers run with GPU passthrough only

## Future Enhancements
- ONNX support for Kokoro (coming soon)
- Additional language support
- Voice conversion features
- Real-time voice modulation