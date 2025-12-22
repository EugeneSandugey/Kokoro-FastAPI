FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

WORKDIR /app

# Install ffmpeg and curl (curl needed for healthcheck)
RUN apt-get update && apt-get install -y ffmpeg curl && rm -rf /var/lib/apt/lists/*

# Upgrade to latest torch/torchaudio for forced alignment support
# Also install faster-whisper for diarization (loaded on-demand)
RUN pip install --no-cache-dir \
    torch==2.5.1 \
    torchaudio==2.5.1 \
    fastapi \
    uvicorn \
    faster-whisper \
    pyannote.audio

# Set library path for cuDNN
ENV LD_LIBRARY_PATH=/opt/conda/lib/python3.10/site-packages/nvidia/cudnn/lib:/opt/conda/lib/python3.10/site-packages/nvidia/cublas/lib:$LD_LIBRARY_PATH

# Copy server
COPY server.py .

# Expose port
EXPOSE 8881

# Run server
CMD ["python3", "server.py"]
