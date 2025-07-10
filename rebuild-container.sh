#!/bin/bash

# Rebuild Kokoro TTS container from source
# Use this if you need to modify the container or rebuild locally

echo "Building Kokoro TTS container from source..."

# Stop and remove existing container
docker stop kokoro-tts 2>/dev/null || true
docker rm kokoro-tts 2>/dev/null || true

# Build from local source (GPU version)
cd docker/gpu
docker compose build

# Start with auto-restart policy
docker run -d \
  --name kokoro-tts \
  --gpus all \
  -p 8880:8880 \
  --restart=always \
  kokoro-fastapi-gpu:latest

echo "Container rebuilt and started!"
echo "Testing API..."
sleep 10
curl -s http://localhost:8880/health | jq .status || echo "API not ready yet"