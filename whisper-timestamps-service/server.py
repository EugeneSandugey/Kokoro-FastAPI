#!/usr/bin/env python3
"""Word-level Timestamps Service - GPU-accelerated forced alignment using Wav2Vec2
   + Speaker Diarization using pyannote-audio 3.1"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import tempfile
import subprocess
import os
import time
import torch
import torchaudio
import shutil

app = FastAPI(title="ForceAlign Timestamps Service", version="3.0.0")

# Suppress torchaudio deprecation warnings
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="torchaudio")

# Load ForceAlign model once at startup (Wav2Vec2 - only 0.4GB VRAM)
print("Loading Wav2Vec2 model for forced alignment...")
start = time.time()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
bundle = torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H
fa_model = bundle.get_model().to(device)
fa_labels = bundle.get_labels()
fa_dictionary = {c: i for i, c in enumerate(fa_labels)}
print(f"Wav2Vec2 model loaded in {time.time() - start:.1f}s on {device}")

# Load diarization pipeline (requires HF_TOKEN env var)
diarize_pipeline = None
HF_TOKEN = os.environ.get("HF_TOKEN")
if HF_TOKEN:
    print("Loading pyannote speaker-diarization-3.1...")
    start = time.time()
    try:
        from pyannote.audio import Pipeline
        diarize_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=HF_TOKEN
        )
        diarize_pipeline.to(torch.device("cuda"))
        print(f"Diarization pipeline loaded in {time.time() - start:.1f}s")
    except Exception as e:
        print(f"WARNING: Failed to load diarization pipeline: {e}")
        print("Diarization endpoint will be disabled")
else:
    print("WARNING: HF_TOKEN not set - diarization endpoint disabled")
    print("Set HF_TOKEN env var with your HuggingFace token to enable diarization")


class TimestampRequest(BaseModel):
    audio_path: str  # Path to audio file (must be accessible to container)
    original_text: str  # Original text for alignment


class TimestampResponse(BaseModel):
    words: list[str]
    startTimes: list[float]
    endTimes: list[float]
    latency_ms: float


@app.get("/health")
def health():
    return {
        "status": "ok",
        "alignment_model": "Wav2Vec2-BASE-960H",
        "diarization": "enabled" if diarize_pipeline else "disabled"
    }


# Diarization models
class DiarizeRequest(BaseModel):
    audio_path: str
    min_speakers: int = 1
    max_speakers: int = 10


class SpeakerSegment(BaseModel):
    speaker: str
    start: float
    end: float
    text: str
    words: list[dict] = []


class DiarizeResponse(BaseModel):
    segments: list[SpeakerSegment]
    speakers: list[str]
    duration: float
    latency_ms: float


def force_align_audio(audio_path: str, transcript: str) -> dict:
    """Perform forced alignment using Wav2Vec2 model.

    This aligns the provided transcript to the audio acoustically,
    giving accurate word-level timestamps.
    """
    # Convert to WAV if needed and copy to temp (for write access)
    temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    wav_path = temp_wav.name
    temp_wav.close()

    try:
        if audio_path.endswith('.mp3'):
            subprocess.run(
                ['ffmpeg', '-y', '-i', audio_path, '-ar', '16000', '-ac', '1', wav_path],
                capture_output=True, check=True
            )
        else:
            shutil.copy(audio_path, wav_path)

        # Load audio
        waveform, sample_rate = torchaudio.load(wav_path)
        if sample_rate != bundle.sample_rate:
            waveform = torchaudio.functional.resample(waveform, sample_rate, bundle.sample_rate)
        waveform = waveform.to(device)

        # Get emissions from model
        with torch.inference_mode():
            emissions, _ = fa_model(waveform)
            emissions = torch.log_softmax(emissions, dim=-1)

        emission = emissions[0].cpu()

        # Tokenize transcript
        words = transcript.split()
        tokens = []
        for word in words:
            word_tokens = [fa_dictionary.get(c.upper(), 0) for c in word if c.upper() in fa_dictionary]
            tokens.extend(word_tokens)

        if not tokens:
            raise ValueError("No valid tokens found in transcript")

        # Build trellis for alignment
        trellis = get_trellis(emission, tokens)

        # Backtrack to find alignment path
        path = backtrack(trellis, emission, tokens)

        # Get word segments
        segments = merge_repeats(path)
        word_segments = merge_words(segments, words)

        # Convert frame indices to time
        ratio = waveform.size(1) / emission.size(0) / bundle.sample_rate

        result_words = []
        start_times = []
        end_times = []

        for word, seg in zip(words, word_segments):
            result_words.append(word)
            start_times.append(seg.start * ratio)
            end_times.append(seg.end * ratio)

        # Fix zero-duration words (numbers, symbols that Wav2Vec2 can't match)
        # When Wav2Vec2 can't match a word, it gets zero duration and subsequent
        # words get pushed to the same timestamp. We need to:
        # 1. Estimate duration for unmatchable words (based on char count)
        # 2. Shift all subsequent words forward to make room

        i = 0
        while i < len(result_words):
            duration = end_times[i] - start_times[i]
            if duration < 0.05:  # Less than 50ms = probably failed to align
                # Find the start of this gap (previous word's end time)
                prev_end = end_times[i - 1] if i > 0 else 0

                # Find all consecutive zero-duration words
                gap_start = i
                gap_end = i
                while gap_end < len(result_words) and (end_times[gap_end] - start_times[gap_end]) < 0.05:
                    gap_end += 1

                # Estimate duration for these words (roughly 0.15s per word for numbers/short words)
                num_zero_words = gap_end - gap_start
                estimated_duration = 0.2 * num_zero_words  # 200ms per word

                # Assign timestamps to the zero-duration words
                word_dur = estimated_duration / num_zero_words
                for j in range(gap_start, gap_end):
                    idx = j - gap_start
                    start_times[j] = prev_end + (idx * word_dur)
                    end_times[j] = prev_end + ((idx + 1) * word_dur)

                # Shift all subsequent words forward by the estimated duration
                # (minus any existing gap that was already there)
                existing_gap = 0
                if gap_end < len(result_words):
                    existing_gap = start_times[gap_end] - prev_end

                shift_amount = estimated_duration - existing_gap
                if shift_amount > 0:
                    for j in range(gap_end, len(result_words)):
                        start_times[j] += shift_amount
                        end_times[j] += shift_amount

                # Skip to end of gap
                i = gap_end
            else:
                i += 1

        return {
            'words': result_words,
            'startTimes': start_times,
            'endTimes': end_times
        }

    finally:
        try:
            os.remove(wav_path)
        except:
            pass


def get_trellis(emission, tokens, blank_id=0):
    """Build trellis matrix for CTC alignment."""
    num_frames = emission.size(0)
    num_tokens = len(tokens)

    trellis = torch.full((num_frames + 1, num_tokens + 1), -float('inf'))
    trellis[0, 0] = 0

    for t in range(num_frames):
        trellis[t + 1, 0] = trellis[t, 0] + emission[t, blank_id]
        for j in range(num_tokens):
            # Stay in same token or move to next
            trellis[t + 1, j + 1] = max(
                trellis[t, j + 1] + emission[t, blank_id],
                trellis[t, j] + emission[t, tokens[j]]
            )

    return trellis


def backtrack(trellis, emission, tokens, blank_id=0):
    """Backtrack through trellis to find optimal alignment path."""
    t, j = trellis.size(0) - 1, trellis.size(1) - 1
    path = []

    while j > 0:
        stayed = trellis[t - 1, j] + emission[t - 1, blank_id]
        changed = trellis[t - 1, j - 1] + emission[t - 1, tokens[j - 1]]

        path.append((t - 1, j - 1, tokens[j - 1]))

        if changed > stayed:
            j -= 1
        t -= 1

    while t > 0:
        path.append((t - 1, 0, blank_id))
        t -= 1

    path.reverse()
    return path


class Segment:
    def __init__(self, label, start, end):
        self.label = label
        self.start = start
        self.end = end


def merge_repeats(path):
    """Merge repeated tokens into segments."""
    segments = []
    i = 0
    while i < len(path):
        t, j, token = path[i]
        if token == 0:  # blank
            i += 1
            continue

        start = t
        while i < len(path) and path[i][2] == token:
            i += 1
        end = path[i - 1][0] + 1

        segments.append(Segment(token, start, end))

    return segments


def merge_words(segments, words):
    """Merge token segments into word segments."""
    word_segments = []
    seg_idx = 0

    for word in words:
        word_len = len([c for c in word if c.upper() in fa_dictionary])
        if word_len == 0:
            # Word has no valid characters, use previous end or 0
            if word_segments:
                word_segments.append(Segment(word, word_segments[-1].end, word_segments[-1].end))
            else:
                word_segments.append(Segment(word, 0, 0))
            continue

        if seg_idx >= len(segments):
            # Ran out of segments, extrapolate
            if word_segments:
                word_segments.append(Segment(word, word_segments[-1].end, word_segments[-1].end + 10))
            else:
                word_segments.append(Segment(word, 0, 10))
            continue

        start = segments[seg_idx].start
        end_idx = min(seg_idx + word_len - 1, len(segments) - 1)
        end = segments[end_idx].end

        word_segments.append(Segment(word, start, end))
        seg_idx += word_len

    return word_segments


@app.post("/timestamps", response_model=TimestampResponse)
def get_timestamps(req: TimestampRequest):
    """Get word-level timestamps using forced alignment."""
    start_time = time.perf_counter()

    if not os.path.exists(req.audio_path):
        raise HTTPException(status_code=404, detail=f"Audio file not found: {req.audio_path}")

    try:
        result = force_align_audio(req.audio_path, req.original_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alignment failed: {str(e)}")

    latency = (time.perf_counter() - start_time) * 1000

    return TimestampResponse(
        words=result['words'],
        startTimes=result['startTimes'],
        endTimes=result['endTimes'],
        latency_ms=round(latency, 1)
    )


@app.post("/diarize", response_model=DiarizeResponse)
def diarize_audio(req: DiarizeRequest):
    """Transcribe audio with speaker diarization - identifies who said what"""
    if not diarize_pipeline:
        raise HTTPException(
            status_code=503,
            detail="Diarization not available. Set HF_TOKEN env var and accept model agreements at huggingface.co"
        )

    start_time = time.perf_counter()

    if not os.path.exists(req.audio_path):
        raise HTTPException(status_code=404, detail=f"Audio file not found: {req.audio_path}")

    # Convert to WAV if needed
    wav_path = req.audio_path
    temp_wav = None

    if not req.audio_path.endswith('.wav'):
        temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        wav_path = temp_wav.name
        temp_wav.close()
        subprocess.run(
            ['ffmpeg', '-y', '-i', req.audio_path, '-ar', '16000', '-ac', '1', wav_path],
            capture_output=True
        )

    # We need whisper for transcription in diarization
    # Load it on-demand since it's not always needed
    from faster_whisper import WhisperModel
    whisper_model = WhisperModel("distil-large-v3", device="cuda", compute_type="float16")

    # Step 1: Transcribe with whisper (word timestamps)
    segments_raw, info = whisper_model.transcribe(wav_path, word_timestamps=True, language="en")

    # Collect all segments and words
    whisper_segments = []
    for seg in segments_raw:
        words = []
        if seg.words:
            for w in seg.words:
                words.append({
                    'word': w.word.strip(),
                    'start': float(w.start),
                    'end': float(w.end)
                })
        whisper_segments.append({
            'start': float(seg.start),
            'end': float(seg.end),
            'text': seg.text.strip(),
            'words': words
        })

    # Step 2: Run speaker diarization
    diarization = diarize_pipeline(
        wav_path,
        min_speakers=req.min_speakers,
        max_speakers=req.max_speakers
    )

    # Step 3: Assign speakers to whisper segments
    speaker_timeline = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        speaker_timeline.append({
            'start': turn.start,
            'end': turn.end,
            'speaker': speaker
        })

    # Assign speakers to segments based on overlap
    result_segments = []
    speakers_seen = set()

    for seg in whisper_segments:
        seg_mid = (seg['start'] + seg['end']) / 2

        speaker = "UNKNOWN"
        for sp in speaker_timeline:
            if sp['start'] <= seg_mid <= sp['end']:
                speaker = sp['speaker']
                break

        speakers_seen.add(speaker)
        result_segments.append(SpeakerSegment(
            speaker=speaker,
            start=seg['start'],
            end=seg['end'],
            text=seg['text'],
            words=seg['words']
        ))

    # Clean up temp wav
    if temp_wav:
        try:
            os.remove(wav_path)
        except:
            pass

    latency = (time.perf_counter() - start_time) * 1000

    return DiarizeResponse(
        segments=result_segments,
        speakers=sorted(list(speakers_seen)),
        duration=info.duration if hasattr(info, 'duration') else 0,
        latency_ms=round(latency, 1)
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8881)
