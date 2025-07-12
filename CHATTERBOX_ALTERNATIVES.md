# Chatterbox TTS Alternatives for Improved Long-Form Audio

## Current Situation (2025-07-12)
- Base Chatterbox has a 40-second limit due to `max_new_tokens=1000`
- We've increased it to 10000 which allows ~50 seconds
- Very long texts (60s+) cause CUDA errors
- Audio cuts off during playback around 30 seconds when it reaches token limit

## Two Superior Alternatives

### 1. Chatterbox-TTS-Server (by devnen)
**Best for API Integration**

Repository: https://github.com/devnen/Chatterbox-TTS-Server

**Key Features:**
- OpenAI-compatible API endpoints (drop-in replacement)
- **Automatic text chunking** for unlimited length audio
- Built-in voices (no reference needed)
- Docker support (already using Docker)
- FastAPI-based server
- Web UI for testing
- Audiobook generation support

**Integration:**
```bash
# Would replace current endpoint
http://localhost:8881/v1/audio/speech
# Same parameters as current setup
```

### 2. Chatterbox-TTS-Extended (by petermg)
**Best for Quality Control**

Repository: https://github.com/petermg/Chatterbox-TTS-Extended

**Key Features:**
- **Whisper validation** - catches stutters, skipped words, artifacts
- Generates multiple candidates and picks best
- Advanced text preprocessing (removes "um", "ahh", fixes abbreviations)
- Voice conversion capabilities
- Batch file processing
- Rich post-processing with Auto-Editor

**Quality Control Process:**
1. Generates 3-5 candidates per chunk
2. Whisper transcribes each back to text
3. Compares with original, selects best match
4. Automatically retries on failures

## System Capabilities
With 9950X (16c/32t), 200GB RAM, RTX 4090:
- Can easily run Chatterbox + Whisper simultaneously
- Whisper small/medium adds only 1-2 seconds per chunk
- Parallel processing with 8-12 workers
- VRAM usage: Chatterbox (3GB) + Whisper small (1.5GB) = 4.5GB total

## Recommendation
1. **For immediate needs**: Chatterbox-TTS-Server
   - Solves the length problem cleanly
   - Minimal changes to current workflow
   - Production-ready

2. **For best quality**: Chatterbox-TTS-Extended
   - Whisper validation catches all artifacts
   - Worth the extra processing time
   - Perfect for audiobooks or critical content

## Current Workaround
The 10x token increase (1000→10000) is working for ~50 second audio, but proper chunking solutions above are more robust for unlimited length.