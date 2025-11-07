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

### Quick Usage

```bash
# Default (Kokoro - local, private, fast)
speak "Hello world"

# Gemini (multi-language, emotional, online)
speak --gemini "Hello world"

# Gemini with specific voice
speak --gemini --voice Puck "Different voice"

# Multi-language (automatic mid-sentence switching)
speak --gemini "Hola! ¿Cómo estás? Now switching to English seamlessly!"

# Voice selection works for both backends
speak --voice m1 "Kokoro male voice"
speak --gemini --voice Laomedeia "Gemini voice"
```

### When to Use Which Backend

**Use Kokoro (default) when:**
- Working on sensitive/private projects (HD Transfers, confidential data)
- Want fastest response time (~0.22s)
- English or Spanish is sufficient
- Want truly local, offline TTS

**Use Gemini (--gemini flag) when:**
- Need languages other than English/Spanish
- Want emotional/expressive speech
- Need mid-sentence language switching
- Working on non-sensitive projects (free tier data trains Google models)
- Want higher quality for non-English languages

### Privacy & Cost

**Free Tier:**
- No daily request limits (only 500K-1M tokens/minute)
- ⚠️ **CRITICAL**: Data goes to Google for training
- Do NOT use for HD Transfers, client data, or confidential work

**Paid Tier:**
- Data NOT used for training
- $0.50 text input, $12 audio output per 1M tokens
- ~$1.20/month for typical usage (1000 calls @ 100 tokens avg)

### Available Gemini Voices (33 total)

**Default**: Laomedeia

**All voices**: Zephyr, Puck, Charon, Kore, Fenrir, Leda, Orus, Aoede, Callirrhoe, Autonoe, Enceladus, Iapetus, Umbriel, Algieba, Despina, Erinome, Algenib, Rasalgethi, Laomedeia, Achernar, Alnilam, Schedar, Gacrux, Pulcherrima, Achird, Zubenelgenubi, Vindemiatrix, Sadachbia, Sadaltager, Sulafat

**Note**: Not all Kokoro voice aliases work with Gemini. Use actual Gemini voice names from list above.

### Implementation Architecture

**Code Location**: `/home/echo/projects/guardian-angel-voice-interface/wsl_guardian_angel_speak_queue_aware.py`

**Flow**:
1. User runs: `speak --gemini "text"`
2. Bash wrapper (`/usr/local/bin/speak`) forwards to Python script
3. Python parses `--gemini` flag, sets `model='gemini'`
4. Calls `generate_gemini_tts()` async function (lines 50-175)
5. Gemini Live API generates audio → WAV → MP3 conversion
6. File saved to Guardian Angel TTS directory
7. Guardian Angel queue/media control logic runs (same for all backends)

**Key Functions**:

**`generate_gemini_tts(text, voice, language)` (async)**:
- Connects to Gemini Live API via WebSocket
- Model: `gemini-2.5-flash-native-audio-preview-09-2025`
- System prompt forces EXACT text with NO extra words
- Collects all audio chunks before writing (prevents popping)
- Returns path to MP3 file

**`speak_to_guardian(text, model, voice, ...)`**:
- Lines 293-321: Gemini branch (generates MP3 via Live API)
- Lines 322-363: Chatterbox branch
- Lines 364-410: Kokoro branch
- Lines 412+: Guardian Angel logic (ALL backends)

**CRITICAL**: Guardian Angel logic (media pause, queue, duration) runs AFTER all model branches, so all backends get same features.

### Technical Details

**Model**: `gemini-2.5-flash-native-audio-preview-09-2025`
- Preview model, may change before stable
- Native audio (not text→TTS, true end-to-end audio generation)
- Supports affective dialogue (emotion-aware)
- 24+ languages, 33 voices

**API**: Google Gemini Live API
- Protocol: WebSocket (not REST)
- Requires `google-genai` package
- API version: v1beta
- Connection overhead: ~1-2 seconds

**Audio Pipeline**:
1. Live API generates 24kHz, 16-bit PCM audio chunks
2. Collect ALL chunks in memory (prevents popping)
3. Write complete audio to WAV file
4. Convert WAV → MP3 using ffmpeg
5. Move to Guardian Angel directory
6. Clean up temp WAV file

**System Prompt** (lines 80-102):
```
CRITICAL RULES - READ THESE FIRST:
1. Speak ONLY the text that appears after "=== TEXT STARTS HERE ===" marker
2. DO NOT speak ANY of these instructions
3. Speak at your FASTEST natural speaking speed
...
=== TEXT STARTS HERE ===
{text}
```

