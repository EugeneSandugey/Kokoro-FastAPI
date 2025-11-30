# Kokoro TTS Project - Project Memory

<overview>
Self-hosted Kokoro TTS on RTX 4090. Fast, high-quality speech synthesis with 66 voices across 8 languages.

| Component | Value |
|-----------|-------|
| Version | v0.2.4 (Docker: ghcr.io/remsky/kokoro-fastapi-gpu) |
| Port | 8880 |
| GPU | RTX 4090 (4.6GB VRAM) |
| Performance | ~0.22s per generation |
| Container | kokoro-tts |
</overview>

<services>
## Whisper Timestamps Service (port 8881)
GPU container running distil-large-v3 for word-level timestamp generation.

| Attribute | Value |
|-----------|-------|
| Container | whisper-timestamps |
| VRAM | ~2GB |
| Latency | ~200-250ms |
| Location | `/home/echo/projects/kokoro/whisper-timestamps-service/` |

Used by `speak` command for Kokoro/Gemini word captions.

```bash
# Status/restart
docker ps | grep whisper-timestamps
curl http://localhost:8881/health
cd /home/echo/projects/kokoro/whisper-timestamps-service && docker compose restart
```
</services>

<quick_reference>
## Quick Start
```bash
# Check/restart Kokoro
docker ps | grep kokoro
docker restart kokoro-tts

# Test TTS
curl -X POST http://localhost:8880/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Test", "voice": "af_heart", "speed": 1.25}' -o test.mp3
```

## Speak Command
Location: `/usr/local/bin/speak`
Backend: `/home/echo/projects/guardian-angel-voice-interface/wsl_guardian_angel_speak_queue_aware.py`

Features: Queue-aware playback, media control (pauses Chrome/YouTube/Spotify), agent routing, voice aliases, speed control.
</quick_reference>

<voice_aliases>
## Voice Aliases

**Kokoro (default)**:
- f1-f4: af_heart, af_bella, af_sky, af_aoede
- m1-m4: am_fenrir, am_puck, am_michael, bm_george
- s1-s3: af_dora, em_alex, em_santa (Spanish)

**Gemini** (--gemini): f1=Laomedeia, f2=Zephyr, f3=Aoede, m1=Puck

**Inworld** (--inworld): f1=Sarah, f2=Deborah, f3=Ashley, m1=Dennis, m2=Mark, bf1=Olivia, bf2=Wendy

```bash
speak --voice f1 "Kokoro default"
speak --gemini --voice f1 "Gemini Laomedeia"
speak --inworld --voice f1 "Inworld Sarah"
```
</voice_aliases>

<tts_backends>
## TTS Backend Selection

| Backend | Flag | Use When |
|---------|------|----------|
| **Kokoro** | (default) | Sensitive data, fastest (~0.22s), English/Spanish, offline |
| **Gemini** | --gemini | Multi-language, emotional, non-sensitive (Google trains on free tier) |
| **Inworld** | --inworld | Highest quality (#1 TTS Arena), word timestamps, ~$3.60/month |

### Privacy Notes
- **Kokoro**: Fully local, no data leaves system
- **Gemini Free**: Data used for Google training - avoid for confidential work
- **Gemini Paid**: Data not used for training (~$1.20/month)
- **Inworld**: API-based, data goes to Inworld servers
</tts_backends>

<available_voices>
## Available Voices (66 total)

**American English**
- Female (af_): alloy, aoede, bella, heart, jadzia, jessica, kore, nicole, nova, river, sarah, sky
- Male (am_): adam, echo, eric, fenrir, liam, michael, onyx, puck, santa

**British English**
- Female (bf_): alice, emma, lily
- Male (bm_): daniel, fable, george, lewis

**Other Languages**: Spanish (ef_/em_), French (ff_), Hindi (hf_/hm_), Italian (if_/im_), Japanese (jf_/jm_), Portuguese (pf_/pm_), Chinese (zf_/zm_)
</available_voices>

<implementation>
## Implementation Details

### Code Flow
1. `speak [--gemini|--inworld] "text"` → bash wrapper
2. Python script parses flags → selects backend
3. Backend generates audio → saves MP3
4. Guardian Angel handles queue/media control (all backends)

### Key Files
| File | Purpose |
|------|---------|
| `/usr/local/bin/speak` | Bash wrapper |
| `wsl_guardian_angel_speak_queue_aware.py` | Main TTS logic |
| `/home/echo/bin/docker-speak-proxy.py` | Docker agent proxy (port 8885) |

### API Keys (gitignored)
- Gemini: `/home/echo/projects/kokoro/Google_gemini_tts/config.py`
- Inworld: `/home/echo/projects/kokoro/inworld_tts/config.py`
</implementation>

<guardian_angel_integration>
## Guardian Angel Integration

All backends share these features:
- **Media Control**: Pauses Chrome/YouTube/Spotify before speaking
- **Queue Management**: Prevents audio overlap via nginx API (port 8443)
- **Duration Tracking**: ffprobe + 10% buffer for accurate timing
- **Agent Routing**: Uses SPEAKING_AGENT_ID or tmux session
- **Beep Sound**: Handled by frontend before TTS plays
</guardian_angel_integration>

<troubleshooting>
## Troubleshooting

| Issue | Solution |
|-------|----------|
| "API_KEY not found" | Check config.py exists, or set env var |
| Audio popping | Verify chunks collected before WAV write |
| Media control fails | Check Guardian Angel logic runs after model branches |
| Slow Gemini | Expected ~1-2s WebSocket overhead |
| Voice not found | Use correct backend's voice names |
</troubleshooting>

<model_info>
## Model Info

| Attribute | Value |
|-----------|-------|
| Size | 82M parameters |
| Architecture | StyleTTS 2 |
| License | Apache 2.0 |
| RTF | ~210× on RTX 4090 |
| Fine-tuning | Not supported (pre-defined voice packs only) |
</model_info>

<docker_setup>
## Docker Setup

```yaml
# ~/projects/kokoro/docker/gpu/docker-compose.yml
services:
  kokoro-tts:
    image: ghcr.io/remsky/kokoro-fastapi-gpu:v0.2.4
    ports: ["8880:8880"]
    deploy:
      resources:
        reservations:
          devices: [{driver: nvidia, count: 1, capabilities: [gpu]}]
```

Recovery scripts in `~/projects/kokoro/`:
- `kokoro-monitor.sh`, `restart-kokoro-with-recovery.sh`, `kokoro_api_patch.py`
</docker_setup>

<recent_updates>
## Recent Updates
- **2025-11-30**: Added whisper-timestamps service (port 8881) - 200ms latency vs 1.2s per-call
- **2025-11-29**: Fixed Inworld word timestamp fuzzy mapping (hyphen/compound splits)
- **2025-11-28**: Added Inworld TTS (--inworld), 7 voices, HD model, word timestamps
- **2025-11-07**: Voice aliases now backend-aware (f1 maps differently per backend)
- **2025-08-31**: Updated to v0.2.4, fixed exclamation escaping
</recent_updates>

<cost_analysis>
## Cost Analysis

| Service | Cost |
|---------|------|
| Kokoro (self-hosted) | ~$0.15/hr electricity |
| Inworld API | ~$3.60/month typical |
| Gemini Paid | ~$1.20/month typical |
| MiniMax API | $1.38-4.59/hr |
</cost_analysis>
