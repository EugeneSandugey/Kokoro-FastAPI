#!/bin/bash
set -euo pipefail

echo "=== F5-TTS RunPod Training ==="
echo "Started: $(date -u)"
echo "Pod: ${RUNPOD_POD_ID:-unknown}"
echo "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo 'unknown')"

# ---- Configuration from environment variables ----
RUN_NAME="${RUN_NAME:?RUN_NAME required}"
LEARNING_RATE="${LEARNING_RATE:?LEARNING_RATE required}"
BATCH_SIZE="${BATCH_SIZE:-5000}"
EPOCHS="${EPOCHS:-8}"
WARMUP_UPDATES="${WARMUP_UPDATES:-50}"
SAVE_PER_UPDATES="${SAVE_PER_UPDATES:-500}"
KEEP_LAST_N="${KEEP_LAST_N:-3}"
LAST_PER_UPDATES="${LAST_PER_UPDATES:-200}"
MAX_SAMPLES="${MAX_SAMPLES:-32}"
GRAD_ACCUM="${GRAD_ACCUM:-1}"
MAX_GRAD_NORM="${MAX_GRAD_NORM:-1.0}"
CHECKPOINT_ACTIVATIONS="${CHECKPOINT_ACTIVATIONS:-False}"
DATASET_NAME="${DATASET_NAME:-kokoro_libri}"
CONFIG_NAME="${CONFIG_NAME:-F5TTS_RunPod_Base}"

VOLUME="/workspace"
F5_ROOT="/app/F5-TTS"
RESULTS_DIR="${VOLUME}/results/${RUN_NAME}"
STATUS_DIR="${VOLUME}/status"

echo ""
echo "Config:"
echo "  RUN_NAME:      ${RUN_NAME}"
echo "  LEARNING_RATE: ${LEARNING_RATE}"
echo "  BATCH_SIZE:    ${BATCH_SIZE}"
echo "  EPOCHS:        ${EPOCHS}"
echo "  DATASET_NAME:  ${DATASET_NAME}"
echo "  CONFIG_NAME:   ${CONFIG_NAME}"
echo ""

# ---- Verify volume is mounted ----
if [ ! -d "${VOLUME}/data" ]; then
    echo "FATAL: Network volume not mounted or data missing at ${VOLUME}/data"
    echo "Contents of ${VOLUME}:"
    ls -la "${VOLUME}/" 2>/dev/null || echo "(empty or not mounted)"
    exit 1
fi

# ---- Create symlinks: volume data -> F5-TTS expected paths ----
echo "Setting up symlinks..."

# Data directory
rm -rf "${F5_ROOT}/data"
ln -sf "${VOLUME}/data" "${F5_ROOT}/data"
echo "  data/ -> ${VOLUME}/data/"

# Create results and status dirs
mkdir -p "${RESULTS_DIR}"
mkdir -p "${STATUS_DIR}"

# Checkpoint directory: create ckpts/ in F5 root, symlink the run dir
rm -rf "${F5_ROOT}/ckpts"
mkdir -p "${F5_ROOT}/ckpts"
ln -sf "${RESULTS_DIR}" "${F5_ROOT}/ckpts/${RUN_NAME}"
echo "  ckpts/${RUN_NAME}/ -> ${RESULTS_DIR}/"

# TensorBoard runs directory
rm -rf "${F5_ROOT}/runs"
mkdir -p "${VOLUME}/runs"
ln -sf "${VOLUME}/runs" "${F5_ROOT}/runs"
echo "  runs/ -> ${VOLUME}/runs/"

# ---- CRITICAL: Copy pretrained weights into checkpoint dir ----
if [ ! -f "${RESULTS_DIR}/pretrained_model.safetensors" ]; then
    if [ ! -f "${VOLUME}/pretrained/pretrained_model.safetensors" ]; then
        echo "FATAL: pretrained_model.safetensors not found on volume"
        echo "FAILED: pretrained weights missing from volume" > "${STATUS_DIR}/${RUN_NAME}.failed"
        exit 1
    fi
    echo "Copying pretrained weights..."
    cp "${VOLUME}/pretrained/pretrained_model.safetensors" "${RESULTS_DIR}/"
    echo "  Copied $(du -sh "${RESULTS_DIR}/pretrained_model.safetensors" | cut -f1)"