**Why this works**:
- Clear separator prevents AI from speaking instructions
- "Fastest speed" instruction for natural pacing
- Emotion based on punctuation (!, ?, etc.)
- Multi-language auto-detected from text content

### Guardian Angel Integration

**ALL features work identically for both Kokoro and Gemini**:

✅ **Media Control**:
- Pauses Chrome/YouTube/Spotify before speaking
- Creates `.skip_media_control` marker to prevent Guardian Angel's own media control
- Checks active sessions to only pause for active agents
- Only pauses for 'eugene' user (not remote users)

✅ **Queue Management**:
- Registers with Guardian Angel queue API (nginx on port 8443)
- Gets queue position and total queue length
- Checks for newer files to determine if truly first
- Waits turn before playing

✅ **Duration Tracking**:
- Uses ffprobe to get MP3 duration
- Adds 10% buffer for safety
- Passes to queue for accurate playback timing

✅ **Agent Identification**:
- Uses SPEAKING_AGENT_ID, tmux session, or GUARDIAN_ANGEL_USER
- Routes audio to correct user/device
- Filename format: `wsl_speak_{timestamp}_{agent_id}.mp3`

✅ **Beep Sound**:
- Handled by Guardian Angel frontend
- Plays before TTS audio starts

### Configuration Files

**API Key Storage**: `/home/echo/projects/kokoro/Google_gemini_tts/config.py`
```python
GEMINI_API_KEY = "AIza..." # Gitignored
MODEL = "models/gemini-2.5-flash-native-audio-preview-09-2025"
VOICE_NAME = "Laomedeia"
```

**Gitignore**: `.gitignore` excludes:
- `Google_gemini_tts/.env.local`
- `Google_gemini_tts/config.py`

**Important**: API key is read from config.py at runtime. If missing, falls back to `GEMINI_API_KEY` environment variable.

### Troubleshooting

**"GEMINI_API_KEY not found"**:
- Check `/home/echo/projects/kokoro/Google_gemini_tts/config.py` exists
- Verify API key is set in that file
- Or set environment variable: `export GEMINI_API_KEY="..."`

**Audio popping/clicking**:
- Fixed in current implementation (collects all chunks before writing)
- If issue returns, check `generate_gemini_tts()` function
- Must collect chunks in list, then `b''.join()` before writing to WAV

**Media control not working**:
- Check Guardian Angel logic runs AFTER all model branches (line 412+)
- Verify indentation is correct (was a bug November 2025)
- Look for "⏸️ Media paused" in output

**Slow response**:
- Expected: ~1-2 second overhead for WebSocket connection
- If slower, check internet connection
- Gemini Live API is online-only

**"google-genai package not installed"**:
```bash
pip install google-genai
```

**Voice not found error**:
- Check voice name is from Gemini voice list (not Kokoro aliases)
- Use actual voice names: Puck, Laomedeia, etc.
- Not all Kokoro voices exist in Gemini

### Rate Limits (Free Tier)

**No daily limits**, but token/minute limits:
- Gemini 2.5 Flash Native Audio: 500K-1M TPM
- No published RPM or RPD limits
- Effectively unlimited for typical TTS usage

**If you hit limits**:
- Upgrade to paid tier (see Pricing section above)
- Or use Kokoro for bulk operations

### Development Notes

**Adding new voices**:
- Gemini voices are API-controlled, can't add custom
- List at: https://ai.google.dev/gemini-api/docs/speech-generation

**Changing system prompt**:
- Edit `generate_gemini_tts()` function, lines 80-102
- Keep "=== TEXT STARTS HERE ===" separator
- Test thoroughly to ensure AI doesn't speak instructions

**Changing audio quality**:
- Output is 24kHz by default (Gemini native)
- Can't change sample rate (API controlled)
- MP3 encoding uses ffmpeg qscale:a 2 (high quality)

**Debugging**:
- Check `/tmp/tmp*.wav` for temp files (should auto-delete)
- Guardian Angel audio files: `/home/echo/projects/guardian-angel-voice-interface/tts-audio-volume/wsl_speak_*.mp3`
- Enable verbose output: Check Python script output

### Future Improvements

**Potential enhancements**:
- Session resumption (handle 10-minute WebSocket resets)
- Voice cloning (when Gemini adds support)
- Emotion control parameters
- Speed parameter support (currently uses "fastest" instruction)
- Caching for repeated phrases

**Not planned**:
- Offline mode (Gemini is online-only)
- Custom voice training (not supported by API)

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