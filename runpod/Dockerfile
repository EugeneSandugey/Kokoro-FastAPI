FROM pytorch/pytorch:2.4.0-cuda12.4-cudnn9-devel

USER root
ARG DEBIAN_FRONTEND=noninteractive

LABEL maintainer="kokoro-training"
LABEL description="F5-TTS training image for RunPod parallel sweeps"

# System dependencies (matching upstream F5-TTS Dockerfile)
RUN set -x \
    && apt-get update \
    && apt-get -y install wget curl man git less openssl libssl-dev unzip build-essential \
    && apt-get install -y openssh-server sox libsox-fmt-all libsox-fmt-mp3 libsndfile1-dev ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install F5-TTS at /app/F5-TTS/ (NOT /workspace/ which is the volume mount)
WORKDIR /app

RUN git clone https://github.com/SWivid/F5-TTS.git \
    && cd F5-TTS \
    && git checkout 655fbca5529b68e36d7b8f2d6d131f68132156fe \
    && git submodule update --init --recursive \
    && pip install -e . --no-cache-dir

# Additional utilities for monitoring and data transfer
RUN pip install --no-cache-dir tensorboard

# Copy our custom config with correct architecture settings
# (upstream configs have wrong text_mask_padding/pe_attn_head for our pretrained weights)
COPY F5TTS_RunPod_Base.yaml /app/F5-TTS/src/f5_tts/configs/F5TTS_RunPod_Base.yaml

# Copy entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

WORKDIR /app/F5-TTS

ENV SHELL=/bin/bash
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/app/entrypoint.sh"]
