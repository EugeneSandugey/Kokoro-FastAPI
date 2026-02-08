# Kokoro TTS Project - Project Memory

<overview>
Self-hosted Kokoro TTS on RTX 4090. Fast, high-quality speech synthesis with 66 voices across 8 languages.

| Component | Value |
|-----------|-------|
| Version | v0.2.4 (Docker: ghcr.io/remsky/kokoro-fastapi-gpu) |
| Port | 8880 |
| GPU | RTX 4090 (~5.5GB VRAM single instance, ~10.5GB for 5 instances) |
| Performance | ~2.3s for 2-min audio (50x+ realtime) |
| Container | kokoro-tts |
</overview>

<team>
## Project Team

| Agent | Role | Brain | Location |
|-------|------|-------|----------|
| **kokoro** (me) | Training system lead, TTS optimization, model development | Claude | ~/projects/kokoro/ |
| **stt** | STT validation system, quality metrics, Parakeet/Qwen engines | Claude | ~/projects/stt/ |
| **chat-validator** | Independent research, second opinions, plan critique | ChatGPT | ~/projects/chat-validator/ |

**Collaboration model:**
- I (kokoro) own the training pipeline and TTS model development
- STT agent owns the validation/quality measurement system (port 11401)
- chat-validator provides independent perspective (different AI brain = different biases)
- For major decisions: independent research → mutual critique → converged plan

**CRITICAL - Inter-Agent Messaging Rule:**
- Agents have ZERO shared context. They see ONLY the message you send them.
- NEVER summarize. Send FULL detailed content.
- Your message IS your output. The other agent sees nothing else.
- Include ALL relevant context, data, code, specifications in the message itself.
- There is no user in the middle. This is agent-to-agent, not agent-to-human.
- If you need to share a plan, send the ENTIRE plan, not a summary of it.
- If you need to share data, include the ACTUAL data, not a description of it.
</team>

<services>
## Whisper Timestamps Service (port 8881)
GPU container running distil-large-v3 for word-level timestamp generation.

| Attribute | Value |
|-----------|-------|
| Container | whisper-timestamps |
| VRAM | ~2GB |
| Latency | ~200-250ms |
| Location | `/home/echo/projects/kokoro/whisper-timestamps-service/` |

Used by `speak` command for Kokoro/Gemini word captions.

```bash
# Status/restart
docker ps | grep whisper-timestamps
curl http://localhost:8881/health
cd /home/echo/projects/kokoro/whisper-timestamps-service && docker compose restart
```
</services>

<quick_reference>
## Quick Start
```bash
# Check/restart Kokoro
docker ps | grep kokoro
docker restart kokoro-tts

# Test TTS
curl -X POST http://localhost:8880/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Test", "voice": "af_heart", "speed": 1.25}' -o test.mp3
```

## Speak Command
Location: `/usr/local/bin/speak`
Backend: `/home/echo/projects/guardian-angel-voice-interface/wsl_guardian_angel_speak_queue_aware.py`

Features: Queue-aware playback, media control (pauses Chrome/YouTube/Spotify), agent routing, voice aliases, speed control.
</quick_reference>

<voice_aliases>
## Voice Aliases

**Kokoro (default)**:
- f1-f4: af_heart, af_bella, af_sky, af_aoede
- m1-m4: am_fenrir, am_puck, am_michael, bm_george
- s1-s3: af_dora, em_alex, em_santa (Spanish)

**Gemini** (--gemini): f1=Laomedeia, f2=Zephyr, f3=Aoede, m1=Puck

**Inworld** (--inworld): f1=Sarah, f2=Deborah, f3=Ashley, m1=Dennis, m2=Mark, bf1=Olivia, bf2=Wendy

```bash
speak --voice f1 "Kokoro default"
speak --gemini --voice f1 "Gemini Laomedeia"
speak --inworld --voice f1 "Inworld Sarah"
```
</voice_aliases>

<tts_backends>
## TTS Backend Selection

