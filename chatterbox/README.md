# Chatterbox TTS Integration

## Overview

Chatterbox is a state-of-the-art voice cloning TTS system from ResembleAI that provides:
- High-quality voice cloning from 3-5 second samples
- Emotion control through exaggeration and cfg_weight parameters
- OpenAI-compatible API for easy integration
- GPU-accelerated inference

## Quick Start

### 1. Deploy Chatterbox Container

```bash
cd /home/echo/projects/kokoro/chatterbox
docker compose up -d
```

### 2. Verify Deployment

```bash
# Check container status
docker ps | grep chatterbox

# Test health endpoint
curl http://localhost:8881/health

# View logs
docker logs chatterbox-tts -f
```

### 3. Test Voice Cloning

```bash
# Test with default voice
curl -X POST http://localhost:8881/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "chatterbox",
    "input": "Hello from Chatterbox!",
    "voice": "default"
  }' \
  -o test_default.mp3

# Test with voice cloning (requires WAV file)
curl -X POST http://localhost:8881/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "chatterbox",
    "input": "This is my cloned voice speaking.",
    "voice": "/path/to/voice_sample.wav"
  }' \
  -o test_cloned.mp3
```

## Voice Cloning Guidelines

### Preparing Voice Samples

1. **Duration**: 3-5 seconds of clear speech
2. **Format**: WAV file (other formats may work but WAV is recommended)
3. **Quality**: Clean recording without background noise
4. **Content**: Natural speech with varied intonation

### Sample Preparation Commands

```bash
# Convert to WAV if needed
ffmpeg -i input.mp3 -acodec pcm_s16le -ar 44100 output.wav

# Trim to specific duration
ffmpeg -i input.wav -ss 00:00:01 -t 00:00:05 -acodec copy output_trimmed.wav

# Reduce noise (requires sox)
sox input.wav output_clean.wav noisered noise.prof 0.3
```

## API Parameters

### Required Parameters

- `model`: Always "chatterbox"
- `input`: Text to synthesize
- `voice`: Either "default" or path to WAV file

### Optional Parameters

- `speed`: Speech rate (default: 1.0)
- `response_format`: Output format (default: "mp3")
- `exaggeration`: Emotion intensity (0.25-2.0, default: 0.5)
- `cfg_weight`: Generation guidance (0.0-1.0, default: 0.5)

## Emotion Control Guide

### Exaggeration Parameter (0.25-2.0)

- **0.25-0.4**: Very calm, monotone delivery
- **0.5** (default): Natural, balanced emotion
- **0.6-0.8**: More expressive, animated
- **0.9-1.5**: Highly emotional, theatrical
- **1.6-2.0**: Extreme emotion (use sparingly)

### CFG Weight Parameter (0.0-1.0)

- **0.0-0.2**: Maximum variation, less consistent
- **0.3**: Good for fast speakers or high expression
- **0.5** (default): Balanced consistency
- **0.7-0.8**: More controlled, consistent
- **0.9-1.0**: Very rigid, minimal variation

### Common Combinations

```python
# Natural conversation
{"exaggeration": 0.5, "cfg_weight": 0.5}

# Expressive storytelling
{"exaggeration": 0.7, "cfg_weight": 0.3}

# Calm narration
{"exaggeration": 0.3, "cfg_weight": 0.7}

# Excited announcement
{"exaggeration": 0.9, "cfg_weight": 0.3}

# Robotic/monotone
{"exaggeration": 0.25, "cfg_weight": 0.9}
```

## Python Integration Examples

### Basic Usage

```python
import requests
import json

def generate_speech(text, voice_path=None, emotion="natural"):
    # Emotion presets
    emotions = {
        "natural": {"exaggeration": 0.5, "cfg_weight": 0.5},
        "excited": {"exaggeration": 0.8, "cfg_weight": 0.3},
        "calm": {"exaggeration": 0.3, "cfg_weight": 0.7},
        "dramatic": {"exaggeration": 1.2, "cfg_weight": 0.3}
    }
    
    params = emotions.get(emotion, emotions["natural"])
    
    response = requests.post(
        "http://localhost:8881/v1/audio/speech",
        json={
            "model": "chatterbox",
            "input": text,
            "voice": voice_path or "default",
            "speed": 1.0,
            **params
        }
    )
    
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"TTS failed: {response.text}")

# Example usage
audio = generate_speech(
    "Hello! This is an excited voice clone!",
    voice_path="/path/to/voice.wav",
    emotion="excited"
)

with open("output.mp3", "wb") as f:
    f.write(audio)
```

