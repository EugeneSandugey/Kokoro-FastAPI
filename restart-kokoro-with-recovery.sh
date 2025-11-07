#!/bin/bash
# Restart Kokoro with auto-recovery enabled

# Stop existing container
docker stop kokoro-tts 2>/dev/null
docker rm kokoro-tts 2>/dev/null

# Run with restart policy and health check
docker run -d \
  --name kokoro-tts \
  --gpus all \
  -p 8880:8880 \
  --restart unless-stopped \
  --health-cmd="curl -f http://localhost:8880/health || exit 1" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  --health-start-period=40s \
  ghcr.io/remsky/kokoro-fastapi-gpu:v0.2.1

echo "Kokoro TTS restarted with auto-recovery enabled"
echo "Container will auto-restart on failures"