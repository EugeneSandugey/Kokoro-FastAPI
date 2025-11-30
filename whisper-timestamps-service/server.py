#!/usr/bin/env python3
"""Whisper Timestamps Service - GPU-accelerated word-level timestamps using distil-large-v3"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import tempfile
import subprocess
import os
import time

app = FastAPI(title="Whisper Timestamps Service", version="1.0.0")

# Load model once at startup
print("Loading distil-large-v3 model...")
start = time.time()
from faster_whisper import WhisperModel
model = WhisperModel("distil-large-v3", device="cuda", compute_type="float16")
print(f"Model loaded in {time.time() - start:.1f}s")


class TimestampRequest(BaseModel):
    audio_path: str  # Path to audio file (must be accessible to container)
    original_text: str  # Original text for fuzzy matching


class TimestampResponse(BaseModel):
    words: list[str]
    startTimes: list[float]
    endTimes: list[float]
    latency_ms: float


@app.get("/health")
def health():
    return {"status": "ok", "model": "distil-large-v3"}


@app.post("/timestamps", response_model=TimestampResponse)
def get_timestamps(req: TimestampRequest):
    start_time = time.perf_counter()

    if not os.path.exists(req.audio_path):
        raise HTTPException(status_code=404, detail=f"Audio file not found: {req.audio_path}")

    # Convert to WAV if needed
    wav_path = req.audio_path
    temp_wav = None

    if req.audio_path.endswith('.mp3'):
        temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        wav_path = temp_wav.name
        temp_wav.close()
        subprocess.run(
            ['ffmpeg', '-y', '-i', req.audio_path, '-ar', '16000', '-ac', '1', wav_path],
            capture_output=True
        )

    # Transcribe with word timestamps
    segments, _ = model.transcribe(wav_path, word_timestamps=True, language="en")

    # Collect distil words
    distil_words = []
    for seg in segments:
        if seg.words:
            for w in seg.words:
                distil_words.append({
                    'word': w.word.strip(),
                    'start': float(w.start),
                    'end': float(w.end)
                })

    # Clean up temp wav
    if temp_wav:
        try:
            os.remove(wav_path)
        except:
            pass

    if not distil_words:
        raise HTTPException(status_code=500, detail="No words detected in audio")

    # Fuzzy match to original text
    original_words = req.original_text.split()
    aligned_words = []
    aligned_starts = []
    aligned_ends = []
    distil_idx = 0

    for orig_word in original_words:
        orig_clean = orig_word.lower().strip('.,!?;:\'"()-$')

        if distil_idx >= len(distil_words):
            if aligned_ends:
                aligned_words.append(orig_word)
                aligned_starts.append(aligned_ends[-1])
                aligned_ends.append(aligned_ends[-1] + 0.2)
            continue

        distil_clean = distil_words[distil_idx]['word'].lower().strip('.,!?;:\'"()-$').lstrip('-')

        # Exact match or spelling variation
        if orig_clean == distil_clean or orig_clean.rstrip('l') == distil_clean.rstrip('l'):
            aligned_words.append(orig_word)
            aligned_starts.append(distil_words[distil_idx]['start'])
            aligned_ends.append(distil_words[distil_idx]['end'])
            distil_idx += 1
            continue

        # Try combining fragmented words
        combined = distil_clean
        start_t = distil_words[distil_idx]['start']
        end_t = distil_words[distil_idx]['end']
        consumed = 1
        found_match = False

        while distil_idx + consumed < len(distil_words) and len(combined) < len(orig_clean) + 5:
            next_word = distil_words[distil_idx + consumed]['word'].lower().strip('.,!?;:\'"()-$').lstrip('-')
            combined += next_word
            end_t = distil_words[distil_idx + consumed]['end']
            consumed += 1

            if combined == orig_clean or orig_clean in combined or combined in orig_clean:
                found_match = True
                break

        if found_match:
            aligned_words.append(orig_word)
            aligned_starts.append(start_t)
            aligned_ends.append(end_t)
            distil_idx += consumed
        else:
            aligned_words.append(orig_word)
            aligned_starts.append(distil_words[distil_idx]['start'])
            aligned_ends.append(distil_words[distil_idx]['end'])
            distil_idx += 1

    latency = (time.perf_counter() - start_time) * 1000

    return TimestampResponse(
        words=aligned_words,
        startTimes=aligned_starts,
        endTimes=aligned_ends,
        latency_ms=round(latency, 1)
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8881)