| Backend | Flag | Use When |
|---------|------|----------|
| **Kokoro** | (default) | Sensitive data, fastest (~0.22s), English/Spanish, offline |
| **Gemini** | --gemini | Multi-language, emotional, non-sensitive (Google trains on free tier) |
| **Inworld** | --inworld | Highest quality (#1 TTS Arena), word timestamps, ~$3.60/month |

### Privacy Notes
- **Kokoro**: Fully local, no data leaves system
- **Gemini Free**: Data used for Google training - avoid for confidential work
- **Gemini Paid**: Data not used for training (~$1.20/month)
- **Inworld**: API-based, data goes to Inworld servers
</tts_backends>

<available_voices>
## Available Voices (66 total)

**American English**
- Female (af_): alloy, aoede, bella, heart, jadzia, jessica, kore, nicole, nova, river, sarah, sky
- Male (am_): adam, echo, eric, fenrir, liam, michael, onyx, puck, santa

**British English**
- Female (bf_): alice, emma, lily
- Male (bm_): daniel, fable, george, lewis

**Other Languages**: Spanish (ef_/em_), French (ff_), Hindi (hf_/hm_), Italian (if_/im_), Japanese (jf_/jm_), Portuguese (pf_/pm_), Chinese (zf_/zm_)
</available_voices>

<implementation>
## Implementation Details

### Code Flow
1. `speak [--gemini|--inworld] "text"` → bash wrapper
2. Python script parses flags → selects backend
3. Backend generates audio → saves MP3
4. Guardian Angel handles queue/media control (all backends)

### Key Files
| File | Purpose |
|------|---------|
| `/usr/local/bin/speak` | Bash wrapper |
| `wsl_guardian_angel_speak_queue_aware.py` | Main TTS logic |
| `/home/echo/bin/docker-speak-proxy.py` | Docker agent proxy (port 8885) |

### API Keys (gitignored)
- Gemini: `/home/echo/projects/kokoro/Google_gemini_tts/config.py`
- Inworld: `/home/echo/projects/kokoro/inworld_tts/config.py`
</implementation>

<guardian_angel_integration>
## Guardian Angel Integration

All backends share these features:
- **Media Control**: Pauses Chrome/YouTube/Spotify before speaking
- **Queue Management**: Prevents audio overlap via nginx API (port 8443)
- **Duration Tracking**: ffprobe + 10% buffer for accurate timing
- **Agent Routing**: Uses SPEAKING_AGENT_ID or tmux session
- **Beep Sound**: Handled by frontend before TTS plays
</guardian_angel_integration>

<troubleshooting>
## Troubleshooting

| Issue | Solution |
|-------|----------|
| "API_KEY not found" | Check config.py exists, or set env var |
| Audio popping | Verify chunks collected before WAV write |
| Media control fails | Check Guardian Angel logic runs after model branches |
| Slow Gemini | Expected ~1-2s WebSocket overhead |
| Voice not found | Use correct backend's voice names |
</troubleshooting>

<model_info>
## Model Info

| Attribute | Value |
|-----------|-------|
| Size | 82M parameters |
| Architecture | StyleTTS 2 |
| License | Apache 2.0 |
| RTF | ~210× on RTX 4090 |
| Fine-tuning | Not supported (pre-defined voice packs only) |
</model_info>

<docker_setup>
## Docker Setup

```yaml
# ~/projects/kokoro/docker/gpu/docker-compose.yml
services:
  kokoro-tts:
    image: ghcr.io/remsky/kokoro-fastapi-gpu:v0.2.4
    ports: ["8880:8880"]
    deploy:
      resources:
        reservations:
          devices: [{driver: nvidia, count: 1, capabilities: [gpu]}]
```

Recovery scripts in `~/projects/kokoro/`:
- `kokoro-monitor.sh`, `restart-kokoro-with-recovery.sh`, `kokoro_api_patch.py`
</docker_setup>

<recent_updates>
## Recent Updates
- **2025-11-30**: Added whisper-timestamps service (port 8881) - 200ms latency vs 1.2s per-call
- **2025-11-29**: Fixed Inworld word timestamp fuzzy mapping (hyphen/compound splits)
- **2025-11-28**: Added Inworld TTS (--inworld), 7 voices, HD model, word timestamps
- **2025-11-07**: Voice aliases now backend-aware (f1 maps differently per backend)
- **2025-08-31**: Updated to v0.2.4, fixed exclamation escaping
- **2026-02-02**: Benchmarked 1-5 instances (56x-139x realtime), explored TTS API business
- **2026-02-03**: Downloaded Gemini Flash 2.0 Speech dataset (279hrs, 45GB) to NAS P: drive
- **2026-02-03**: Built STT validation pipeline spec (tiered Parakeet→Qwen voting system)
- **2026-02-03**: Generated Alice in Wonderland test dataset (378 chunks, 2.26hrs) for validator testing
- **2026-02-03**: Validated Parakeet: 98.5% confidence on Kokoro audio, 507x realtime on 20min file
- **2026-02-03**: Researched available TTS datasets — most large ones are mediocre LibriVox quality
- **2026-02-03**: NAS P: drive mounted in WSL via `sudo mount -t drvfs P: /mnt/p` (38TB, 30TB free)
- **2026-02-03**: STT agent fixed normalization: hyphens→spaces, underscores stripped, 47 homophone pairs (commit 8729f82)
- **2026-02-03**: STT agent deployed compound/spelling_variant/gt_error verdicts (commit 989283b)
- **2026-02-03**: Full dual-engine validation confirmed: **100% pass rate**, 0 tts_failures on 713 words (10 chunks)
- **2026-02-03**: Requested two pipeline modes from STT: batch (step-sequential) + stream (file-sequential)
- **2026-02-03**: STT agent shipped per-judge timing, word-level confidence, new verdicts, save-to-disk (commit 80855e0)
- **2026-02-03**: 3-way comparison: Kokoro MOS 4.12 > Gemini 3.90 > LibriTTS-R 3.78. Gemini 99.3% pass after new verdicts
- **2026-02-03**: Chat-validator critique: reward hacking risk, forced alignment suggestion, phonetic similarity > lists, need human MOS calibration
- **2026-02-03**: Accepted chat-validator proposal for concrete scoring/routing policy with thresholds and cascade
- **2026-02-03**: Dataset comparison (STT accuracy): LibriTTS-R 60.5% zero-WER (best) > Gemini 41% > Kokoro 36.5%
- **2026-02-03**: Gemini dataset has 41.5% files above 5% WER — needs heavy filtering for training
- **2026-02-03**: Extracted 200 Gemini samples (100 Kore + 100 Puck) and 200 LibriTTS-R samples for testing
- **2026-02-03**: Converged training plan complete (899 lines), licensing decision made (Research mode)
- **2026-02-03**: Added Gemini 2.5 native audio data generation strategy to plan (unlimited free training data)
- **2026-02-03**: Researched: synthetic TTS training validated by research (can outperform real data)
- **2026-02-03**: Added enterprise GPU benefits section (A100 80GB enables 4x batch, larger models, concurrent eval)
- **2026-02-03**: Sent critique request to chat-validator for Round 2 review
- **2026-02-05**: Kokoro synthetic training completed: 30 epochs, ~21,986 updates, loss 0.3-0.6
- **2026-02-05**: Objective MOS+STT comparison of 6 models × 4 speakers (24 files)
- **2026-02-05**: KEY FINDING: kokoro_synthetic 7k (MOS 4.174) beats 21k (MOS 4.016) — overfitting after ~7k
- **2026-02-05**: All fine-tuned models beat pretrained base (3.738). Synthetic data > human data for MOS.
- **2026-02-05**: Fresh perspective: LR too conservative (1e-6), need LR sweep, plan-vs-reality gap identified
- **2026-02-05**: Updated global CLAUDE.md with context_sync_protocol + team_dynamics sections
- **2026-02-05**: Eugene identified homograph blind spot (lives /laɪvz/ vs /lɪvz/) — STT validator completely blind to this class
- **2026-02-05**: 3-agent collaboration: kokoro coordinated, STT built, chat-validator pressure-tested
- **2026-02-05**: Homograph phoneme validator Phase 1 built: wav2vec2 + panphon + BERT classifiers + 6 verdict types
- **2026-02-05**: Generated 30 negative control audio files (15 correct + 15 wrong pronunciations, 15 homographs)
- **2026-02-05**: Calibration: 91.7% error detection, 50% precision (IPA mapping mismatch root cause)
- **2026-02-05**: Ship decision: allowlist mode — live, lives, wind, conduct active. All else → context_ambiguous
- **2026-02-05**: Deployed and verified on 378 Alice files: 14 correct, 1 suspect, 113 ambiguous, 0 false positives
- **2026-02-06**: Built 100-prompt eval set across 10 categories (numbers, decimals, dates, currency, negations, quotes, lists, abbreviations, homographs, long prosody)
- **2026-02-06**: Generated 500 eval audio files (100 prompts × 5 models: kokoro_production, base_pretrained, libri_7k, kokoro_17k, kokoro_21k)
- **2026-02-06**: KEY CORRECTION: "7k beats 21k" was statistical artifact (4 samples). With 100 prompts: kokoro_21k (4.417) > libri_7k (4.399)
- **2026-02-06**: KEY FINDING: Kokoro production (4.583) beats ALL F5-TTS models (+0.15-0.18 fair composite MOS)
- **2026-02-06**: Discovered F5-TTS audio clipping issue: 91-97% of files exceed [-1,1] range, breaking DNSMOS
- **2026-02-06**: Fair comparison uses NISQA+SCOREQ only. F5 fine-tuning helps only marginally (0.03 MOS) at LR 1e-6
- **2026-02-06**: LR sweep training completed (5e-6, 1e-5, 5e-5) × 8 epochs × 425 updates/epoch = ~3400 steps each
- **2026-02-06**: Storage cleanup: 200GB → 82GB project, freed 118GB by archiving to NAS
- **2026-02-06**: Archived obsolete checkpoints to `/mnt/p/kokoro-training-archive/`
- **2026-02-06**: Disk full crash during 5e-5 training → re-ran after cleanup
- **2026-02-07**: Built RunPod parallel training pipeline (Dockerfile, entrypoint, sweep launcher)
- **2026-02-07**: Platform research: RunPod > Vast.ai (shared Network Volumes) > SaladCloud (no persistence)
- **2026-02-07**: Docker image: f5tts-train (PyTorch 2.4 + CUDA 12.4 + F5-TTS @ commit 655fbca)
- **2026-02-07**: RunPod sweep.py CLI: launch/monitor/cleanup/results for parallel HPO
</recent_updates>

<storage_archive>
## Storage Archive (NAS Network Drive)

**Archive location**: `/mnt/p/kokoro-training-archive/` (NAS P: drive, 38TB total, ~29TB free)
**Date archived**: 2026-02-06
**Space freed**: 118GB (project: 200GB → 82GB, disk: 44GB free → 135GB free)

### Archived Checkpoints (`/mnt/p/kokoro-training-archive/ckpts/`)

| Directory | Size | Contents | Why Archived |
|-----------|------|----------|--------------|
| `F5TTS_Base_vocos_pinyin_smoke_test_prepared/` | 22GB | Smoke test runs | Testing complete |
| `F5TTS_Base_vocos_pinyin_libri_200/` | 32GB | Early LibriTTS run (200 samples) | Superseded by libri_filtered |
| `F5TTS_Base_vocos_pinyin_libri_full/` | 12GB | Full LibriTTS run | Superseded by libri_filtered |
| `F5TTS_Base_vocos_pinyin_kokoro_libri_pinyin/` | 28KB | Dataset naming error dir | Empty, cleanup |

### Archived Experiments (`/mnt/p/kokoro-training-archive/`)

| Directory | Size | Contents | Why Archived |
|-----------|------|----------|--------------|
| `chatterbox/` | 3GB | Chatterbox TTS experiment | Not actively used |

### Kept Locally (Essential for Current Work)

| Directory | Size | Contents |
|-----------|------|----------|
| `F5TTS_Base_vocos_pinyin_libri_filtered/` | 6.3GB | model_7000.pt + pretrained (best LibriTTS model) |
| `F5TTS_Base_vocos_pinyin_kokoro_libri/` | 12GB | model_17000.pt + model_21000.pt + pretrained |
| `lr_sweep_5e6/` | 22GB | LR 5e-6 training (complete) |
| `lr_sweep_1e5/` | 22GB | LR 1e-5 training (complete) |
| `lr_sweep_5e5/` | ~22GB | LR 5e-5 training (re-run after disk crash) |

### Deleted Locally (Not Archived)

Intermediate checkpoints deleted to save space (only kept final/best checkpoints):
- `libri_filtered/`: model_5000, 6000, 8000, 9000, model_last (~25GB deleted)
- `kokoro_libri/`: model_18000, 19000, 20000, model_last (~20GB deleted)

### Recovery Commands
```bash
# Mount NAS if not mounted
sudo mount -t drvfs P: /mnt/p

# Check archive contents
ls -la /mnt/p/kokoro-training-archive/ckpts/

# Restore a checkpoint (if needed)
cp -r /mnt/p/kokoro-training-archive/ckpts/F5TTS_Base_vocos_pinyin_smoke_test_prepared \
      /home/echo/projects/kokoro/training/F5-TTS/ckpts/
```

### Disk Space Management Policy
- Keep only essential checkpoints locally (final + best models)
- Archive completed experiments to NAS immediately
- Target: Keep project folder under 100GB
- Current local checkpoint size: ~85GB
</storage_archive>

<critique_insights>
## Chat-Validator Critique Key Insights (Feb 2026)

**Risks identified:**
- **Reward hacking**: Optimizing solely for STT accuracy → robotic over-articulated speech. Need multi-objective training signal.
- **"Both wrong = TTS failure" is unreliable**: Shared normalization biases, LM autocorrect can cause false convergence.
- **MOS judge drift**: Objective MOS predictors drift out-of-domain. Need periodic human calibration.
- **Data provenance**: HF license label ≠ commercial safety. Gemini dataset has precedent (Kokoro used it) but verify.
- **Synthetic-only bootstrapping**: Risk of "learning the teacher's accent" — mix in real speech.

**Improvements suggested:**
- Phonetic similarity (G2P → phoneme edit distance) instead of hardcoded homophone/spelling lists
- Forced alignment/decoding instead of free-form for per-word confidence (faster + more stable)
- SCOREQ may be redundant with NISQA — test with correlation analysis
- Multi-objective scoring: intelligibility + naturalness + speaker similarity + DSP sanity
- Cascade for speed: Parakeet on everything → Qwen on flagged only → MOS on passed only

**Awaiting from chat-validator:**
- Concrete scoring/routing policy with thresholds per stage
- Stage cascade design for throughput targets
- Multi-objective weighting for training signal
- Human calibration protocol
- Forced alignment architecture investigation
</critique_insights>

<dataset_comparison>
## Dataset Quality Comparison (STT Accuracy)

Parakeet scan on 200 samples each (Feb 2026):

| Metric | Kokoro Alice | Gemini 200 | LibriTTS-R 200 |
|--------|--------------|------------|----------------|
| Files | 378 | 200 | 200 |
| Duration (min) | 136.0 | 41.3 | 23.7 |
| Mean WER (%) | 3.7 | 19.1* | 3.7 |
| Median WER (%) | 1.6 | 3.3 | 0.0 |
| Zero WER (%) | 36.5% | 41.0% | **60.5%** |
| Above 5% WER | ~22% | 41.5% | **17.0%** |
| Mean Confidence | 98.64% | **98.80%** | 97.89% |

*Gemini mean WER skewed by GT text mismatches (max 1200% WER)

**Key findings:**
- LibriTTS-R (human) has BEST STT accuracy (60.5% zero-WER, 17% above 5%)
- Gemini needs heavy filtering (41.5% of files have WER >5%)
- Kokoro is middle ground (36.5% zero-WER, 22% above 5%)
- Gemini has highest confidence but worst accuracy → GT issues, not TTS quality
- Human speech has more variation → lower confidence but better accuracy

**Data locations:**
- Gemini 200: `/home/echo/projects/kokoro/sttdata/gemini_200/` (100 Kore + 100 Puck)
- LibriTTS-R 200: `/home/echo/projects/kokoro/sttdata/libri_200/`
- Kokoro Alice: `/home/echo/projects/kokoro/sttdata/dev_clean/LibriTTS_R/dev-clean/SAMPLE TEST/book_chunks/`
</dataset_comparison>

<training_plan_summary>
## Converged Training Plan (Feb 2026)

**Plan file**: `/home/echo/projects/kokoro/training_plan_converged_v1.md`
**Authors**: kokoro + chat-validator (independent research → mutual critique → convergence)
**Status**: ✅ RESEARCH MODE SELECTED, implementation-ready

### Licensing Decision (RESOLVED)
- F5-TTS pretrained models are **CC-BY-NC** due to Emilia training data
- **Decision**: Research mode - fine-tune CC-BY-NC weights to prove pipeline
- **Later**: Train from scratch on commercial data for production deployment
- Commercial-safe datasets available: LibriTTS-R (585hr), Gemini (279hr), LJSpeech (24hr)

### Core Architecture
- F5-TTS (flow matching + DiT), optional F5R-style RL post-training
- Quality metrics as **controller-level signals only**, NOT loss replacement
- 5 Components: Trainer | Evaluator | DataManager | Controller | Registry

### NEW: Gemini 2.5 Data Generation Strategy

**Licensing**: Eugene decided licenses are OK for research phase. Will verify for commercial deployment later.

**Technical specs:**
- Eugene has unlimited Gemini 2.5 Flash native audio API access
- 24kHz output matches F5-TTS exactly, 30+ voices, emotion control
- Method: "Transcribe this text: [TEXT]" → capture audio → perfect ground truth
- Research validates: synthetic data can outperform real data for TTS training

**Targeted use strategy** (Eugene's insight):
- Use Gemini 2.5 specifically for hard cases where we get garbage results
- More efficient than generating massive random datasets
- Identify weakness → generate targeted training data → retrain → verify

### Model Size Strategy (from chat-validator Round 2)

**Research Phase (local 4090):**
- Use F5TTS_Small (768/18/12, ~90M) for fast iteration
- Run Base (1024/22/16, ~155M) parity checks weekly
- **CRITICAL**: Default batch (38400 frames = 410s audio) WAY TOO BIG - use 6k-12k frames (60-120s)

**Production Phase (cloud):**
- <1k hours data: Train Base (155M) directly on 4xA100
- Thousands of hours: Train teacher (500M-800M) → distill to Base
- Distillation insight: Spotify found 180M student drops quality vs teacher; 40M drops more

### Compute Strategy
- **Local 4090**: Pipeline testing, hyperparameter sweeps (free, instant iteration)
- **Cloud (production runs)**: 4x A100 40GB (~$4.40/hr) or 4x A100 80GB (~$6-8/hr)
- A100 80GB unlocks: 4x batch size, larger models (up to 1B params), concurrent eval
- **Multi-4090 doesn't scale well** (no P2P support) - prefer single A100/H100
- Expected: 4-8x faster training + potentially better quality from larger batches

### HPO Platform Decision
- **Recommended**: CUSTOM time-sliced PBT/ASHA orchestrator + W&B logging
- Why: No framework fights with Accelerate, easier checkpoint restore
- NOT Optuna (no schedule discovery), NOT Ray Tune (Accelerate conflicts)

### Documentation (saved locally)
- `/home/echo/projects/kokoro/docs/f5-tts/F5TTS_v1_Base.yaml` - Training config
- `/home/echo/projects/kokoro/docs/f5-tts/TRAINING_NOTES.md` - Training guide
- `/home/echo/projects/kokoro/docs/f5-tts/CRITIQUE_FAILURE_MODES.md` - Failure analysis

### Key Failure Risks (from critique)
1. Licensing catastrophe (shipping CC-BY-NC commercially)
2. Text normalization drift → false regressions
3. Device pinning errors (MOS judges silently using GPU)
4. Incomplete checkpoint restore (PBT appears unstable)
5. Eval throughput destruction (30-50% wall time evaluating)

### Pre-Implementation Checklist
- [x] Licensing decision made (research mode)
- [x] Homograph phoneme validator deployed (Phase 1, allowlist: live/lives/wind/conduct)
- [x] Negative controls generated (30 files, 15 homographs)
- [ ] F5-TTS version pinned
- [ ] Device placement assertions on MOS judges
- [ ] Restore fidelity test passing
- [ ] STT validator circuit breaker + timeouts
- [ ] Gemini 2.5 data capture script implemented
- [ ] Homograph IPA mapping normalization
- [x] Expanded eval set (100 sentences, 10 categories) — `sttdata/eval_set/`
- [x] ABX human preference test (7k vs 21k) — REPLACED: 100-prompt eval showed 21k > 7k (artifact resolved)
- [x] LR sweep (5e-6, 1e-5, 5e-5) — training complete, evaluation pending

### Plan File Sections (for reference)
The full plan at `training_plan_converged_v1.md` contains:
- Sections 1-13: Original converged plan (architecture, system design, HPO, eval, data pipeline, etc.)
- **Section 14**: Homograph Phoneme Validation System (added 2026-02-05)
- **Section 15**: F5-TTS Training Results & Model Comparison (added 2026-02-05)
- **Section 16**: Failure Modes & Risk Analysis (added 2026-02-05)
</training_plan_summary>

<tts_api_business>
## TTS API Business Research (Feb 2026)

**SaladCloud account**: $5 credits loaded. Container Groups for Kokoro deployment ready.
- Deploy via: Custom Container Group → `ghcr.io/remsky/kokoro-fastapi-gpu:v0.2.4` → RTX 3060 → $0.03-0.04/hr

**Training plan**: F5-TTS from scratch with automated STT feedback loop
- Architecture: Flow Matching + DiT (no phonemes needed)
- Training data: Kokoro bulk (free) + ElevenLabs targeted ($99) + LibriTTS (free)
- Automated QA: Multi-STT scoring (Whisper + NVIDIA Parakeet + SenseVoice)
- Training infra: Vast.ai 4x RTX 3090 (~$0.30-0.50/hr) or single A100 (~$1-1.50/hr)
- Serving infra: Salad replicas (RTX 3060 at $0.03/hr)
- Budget estimate: $1,100-2,600 total

**Key insight**: TTS→STT feedback loop for automated training data scoring.
Generate speech → transcribe with multiple STT engines → diff against input →
tag failures → generate correct audio from premium source → retrain → re-score.

**Market opportunity**: RapidAPI TTS marketplace is garbage. No Kokoro. OpenAI resellers with 8.5s latency.
Kokoro cost to serve: $0.01-0.08/M chars. Market price: $0.65-0.80/M chars. 90-99% margins.

**Training approach**: Start small → scale up
- Phase 1: 40M model locally on 4090 (learn pipeline, fast iteration, free)
- Phase 2: 155M model locally on 4090 (full dataset, compete with Kokoro, free)
- Phase 3: 300M model on Vast.ai 4x3090 (teacher model, $50-150)
- Phase 4: Distill 300M→155M→82M→40M, quantize, open source small, serve big via API

**Architecture**: F5-TTS (Flow Matching + DiT)
- Train big (300M, BF16), then compress: distill + prune + quantize
- Distillation: big teacher → small student (student learns from teacher's output, not raw audio)
- Pruning: remove near-zero weights (50% params, 95-98% quality retained)
- Quantization: reduce precision post-training (BF16→INT8→INT4)
- Cost scaling is LINEAR not exponential (2x params ≈ 2x compute/VRAM)

**Hardware for training**:
- RTX 4090 (24GB): up to ~200M with optimization, 155M comfortably, 40M trivially
- RTX 3070 (8GB): 40M only, too small for larger models
- Vast.ai 4x3090: for 300M+ models (~$0.30-0.50/hr)

**VRAM note**: F5-TTS is dramatically more efficient than StyleTTS 2 (Kokoro's arch).
StyleTTS 2 loads 600M+ param WavLM discriminator during training → needs 40-80GB.
F5-TTS has no discriminator/diffusion/adversarial → trains on 10GB RTX 3080.

**Hyperparameter optimization**: Use Optuna + STT scoring as objective function.
- Run 100 short trials on 40M model (2 min each, free on 4090)
- Optuna uses Bayesian optimization (each trial learns from previous)
- STT accuracy is the objective (not training loss)
- Population Based Training (PBT) for evolutionary approach

**Data generation pipeline**:
- Text source: LibriTTS-R (585 hrs, 2456 speakers, free, openslr.org/141/)
- LibriTTS-R includes paired text + audio (24kHz, sentence-segmented, cleaned)
- LibriTTS-R audio quality is mediocre (LibriVox volunteer readers)
- Compare: run LibriTTS-R audio vs Kokoro-regenerated audio through STT validator
- Keep whichever scores higher per sentence → best-of-both dataset
- Reject pile → ElevenLabs shopping list for targeted corrections
- Also: Project Gutenberg (70K+ books), Wikipedia dumps for more text

**Training datasets downloaded**:
- **LibriTTS-R dev-clean** — 13.8 hrs raw (8.9 hrs prepared), 5737 samples, multi-speaker human speech
  - Location: `/home/echo/projects/kokoro/sttdata/dev_clean/LibriTTS_R/dev-clean/` (2.4GB)
  - F5-TTS prepared: `training/F5-TTS/data/libri_full_pinyin/` (5737 samples)
  - Includes `.normalized.txt` files with cleaned transcripts
  - CC BY 4.0 license, professional studio quality (better than LibriVox)
  - Source: [openslr.org/141](https://openslr.org/141) (full dataset is 585 hrs)
- **Gemini Flash 2.0 Speech** — 279 hrs, 47,256 rows, 2 voices (Kore/Puck), 24kHz
  - Location: `/mnt/p/AI-Training-Data/gemini-flash-2.0-speech/` (45GB, NAS P: drive)
  - Load: `from datasets import load_from_disk; ds = load_from_disk('/mnt/p/AI-Training-Data/gemini-flash-2.0-speech')`
  - Source: [huggingface.co/datasets/shb777/gemini-flash-2.0-speech](https://huggingface.co/datasets/shb777/gemini-flash-2.0-speech)
  - **Used to train Kokoro** — high quality synthetic audio from Google, split='en'
  - Each row: kore (female) + puck (male) audio arrays + text + phoneme_length
  - MIT-like license, commercially usable

**Other available datasets (not downloaded)**:
- Parler-TTS MLS: 45K hrs, Apache 2.0, LibriVox-sourced (mediocre quality)
- MLS: 50.5K hrs (44.5K EN), CC BY 4.0, LibriVox-sourced (mediocre quality)
- Emilia: 250K+ hrs, 6 languages, **CC BY-NC 4.0 (non-commercial only)**
- GigaSpeech: 10K hrs, YouTube/podcasts, Apache 2.0, mixed quality
- ElevenLabs dataset (HF): 2.3 hrs, MIT, tiny but precedent
- Most large free datasets = LibriVox volunteer readers = mediocre audio quality
- High-quality synthetic datasets are small; scraping AI-generated audio from production sites is an alternative

**STT Validator System** (built by STT agent, port 11401):
- Container: `parakeet_confidence`, image: `tts-validator:latest`
- API base: `http://localhost:11401`
- Docs: `GET /api/help`
- Health: `GET /status`
- Source: `/mnt/c/Users/eugen/Desktop/parakeet_confidence_demo.py` (volume-mounted)
- Git: `git@github.com:EugeneSandugey/Live-STT.git` (private)
- STT project memory: `/home/echo/projects/stt/CLAUDE.md`
- Container mount: `/data` = `/home/echo/projects/kokoro/sttdata/`

**STT Validator API Quick Reference**:
```bash
# Single file validation (STT + optional MOS)
curl -X POST http://localhost:11401/api/validate \
  -H "Content-Type: application/json" \
  -d '{"audio_path": "/data/path/to/file.wav", "detail": true, "include_mos": true}'

# Folder validation (batch)
curl -X POST http://localhost:11401/api/validate/folder \
  -H "Content-Type: application/json" \
  -d '{"path": "/data/dev_clean/LibriTTS_R/dev-clean/SAMPLE TEST/book_chunks/", "limit": 10}'

# MOS scoring only (no ground truth needed)
curl -X POST http://localhost:11401/api/mos \
  -H "Content-Type: application/json" \
  -d '{"audio_path": "/data/path/to/file.wav"}'
```
Note: paths inside container use `/data/` prefix (mounted from kokoro/sttdata/)

**STT Engines** (dual-engine validation):
- Parakeet TDT_CTC 1.1B: ~146x RT, ~2.0% WER, native CTC word confidence + timestamps
- Qwen3-ASR 1.7B: ~8x RT, 1.63% WER, precision validator for flagged words
- Total STT VRAM: ~8.4GB

**MOS Quality Judges** (4 active, all run on same GPU):
- DNSMOS (Microsoft): signal/background/overall/p808 MOS, ONNX/CPU
- UTMOSv2 (VoiceMOS 2024 winner): naturalness MOS — **single most important TTS metric**
- SCOREQ (NeurIPS 2024): synthetic_nr/natural_nr MOS, ONNX/CPU
- NISQA: 5-dimensional (tts_mos, noi, dis, col, loud) — diagnoses WHAT is wrong
- Composite MOS = average of all 4 judges' primary scores
- Total MOS VRAM: ~1-2GB additional

**Signal Analysis** (11 metrics, no ML, runs with every MOS request):
- duration, sample_rate, peak_amplitude, rms_db, clipping_pct, silence_pct
- energy_std, dynamic_range_db, zero_crossing_rate, spectral_centroid_hz, spectral_rolloff_hz

**Verdict Logic** (word-level):
- pass: both engines match ground truth
- stt_error: Parakeet wrong, Qwen correct → ignore (Parakeet misrecognized)
- tts_failure: both engines wrong same way → real TTS issue
- ambiguous: both wrong differently → manual review
- qwen_error: Parakeet correct, Qwen wrong → ignore
- homophone: both engines agree on sound-alike word (tale/tail) → not an error
- compound: STT merges adjacent words (book shelves → bookshelves) → not an error
- spelling_variant: British/US spelling (labelled→labeled, centre→center) → not an error
- filler_word: "uh", "um", "hmm" etc. not pronounced → not an error (18 fillers)
- abbreviation: "mph"→"hour" type expansions → not an error (45+ mappings)
- gt_typo: GT has typo, engine correct (Levenshtein 1-2) → not an error
- gt_error: GT text has errors like missing spaces → not an error

**Testing protocol**: ALWAYS use `"engines": "both"` for validation during development.
Only consider Parakeet-only mode after full dual-engine validation is 100% confirmed working.

**Validated results** (10 chunks, 713 words, full dual-engine, all fixes deployed):
- Pass rate: **100.0%** across all 10 chunks, **0 tts_failures**
- Verdict breakdown: 12 stt_errors, 4 compounds, 2 spelling_variants, 2 qwen_errors, 1 homophone, 1 gt_error
- 9 verdict types: pass, stt_error, qwen_error, tts_failure, homophone, spelling_variant, compound, gt_error, ambiguous
- Processing: 23.6s total for 220s audio (~9.3x realtime with both engines)
- MOS scoring (all 4 judges): 5.9s, composite 4.16
- STT agent commits: 8729f82 (normalization), 989283b (compound/spelling/gt_error)

**3-way comparison** (5 files each, full dual-engine + MOS, all verdict fixes):

| Metric | Kokoro | Gemini Kore | Gemini Puck | LibriTTS-R |
|--------|--------|-------------|-------------|------------|
| Pass Rate | 100% | 100% | 100% | 100% |
| Composite MOS | 4.123 | 3.895 | — | 3.775 |
| UTMOSv2 | 3.941 | 3.539 | — | 3.387 |
| TTS Failures | 0 | 0 | 0 | 0 |

- Kokoro beats both on MOS quality. Human recordings (LibriTTS-R) score lowest.
- All verdict types working: filler_word, abbreviation, gt_typo, compound (incl. reverse), spelling_variant
- 1 legitimate ambiguous: "mabini" (rare proper noun, both engines wrong differently)
- Test files: sttdata/gemini_test/ (10 files), sttdata/libri_test/ (5 files)

**Per-judge timing** (chunk_0005, 21.5s audio):
- Parakeet: 200ms | Qwen: 2500ms | UTMOSv2: 2298ms | SCOREQ: 932ms | DNSMOS: 913ms | NISQA: 288ms | Signal: 18ms

**Parallelization plan** (STT agent):
- Phase 1: Concurrent judges — FAILED (WavLM CPU contention), reverted to sequential (commit ee79353)
- Phase 4: Selective Qwen (Parakeet-only bulk, Qwen on flagged ~5%) → STT 2.7s→200ms
- Phase 2: File-level parallelism with dedicated worker processes
- Phase 3: UTMOSv2 tensor batching (hardest, 3-4x potential)
- **MOS sampling** (highest priority optimization): mos_mode=all|sample|flagged_only|none
- SCOREQ vs NISQA: NOT redundant (Pearson=+0.16), keep both judges

**Database integration** (Supabase PostgreSQL, commit b3a9214):
- Table: audio_quality (~74 columns), one row per audio file
- Upsert on (file_hash, dataset) — idempotent re-runs
- /api/scan/parakeet: fast Parakeet-only scan → writes parakeet_* columns
- /api/scan/qwen: precision validation (~7x RT) → writes qwen_* columns (commit d1f01e5)
- /api/scan/mos: quality scoring (~4-5x RT) → writes all judge columns (commit d1f01e5)
- **mos_mode parameter**: all | sample | flagged_only | none (commit d1f01e5)
  - sample mode: mos_sample_rate=0.1 (10%) default, only scores random subset
  - flagged_only: only scores files with tts_failures>0 or ambiguous>0 in DB
- Full Alice scan: 378 files, 136 min audio, scanned in 77s (106x RT), 378 DB rows written
- Worst WER file (31.3%) had 0 tts_failures — all GT text errors from text splitter
- Schema flexible: ALTER TABLE ADD COLUMN is instant, metadata JSONB for ad-hoc data

**Threshold analysis** (Alice dataset, 378 Kokoro-generated files):
- 36.5% have zero WER (perfect), median WER 1.6%, mean confidence 98.64
- Suggested thresholds:
  - Strict (50%): WER < 2% AND Conf > 98%
  - Balanced (78%): WER < 5% AND Conf > 97%
  - Permissive (95%): WER < 10% AND Conf > 95%
- Qwen escalation threshold: WER > 5% OR Conf < 98% (~20-25% of files)
- Bottom 10% (WER 8-31%) are GT text errors, not TTS failures

**Next session**: Compare ~100 files each from LibriTTS-R (human), Gemini Kore (female), Gemini Puck (male) against Kokoro baseline. Dashboard work.

**Test data generated**:
- Alice in Wonderland full book: 378 chunks × ~22s = 2.26 hrs, generated in 2.1 min (63.6x realtime)
- Location: `/home/echo/projects/kokoro/sttdata/dev_clean/LibriTTS_R/dev-clean/SAMPLE TEST/book_chunks/`
- Paired .wav + .txt files, voice=af_heart, speed=1.0, 24kHz mono
- Combined file: `alice_wonderland_full.wav` (373MB, 2h15m)
- 20-min test file: `alice_20min.wav` + `alice_20min.txt`
- Batch generation script: `SAMPLE TEST/batch_generate.py`

**Distillation/Compression strategy**:
- Train 300M teacher model (best quality, BF16)
- Distill → 155M, 82M, 40M student models (learn from teacher's output)
- Prune: remove near-zero weights (50% params, 95-98% quality)
- Quantize: BF16→INT8→INT4 post-training for deployment
- Open source small models (GitHub) → brand recognition
- Serve premium model via paid API → revenue

**Sonnet 5 "Fennec"**: Leaked model ID `claude-sonnet-5@20260203`, possibly releasing 2026-02-03.
82.1% SWE-Bench, stronger coding than Opus 4.5, Sonnet-tier pricing. Unconfirmed.
</tts_api_business>

<cost_analysis>
## Cost Analysis

| Service | Cost |
|---------|------|
| Kokoro (self-hosted) | ~$0.07/hr electricity (212W peak × $0.35/kWh SCE rate) |
| Inworld API | ~$3.60/month typical |
| Gemini Paid | ~$1.20/month typical |
| MiniMax API | $1.38-4.59/hr |

Eugene's electricity: SCE (Southern California Edison), Lancaster CA. ~$0.35/kWh blended average.
RTX 4090 running Kokoro: ~195-212W under load = ~$0.07/hr.
</cost_analysis>

<benchmarks>
## RTX 4090 Throughput Benchmarks (Feb 2026)

Benchmark text: 307 words → 127s (2.1 min) audio @ speed=1.25. Scripts in `/home/echo/projects/kokoro/benchmark/`.
20 requests per instance per test. GPU readings from Windows Task Manager (nvidia-smi in WSL reports higher).

| Instances | Throughput | Avg gen/req | Max gen/req | GPU observed (Win) | Scale | Marginal |
|-----------|-----------|-------------|-------------|-------------------|-------|----------|
| 1 | 56x | 2.3s | 2.8s | ~50-55% | 1.00x | baseline |
| 2 | 91x | 2.7s | 3.7s | ~65-70% | 1.64x | +64% |
| 3 | 114x | 3.1s | 4.1s | ~70-75% | 2.05x | +41% |
| 4 | 132x | 3.6s | 5.3s | unknown | 2.36x | +31% |
| 5 | 139x | 4.3s | 6.4s | unknown | 2.50x | +14% |

**Key findings:**
- Zero concurrency per instance (crashes on 2+ simultaneous reqs to same instance)
- CUDA shares model weights across instances (~13GB for 5 instances, ~6.3GB for 1)
- Per-request latency nearly doubles (2.3s→4.3s) from 1→5 instances = GPU contention
- nvidia-smi (WSL) reports 88-98% SM util at 5 instances; Windows shows ~60% — discrepancy
- Diminishing returns: 4th instance +31%, 5th instance only +14%
- VRAM not a bottleneck (13GB of 24GB used at 5 instances)
- Temp stays cool even at max load (49-53°C peak)
- Power: idle 55W → full load ~200W
- Uses physical CPU cores only (16 threads, not 32 with SMT)
- Max capacity: ~16,700 req/hr (30s clips) or ~4,200 req/hr (2-min clips)
</benchmarks>

<f5tts_setup>
## F5-TTS Training Setup (Feb 2026)

**Location**: `/home/echo/projects/kokoro/training/F5-TTS/`
**Virtual environment**: `training/F5-TTS/venv/`
**Activation**: `source /home/echo/projects/kokoro/training/F5-TTS/venv/bin/activate`

### Smoke Test Results (2026-02-03)

| Model | Params | VRAM Overhead | Batch Size | Throughput | Checkpoint |
|-------|--------|---------------|------------|------------|------------|
| Small | ~90M | ~9.5 GB | 6000 frames | 7 updates/s | 2.4 GB |
| Base | ~155M | ~15 GB | 4000 frames | 5-6 updates/s | 5.1 GB |

### Batch Size Optimization (Base model, 90s tests)

| Batch Size | Updates/s | Frames/s | Audio/s | VRAM | Notes |
|------------|-----------|----------|---------|------|-------|
| 4000 frames | 5.53 | 22,120 | 235s | ~16.8 GB | Safe, leaves headroom |
| 5000 frames | 4.92 | 24,600 | 262s | ~18-19 GB | **Best throughput** |
| 6000+ frames | - | - | - | >20 GB | Spills to RAM ❌ |

**Throughput winner: 5000 frames** (10% faster than 4000 in frames/s)
**Gradient accumulation penalty:** 4000×1 is ~50-60% faster than 2000×2 for same effective batch

**Key findings:**
- **5000 frames** is optimal for pure throughput on 4090
- **4000 frames** if running Kokoro service concurrently (needs ~6GB headroom)
- 6000+ frames spills to RAM = unusable
- Don't use gradient accumulation - single larger batch always faster
- 100k updates with Base @ 5000 frames = ~5.6 hours
- Disable `log_samples` to avoid inference stalls

**VRAM optimization tests:**
| Option | VRAM | Speed | Verdict |
|--------|------|-------|---------|
| Baseline | 16.8 GB | 5-6 updates/s | Default |
| Gradient checkpointing | 13.1 GB | 3.5-4.5 updates/s | **Best for larger models** |
| 8-bit optimizer | 18.1 GB | 5-6 updates/s | Don't use (increases VRAM) |

Gradient checkpointing (`checkpoint_activations: True`) saves 3.7 GB (22%) at 25% speed cost.

### Commands

```bash
# Activate venv
cd /home/echo/projects/kokoro/training/F5-TTS
source venv/bin/activate

# Run Base training (RECOMMENDED for production)
accelerate launch src/f5_tts/train/train.py --config-name F5TTS_Base_SmokeTest.yaml

# Run Small training (faster iteration)
accelerate launch src/f5_tts/train/train.py --config-name F5TTS_Small_SmokeTest.yaml

# Prepare dataset from CSV
python src/f5_tts/train/datasets/prepare_csv_wavs.py /path/to/metadata.csv /output/dir
```

### Configs
- Base smoke test: `src/f5_tts/configs/F5TTS_Base_SmokeTest.yaml` (currently 5000 frames - optimal)
- Small smoke test: `src/f5_tts/configs/F5TTS_Small_SmokeTest.yaml` (6000 frames)
- Original Small: `src/f5_tts/configs/F5TTS_Small.yaml`
- Original Base: `src/f5_tts/configs/F5TTS_v1_Base.yaml`
- **LR Sweep configs** (2026-02-06):
  - `src/f5_tts/configs/F5TTS_Base_LR_5e6.yaml` — LR 5e-6
  - `src/f5_tts/configs/F5TTS_Base_LR_1e5.yaml` — LR 1e-5
  - `src/f5_tts/configs/F5TTS_Base_LR_5e5.yaml` — LR 5e-5
  - Runner: `run_lr_sweep.sh`
  - Checkpoints: `ckpts/lr_sweep_5e6/`, `ckpts/lr_sweep_1e5/`, `ckpts/lr_sweep_5e5/`
</f5tts_setup>

<runpod_training>
## RunPod Parallel Training Pipeline (Feb 2026)

**Location**: `/home/echo/projects/kokoro/runpod/`
**Purpose**: Run parallel HPO sweeps on cloud GPUs (20+ experiments simultaneously)
**Platform**: RunPod (shared Network Volumes across pods in same datacenter)

### Architecture
- **Network Volume**: Upload dataset + pretrained weights ONCE, all pods mount it
- **Docker Image**: `f5tts-train:test` (PyTorch 2.4 + CUDA 12.4 + F5-TTS @ 655fbca)
- **Sweep Launcher**: `sweep.py` CLI tool using RunPod Python SDK
- **Entrypoint**: Reads env vars → symlinks volume → copies pretrained → runs training

### Files
| File | Purpose |
|------|---------|
| `runpod/Dockerfile` | Training image (17GB, based on pytorch:2.4.0-cuda12.4) |
| `runpod/entrypoint.sh` | Pod startup: symlinks, weight check, training execution |
| `runpod/sweep.py` | CLI: launch/monitor/cleanup/results/status |
| `runpod/prepare_volume.py` | One-time volume data setup |
| `runpod/F5TTS_RunPod_Base.yaml` | Base config with correct architecture (baked into image) |
| `runpod/configs/*.yaml` | Sweep configs (lr_sweep, example_sweep) |

### Usage
```bash
# Launch sweep
python runpod/sweep.py launch --config runpod/configs/lr_sweep.yaml

# Monitor
python runpod/sweep.py monitor --manifest sweep_20260207_123456.json

# Quick status
python runpod/sweep.py status

# Cleanup
python runpod/sweep.py cleanup --manifest sweep_20260207_123456.json
```

### Key Details
- F5-TTS installed at `/app/F5-TTS/` in image (NOT `/workspace/` which is volume mount)
- Symlinks: `/app/F5-TTS/data/` → `/workspace/data/`, ckpts similarly
- Pretrained weights COPIED (not symlinked) to checkpoint dir
- Config via Hydra CLI overrides from env vars
- `F5TTS_RunPod_Base.yaml` has correct `text_mask_padding: false`, `pe_attn_head: 1`
- raw.arrow needs re-preparation with `/app/F5-TTS/data/...` paths

### Pricing (RTX 3090, community)
- $0.22/hr per pod
- 20 parallel 5-min runs ≈ $0.37 total
- Network Volume: ~$0.07/GB/month

### Prerequisites (NOT YET DONE)
- [ ] Create RunPod account + add credits
- [ ] Push Docker image to Docker Hub
- [ ] Create Network Volume + upload data
- [ ] Set RunPod API key in `runpod/.runpod_key`

### Three-Phase Cloud Strategy
| Phase | Platform | Purpose |
|-------|----------|---------|
| **HPO/Testing** | RunPod (Network Volumes) | Parallel short runs, shared data |
| **Production training** | SaladCloud/Vast.ai | Long single run, cheapest $/hr |
| **Serving/inference** | SaladCloud | $0.18/hr RTX 4090, $5 credits available |
</runpod_training>

<f5tts_critical_lessons>
## F5-TTS Training - CRITICAL LESSONS LEARNED

**DO NOT REPEAT THESE MISTAKES:**

### 1. ALWAYS Copy Pretrained Weights First (Feb 2026)
**What I did wrong:** Created new checkpoint directory for Kokoro training but forgot to copy `pretrained_model.safetensors` into it. Training started from random weights instead of pretrained.

**Result:** Complete garbage output - model couldn't produce coherent speech even after 7000 updates. Loss was ~7-12 instead of ~0.5-0.9.

**MANDATORY CHECKLIST before training:**
```bash
# BEFORE running accelerate launch:
ls ckpts/YOUR_NEW_CHECKPOINT_DIR/pretrained_model.safetensors
# If it doesn't exist:
cp ckpts/EXISTING_TRAINED_DIR/pretrained_model.safetensors ckpts/YOUR_NEW_CHECKPOINT_DIR/
```

**How to tell if you fucked up:**
- Loss starts at ~7-12 instead of ~0.5-0.9
- If loss is >2 on first update, STOP IMMEDIATELY - you forgot pretrained weights

### 2. Architecture Must Match Pretrained Weights
**What I did wrong earlier:** Used wrong architecture settings (`text_mask_padding=True`, `pe_attn_head=4`) that didn't match pretrained weights (`text_mask_padding=False`, `pe_attn_head=1`).

**Result:** Shape mismatch errors or silent quality degradation.

**ALWAYS use for F5TTS_Base pretrained:**
```yaml
arch:
  text_mask_padding: False  # CRITICAL - must be False
  pe_attn_head: 1           # CRITICAL - must be 1
```

### 3. OOM with Long Samples
- Samples >15s can cause OOM even with batch_size that works for shorter clips
- Filter dataset to max 15s OR use gradient checkpointing
- If training crashes mid-epoch, reduce batch size OR filter long samples

### 4. Checkpoint Path Quirks
- Hydra changes working directory during training
- Use RELATIVE paths for `save_dir`, not absolute
- Absolute paths create nested garbage: `/F5-TTS/home/echo/.../ckpts/...`

### 5. Dataset Naming — Avoid Double-Tokenizer Suffix (Feb 2026)
**What I did wrong:** Named dataset `kokoro_libri_pinyin` with tokenizer `pinyin`.

**Result:** `get_tokenizer()` appends `_{tokenizer}` to dataset name, creating `kokoro_libri_pinyin_pinyin/vocab.txt` which doesn't exist.

**Fix:** Use `kokoro_libri` (not `kokoro_libri_pinyin`) when tokenizer is already `pinyin`:
```yaml
datasets:
  name: kokoro_libri      # CORRECT - becomes kokoro_libri_pinyin/
  # name: kokoro_libri_pinyin  # WRONG - becomes kokoro_libri_pinyin_pinyin/

model:
  tokenizer: pinyin       # This gets appended to dataset name
```

**Pattern:** Dataset folder = `{datasets.name}_{model.tokenizer}/`

### 6. Disk Space Awareness (Feb 2026)
**What happened:** LR sweep 5e-5 training crashed at 500 steps because disk hit 0 bytes free. Each checkpoint is ~5GB, so 3 checkpoints per run × 3 runs = 45GB+ in new files.

**Prevention:**
- Check `df -h /` before training runs
- Target: Keep 50GB+ free for training headroom
- Archive old checkpoints to NAS (`/mnt/p/`) immediately after experiments complete
- Delete intermediate checkpoints (keep only model_last.pt and best checkpoint)
</f5tts_critical_lessons>

<f5tts_model_comparison>
## F5-TTS Model Comparison (Feb 2026)

### Small-Scale Test (4 speakers × 1 text, 24 files)
**Files**: `sttdata/f5_comparison/` (24 wav + txt pairs)
**Scoring**: Composite MOS (4 judges), UTMOSv2, NISQA, SCOREQ, Parakeet WER
**CAVEAT**: Small sample size (4 files per model) — results NOT reliable. See expanded eval below.

| Rank | Model | Training | Composite | UTMOSv2 | NISQA | SCOREQ | WER% |
|------|-------|----------|-----------|---------|-------|--------|------|
| 1 | libri_filtered 7k | LibriTTS-R filtered 5486 samples, 7k steps, LR 1e-6 | 4.174 | 3.589 | 4.293 | 4.639 | 0.0 |
| 2 | kokoro_synthetic 21k | Kokoro af_heart 1.25x, 21k steps, LR 1e-6 | 4.016 | 3.570 | 4.107 | 4.731 | 0.0 |
| 3 | base_pretrained | Original F5TTS_Base weights (no fine-tuning) | 3.738 | 3.443 | 3.620 | 4.206 | 2.63 |

### Expanded Eval (100 prompts, 10 categories, 5 models)
**Date**: 2026-02-06
**Files**: `sttdata/eval_set/` (100 prompts × 5 models = 500 wav files)
**Scoring**: NISQA + SCOREQ only (DNSMOS fails on 91-97% of F5 audio due to clipping >[-1,1])
**Categories**: numbers, decimals, dates, currency, negations, quotes, lists, abbreviations, homographs, long prosody
**Reference audio**: F5-TTS default (basic_ref_en.wav), Kokoro production uses af_heart voice

| Rank | Model | Training Data | Fair Composite | NISQA tts | SCOREQ syn | N |
|------|-------|--------------|----------------|-----------|------------|---|
| 1 | **kokoro_production** | Kokoro v0.2.4 built-in | **4.583** | 4.261 | **4.904** | 100 |
| 2 | kokoro_17k | Kokoro synthetic, 17k steps, LR 1e-6 | 4.433 | **4.291** | 4.575 | 100 |
| 3 | kokoro_21k | Kokoro synthetic, 21k steps, LR 1e-6 | 4.417 | 4.290 | 4.544 | 100 |
| 4 | base_pretrained | F5TTS_Base original weights | 4.404 | 4.263 | 4.545 | 100 |
| 5 | libri_7k | LibriTTS-R filtered, 7k steps, LR 1e-6 | 4.399 | 4.282 | 4.517 | 100 |

### Key Insights (Corrected with 100-prompt eval)
1. **"7k beats 21k" was a statistical artifact** — with 100 prompts, 21k beats libri_7k by 0.018
2. **Kokoro production dominates** all F5-TTS models (+0.15-0.18 fair composite)
3. **Fine-tuning helps marginally** — kokoro_17k beats pretrained by 0.029
4. **More training doesn't help much** — 21k is slightly worse than 17k (-0.016)
5. **SCOREQ gap is huge** — Kokoro 4.904 vs F5 ~4.5 (synthetic speech quality detector strongly favors Kokoro)
6. **F5-TTS clips audio** — 91-97% of files have peak amplitude >1.0, breaking DNSMOS
7. **LR 1e-6 too conservative** — fine-tuning improvements are minimal, need higher LR to see real differences

### F5-TTS Audio Clipping Issue
- F5-TTS generates audio with peak amplitude >1.0 (outside [-1,1] range)
- Causes DNSMOS "np.ndarray values must be between -1 and 1" errors on 91-97% of files
- Kokoro production: 0% DNSMOS errors (properly normalized)
- Workaround: Use NISQA + SCOREQ only for fair comparison
- Fix: Post-process F5 audio with amplitude normalization before scoring

### Next Experiments (prioritized)
1. **LR sweep**: 5e-6, 1e-5, 5e-5 for 2-3k steps each — current 1e-6 barely moves the needle
2. Fix F5 audio clipping (normalize to [-1,1]) for proper 3-judge comparison
3. Mixed dataset: Kokoro + LibriTTS at various ratios
4. Gemini 2.5 targeted data generation for hard cases
</f5tts_model_comparison>

<homograph_validation>
## Homograph Phoneme Validation System (Feb 2026)

**Owner**: STT agent (port 11401, parakeet_confidence container)
**Status**: Phase 1 DEPLOYED, allowlist mode

### What It Solves
Text-based STT (Parakeet/Qwen) is blind to homograph pronunciation errors — words spelled the same but pronounced differently. Example: "lives" noun /laɪvz/ vs verb /lɪvz/ both transcribe as "lives" → 0% WER → invisible error. ~162 common English homographs affected.

### Architecture (3 components)
1. **Expected pronunciation**: NLTK POS + TF-IDF classifiers determine correct pronunciation from sentence context (162 homographs, trained on Google WikipediaHomographData + Meta Llama HD)
2. **Actual pronunciation**: facebook/wav2vec2-lv-60-espeak-cv-ft (~1.2GB VRAM) recognizes IPA phonemes from audio. Word segments extracted using Qwen3-ForcedAligner-0.6B timestamps.
3. **Comparison**: panphon articulatory feature-weighted edit distance. Subsequence matching with center-bias penalty.

### Decision Rule (dual-gate + margin)
- delta = d_alt - d_expected (positive = audio closer to expected)
- q_audio < 0.3 → homograph_unscorable
- p_expected < 0.65 → homograph_context_ambiguous
- word not in ALLOWLIST → homograph_context_ambiguous
- d_exp <= 0.30 AND delta >= 0.08 → homograph_correct
- delta <= -0.08 → pronunciation_suspect
- d_exp >= 0.60 → pronunciation_suspect
- else → homograph_context_ambiguous

### Current Allowlist (drift-tested, 375 files: 5 voices × 3 speeds × 5 sentences)
**Active**: live (100%), lives (98.7%), conduct (100%) — all voices, all speeds
**Active w/ exclusion**: wind (88%) — all voices EXCEPT am_fenrir (66.7%, denylisted)
**Removed**: lead (68% — wav2vec2 non-English phoneme output on short segments)
**Pending**: entrance, present (need more verification)
**Blocked on IPA fix**: bass (confirmed REAL TTS error), minute, tear
**Unsolvable**: close (s/z only), **Stress-only**: upset, insult, subject, moderate, learned

### Negative Controls
Location: `sttdata/f5_comparison/negative_controls/` (30 files, 15 homographs × correct/wrong)

### Phase 1.5 Follow-up
1. IPA mapping normalization (wav2vec2 ↔ pronunciation dictionary)
2. Lead sense-label inversion diagnostic
3. Drift testing: 5 samples × 3 speeds per allowlisted word
4. Discriminative-phone subscore for minimal pairs
5. Stress-aware features for stress-only words
6. Incremental allowlist expansion (criteria: precision ≥ 0.8, recall ≥ 0.8, ambiguous ≤ 0.25)
</homograph_validation>


