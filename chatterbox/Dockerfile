FROM nvidia/cuda:12.1.0-base-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN python3 -m pip install --upgrade pip

# Install PyTorch with CUDA support (without flash-attn)
RUN pip3 install torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121

# Install Chatterbox and Flask
RUN pip3 install chatterbox-tts flask

# Create working directory
WORKDIR /app

# Copy server script
COPY server.py /app/server.py

# Expose port
EXPOSE 8881

# Run the server
CMD ["python3", "/app/server.py"]