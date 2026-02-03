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
</recent_updates>

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