### Streaming with Voice Cloning

```python
import requests

def stream_speech(text, voice_path, chunk_size=1024):
    response = requests.post(
        "http://localhost:8881/v1/audio/speech",
        json={
            "model": "chatterbox",
            "input": text,
            "voice": voice_path,
            "stream": True
        },
        stream=True
    )
    
    for chunk in response.iter_content(chunk_size=chunk_size):
        if chunk:
            yield chunk

# Stream to file
with open("streamed_output.mp3", "wb") as f:
    for chunk in stream_speech("Streaming voice clone!", "/path/to/voice.wav"):
        f.write(chunk)
```

## Container Management

### Start/Stop

```bash
# Start
docker start chatterbox-tts

# Stop
docker stop chatterbox-tts

# Restart
docker restart chatterbox-tts
```

### Resource Monitoring

```bash
# Check GPU usage
docker exec chatterbox-tts nvidia-smi

# Check logs
docker logs chatterbox-tts --tail 100 -f

# Check resource usage
docker stats chatterbox-tts
```

### Rebuild Container

```bash
cd /home/echo/projects/kokoro/chatterbox
docker compose down
docker compose build --no-cache
docker compose up -d
```

## Troubleshooting

### Common Issues

1. **Voice file not found**
   - Ensure the path is absolute
   - Check file permissions
   - Verify WAV format

2. **GPU memory errors**
   - Restart container: `docker restart chatterbox-tts`
   - Check GPU memory: `nvidia-smi`

3. **Slow generation**
   - Verify GPU is being used
   - Check model is loaded on CUDA
   - Monitor with `docker logs chatterbox-tts`

4. **Poor voice quality**
   - Use higher quality voice samples
   - Adjust emotion parameters
   - Try different cfg_weight values

### Debug Commands

```bash
# Test model loading
docker exec chatterbox-tts python -c "
import torch
from chatterbox.tts import ChatterboxTTS
print(f'CUDA available: {torch.cuda.is_available()}')
model = ChatterboxTTS.from_pretrained(device='cuda')
print('Model loaded successfully!')
"

# Check available voices directory
docker exec chatterbox-tts ls -la /voice-samples/

# Test voice cloning with docker volume
docker run -it --rm \
  --gpus all \
  -v /path/to/voices:/voices \
  -p 8881:8881 \
  chatterbox-tts
```

## Integration with Guardian Angel

The Chatterbox TTS integrates seamlessly with Guardian Angel through the universal speak command:

```bash
# Use Chatterbox with Guardian Angel
speak-chatterbox "Hello from cloned voice!" /path/to/voice.wav

# With emotion control
python3 /home/echo/projects/guardian-angel-voice-interface/wsl_guardian_angel_speak_smart_pause_universal.py \
  --model chatterbox \
  --voice-file /path/to/voice.wav \
  --exaggeration 0.7 \
  --cfg-weight 0.3 \
  "Expressive cloned speech!"
```

## Performance Notes

- **Model Loading**: ~5-10 seconds on first request
- **Generation Speed**: 10-20x realtime on RTX 4090
- **Memory Usage**: ~4GB VRAM
- **Voice Cloning**: Adds ~1-2 seconds overhead
- **Concurrent Requests**: Supported but may queue

## Best Practices

1. **Voice Samples**
   - Use consistent recording environment
   - Include varied speech patterns
   - Avoid background music or noise

2. **Text Preparation**
   - Include punctuation for natural pauses
   - Break long texts into sentences
   - Use phonetic spelling for unusual words

3. **Emotion Tuning**
   - Start with defaults (0.5/0.5)
   - Adjust in small increments
   - Test with your specific voice clone

4. **Production Use**
   - Cache generated audio when possible
   - Monitor GPU memory usage
   - Implement request queuing for high load