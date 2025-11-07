#!/bin/bash
# Build and deploy Kokoro with CUDA self-recovery

cd /home/echo/projects/kokoro

echo "Building Kokoro with CUDA recovery..."
docker build -f Dockerfile.kokoro-recovery -t kokoro-recovery:latest .

echo "Stopping existing Kokoro container..."
docker stop kokoro-tts 2>/dev/null
docker rm kokoro-tts 2>/dev/null

echo "Starting Kokoro with self-recovery..."
docker run -d \
  --name kokoro-tts \
  --gpus all \
  -p 8880:8880 \
  --restart unless-stopped \
  -v /home/echo/projects/kokoro/kokoro_api_patch.py:/app/kokoro_api_patch.py:ro \
  kokoro-recovery:latest

echo "Waiting for Kokoro to start..."
sleep 10

echo "Checking logs..."
docker logs kokoro-tts --tail 20

echo "Done! Kokoro is now running with automatic CUDA error recovery."