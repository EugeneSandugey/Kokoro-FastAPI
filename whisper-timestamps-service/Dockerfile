FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

WORKDIR /app

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Install dependencies (nvidia-cudnn-cu12 provides cuDNN 9 for faster-whisper)
RUN pip install --no-cache-dir fastapi uvicorn faster-whisper nvidia-cudnn-cu12

# Set library path for cuDNN
ENV LD_LIBRARY_PATH=/opt/conda/lib/python3.10/site-packages/nvidia/cudnn/lib:/opt/conda/lib/python3.10/site-packages/nvidia/cublas/lib:$LD_LIBRARY_PATH

# Copy server
COPY server.py .

# Expose port
EXPOSE 8881

# Run server
CMD ["python3", "server.py"]