else
    echo "  Pretrained weights already in results dir (resuming?)"
fi

# ---- Verify dataset ----
DATASET_PATH="${F5_ROOT}/data/${DATASET_NAME}_pinyin/raw.arrow"
if [ ! -f "${DATASET_PATH}" ]; then
    echo "FATAL: Dataset not found at ${DATASET_PATH}"
    echo "FAILED: dataset missing" > "${STATUS_DIR}/${RUN_NAME}.failed"
    exit 1
fi
echo "  Dataset verified: $(du -sh "${F5_ROOT}/data/${DATASET_NAME}_pinyin/" | cut -f1)"

# ---- Check for existing checkpoint (resume support) ----
EXISTING_CKPT=$(ls -t "${RESULTS_DIR}"/model_last.pt 2>/dev/null | head -1)
if [ -n "${EXISTING_CKPT}" ]; then
    echo "  Found existing checkpoint: ${EXISTING_CKPT} (will resume)"
fi

echo ""
echo "=== Starting training at $(date -u) ==="
echo ""

cd "${F5_ROOT}"

# Run training with Hydra command-line overrides
accelerate launch src/f5_tts/train/train.py \
    --config-name "${CONFIG_NAME}" \
    "optim.learning_rate=${LEARNING_RATE}" \
    "optim.epochs=${EPOCHS}" \
    "optim.num_warmup_updates=${WARMUP_UPDATES}" \
    "optim.grad_accumulation_steps=${GRAD_ACCUM}" \
    "optim.max_grad_norm=${MAX_GRAD_NORM}" \
    "datasets.name=${DATASET_NAME}" \
    "datasets.batch_size_per_gpu=${BATCH_SIZE}" \
    "datasets.max_samples=${MAX_SAMPLES}" \
    "ckpts.save_per_updates=${SAVE_PER_UPDATES}" \
    "ckpts.keep_last_n_checkpoints=${KEEP_LAST_N}" \
    "ckpts.last_per_updates=${LAST_PER_UPDATES}" \
    "ckpts.save_dir=ckpts/${RUN_NAME}" \
    "ckpts.log_samples=False" \
    "ckpts.logger=tensorboard" \
    "model.arch.checkpoint_activations=${CHECKPOINT_ACTIVATIONS}" \
    "hydra.run.dir=ckpts/${RUN_NAME}" \
    2>&1 | tee "${RESULTS_DIR}/train.log"

TRAIN_EXIT=${PIPESTATUS[0]}

echo ""
echo "=== Training finished at $(date -u) | exit code: ${TRAIN_EXIT} ==="

# ---- Signal completion ----
if [ ${TRAIN_EXIT} -eq 0 ]; then
    # Write completion file with summary
    {
        echo "SUCCESS"
        echo "finished: $(date -u)"
        echo "run_name: ${RUN_NAME}"
        echo "learning_rate: ${LEARNING_RATE}"
        echo "batch_size: ${BATCH_SIZE}"
        echo "epochs: ${EPOCHS}"
        # Extract final loss from log
        FINAL_LOSS=$(grep -oP 'loss=[\d.]+' "${RESULTS_DIR}/train.log" | tail -1 | cut -d= -f2)
        echo "final_loss: ${FINAL_LOSS:-unknown}"
        # List checkpoints
        echo "checkpoints:"
        ls -lh "${RESULTS_DIR}"/model_*.pt 2>/dev/null | awk '{print "  " $NF " (" $5 ")"}'
    } > "${STATUS_DIR}/${RUN_NAME}.done"
    echo "Status: SUCCESS (${STATUS_DIR}/${RUN_NAME}.done)"
else
    {
        echo "FAILED: exit code ${TRAIN_EXIT}"
        echo "finished: $(date -u)"
        echo "run_name: ${RUN_NAME}"
    } > "${STATUS_DIR}/${RUN_NAME}.failed"
    echo "Status: FAILED (${STATUS_DIR}/${RUN_NAME}.failed)"
fi

# Keep pod alive briefly for log retrieval, then exit
echo "Sleeping 30s for log retrieval..."
sleep 30
echo "Exiting."
