# Kokoro TTS Project - Project Memory

## Overview
Self-hosted Kokoro TTS (Text-to-Speech) deployment running on RTX 4090 GPU. Provides fast, high-quality speech synthesis with 66 voices across 8 languages.

**Version**: v0.2.4 (Docker: ghcr.io/remsky/kokoro-fastapi-gpu)
**Port**: 8880
**GPU**: RTX 4090 (4.6GB VRAM)
**Performance**: ~0.22 seconds per generation
**Container**: kokoro-tts

## Quick Start
```bash
# Check status
docker ps | grep kokoro

# Test generation
curl -X POST http://localhost:8880/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Test message", "voice": "af_heart", "speed": 1.25}' \
  -o test.mp3

# Restart if needed
docker restart kokoro-tts
```

## Voice Aliases (November 2025)
Easy-to-remember shortcuts for voices via `speak` command:

**Female (f# / female#):**
- f1, female1 → af_heart (default)
- f2, female2 → af_bella
- f3, female3 → af_sky
- f4, female4 → af_aoede

**Male (m# / male#):**
- m1, male1 → am_fenrir
- m2, male2 → am_puck
- m3, male3 → am_michael
- m4, male4 → bm_george (British)

**Spanish (s# / spanish#):**
- s1, spanish1 → af_dora (female)
- s2, spanish2 → em_alex (male)
- s3, spanish3 → em_santa (male)

**Usage:**
```bash
speak --voice f1 "default female voice"
speak --voice m1 --speed 1.5 "faster male voice"
speak --voice s2 "Hola en español"
```

## Available Voices (66 total)

### American English
**Female (af_)**: alloy, aoede, bella, heart, jadzia, jessica, kore, nicole, nova, river, sarah, sky, v0, v0bella, v0irulan, v0nicole, v0sarah, v0sky

**Male (am_)**: adam, echo, eric, fenrir, liam, michael, onyx, puck, santa, v0adam, v0gurney, v0michael

### British English
**Female (bf_)**: alice, emma, lily, v0emma, v0isabella
**Male (bm_)**: daniel, fable, george, lewis, v0george, v0lewis

### Other Languages
- **Spanish (ef_/em_)**: dora, alex, santa
- **French (ff_)**: siwis
- **Hindi (hf_/hm_)**: alpha, beta, omega, psi
- **Italian (if_/im_)**: sara, nicola
- **Japanese (jf_/jm_)**: alpha, gongitsune, nezumi, tebukuro, kumo
- **Portuguese (pf_/pm_)**: dora, alex, santa
- **Chinese (zf_/zm_)**: xiaobei, xiaoni, xiaoxiao, xiaoyi, yunjian, yunxi, yunxia, yunyang

## Docker Speak Proxy
Location: `/home/echo/bin/docker-speak-proxy.py`
Port: 8885 (internal proxy for Docker agents)

**Purpose**: Allows Docker agents to call host `speak` command with full media control (pauses Chrome/YouTube/Spotify)

**Recent Fixes (November 2025):**
- Added voice parameter support (was ignoring custom voices)
- Added speed parameter support
- Added voice aliases (f1, m1, s1, etc.)
- Fixed default voice to af_heart at 1.25 speed

## Speak Command Integration
Location: `/usr/local/bin/speak`
Backend: `/home/echo/projects/guardian-angel-voice-interface/wsl_guardian_angel_speak_queue_aware.py`

**Features:**
- Queue-aware playback (prevents audio overlap)
- Media control (pauses Chrome/YouTube/Spotify)
- Agent identification (routes audio to correct user)
- Voice aliases support
- Speed control

## Google Gemini TTS Integration (November 2025)

**INTEGRATED INTO MAIN SPEAK COMMAND**

Use the `--gemini` (or `-g`) flag to use Google Gemini TTS instead of Kokoro:

```bash
# Default (Kokoro)
speak "Hello world"

# With Gemini
speak --gemini "Hello world"

# Gemini with specific voice
speak --gemini --voice Puck "Different voice"

# Multi-language (automatic switching)
speak --gemini "Hola! ¿Cómo estás? Switching to English now!"
```

### Why Use Gemini TTS
- **Multi-language support**: All languages, can switch mid-sentence
- **Emotional speech**: Native audio with affective dialogue
- **Quality**: Better than Kokoro for non-English languages
- **Free tier**: No daily limits (only token/minute limits)

### Why NOT Use Gemini TTS
- **Privacy**: Free tier data goes to Google for training
- **Latency**: ~1-2 second overhead for Live API connection
- **Dependency**: Requires internet connection

### Available Gemini Voices
Zephyr, Puck, Charon, Kore, Fenrir, Leda, Orus, Aoede, Callirrhoe, Autonoe, Enceladus, Iapetus, Umbriel, Algieba, Despina, Erinome, Algenib, Rasalgethi, Laomedeia (default), Achernar, Alnilam, Schedar, Gacrux, Pulcherrima, Achird, Zubenelgenubi, Vindemiatrix, Sadachbia, Sadaltager, Sulafat

### Implementation Details
- **Model**: gemini-2.5-flash-native-audio-preview-09-2025
- **API**: Google Gemini Live API (WebSocket)
- **Config**: Google_gemini_tts/config.py (API key stored here, gitignored)
- **Audio Format**: 24kHz WAV → MP3 conversion
- **System Prompt**: Forces AI to speak EXACT text with NO extra words, at FASTEST speed
- **Integration**: Fully integrated with Guardian Angel queue management, media control, beep sound

### When to Use Each
- **Kokoro** (default): Private projects, sensitive data, English/Spanish, lowest latency
- **Gemini** (opt-in via `--gemini`): Multi-language, emotional speech, non-sensitive projects

### Guardian Angel Integration
Both Kokoro and Gemini use the same speak command infrastructure:
- Queue-aware playback (prevents audio overlap)
- Media control (pauses Chrome/YouTube/Spotify)
- Agent identification (routes audio to correct user)
- Beep sound at start
- All features work identically regardless of TTS backend

## Alternative TTS Research (November 2025)

### Tested & Rejected
- **VibeVoice 1.5B**: "Complete horse garbage" - Too slow (3-4x slower than real-time)
- **Chatterbox**: Requires voice cloning samples, tested July 2025
- **Kokoros Rust**: Can't build due to dependency issues, would be slower than GPU Kokoro anyway

### Researched but Not Local
- **MiniMax Speech-02-HD**: #1 on TTS Arena but API-only, $0.05-0.10 per 1K chars
- **F5-TTS**: 10 months old (Oct 2024), no major advantages over Kokoro

**Conclusion**: Kokoro v0.2.4 with RTX 4090 is optimal for self-hosted TTS (0.22s, free, all 66 voices)

## Model Info
- **Size**: 82M parameters (tiny!)
- **Architecture**: Based on StyleTTS 2
- **License**: Apache 2.0 (open weights)
- **Training**: $1000 on A100s (~500 GPU hours)
- **Training Data**: Permissive/non-copyrighted audio only
- **Fine-tuning**: NOT SUPPORTED - uses pre-defined voice packs only

## Performance
- **Speed**: ~0.22 seconds on RTX 4090
- **RTF** (Real-Time Factor): ~210× on RTX 4090, ~90× on 3090 Ti, 3-11× on CPU
- **VRAM Usage**: 4.6GB active
- **Quality**: Comparable to much larger models

## Docker Setup
```yaml
# Location: ~/projects/kokoro/docker/gpu/docker-compose.yml
services:
  kokoro-tts:
    image: ghcr.io/remsky/kokoro-fastapi-gpu:v0.2.4
    ports:
      - "8880:8880"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

## Recovery Scripts
Location: `~/projects/kokoro/`
- `kokoro-monitor.sh` - Monitor for CUDA errors
- `restart-kokoro-with-recovery.sh` - Auto-restart on failure
- `kokoro_api_patch.py` - API patches/fixes
- `build-recovery-kokoro.sh` - Rebuild with recovery

## Git Repository
**Remote**: Not currently tracked (local project only)
**Related Repo**: guardian-angel-voice-interface (contains speak proxy code)

## Recent Updates
- **2025-11-04**: Added voice aliases (f1-f4, m1-m4, s1-s3)
- **2025-11-04**: Fixed Docker speak proxy to support voice/speed parameters
- **2025-08-31**: Updated to v0.2.4, fixed exclamation mark escaping bug
- **2025-07-29**: CUDA recovery monitoring added

## Cost Analysis vs Cloud TTS
**Self-hosted Kokoro**: $0/hour (only ~$0.15/hr electricity for 4090)
**MiniMax API**: $1.38-4.59/hour depending on model
**Savings**: $41-138/month for 1 hour daily use

## Key Files
- `/usr/local/bin/speak` - Main speak command wrapper
- `/home/echo/bin/docker-speak-proxy.py` - Proxy for Docker agents
- `/home/echo/projects/guardian-angel-voice-interface/wsl_guardian_angel_speak_queue_aware.py` - Backend speak implementation
- Container voices: `/app/api/src/voices/v1_0/*.pt` (66 voice files)