#!/usr/bin/env python3
"""Kokoro TTS Benchmark - Sequential vs Parallel throughput testing."""

import requests
import time
import subprocess
import json
import sys
import os
import concurrent.futures
from pathlib import Path

KOKORO_URL = "http://localhost:8880/v1/audio/speech"
VOICE = "af_heart"
SPEED = 1.25
OUTPUT_DIR = Path(__file__).parent / "output"
TEXT_FILE = Path(__file__).parent / "benchmark_text.txt"

def get_gpu_stats():
    """Get current GPU utilization and memory usage."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        parts = result.stdout.strip().split(", ")
        return {
            "gpu_util_pct": int(parts[0]),
            "mem_used_mb": int(parts[1]),
            "mem_total_mb": int(parts[2]),
        }
    except Exception as e:
        return {"error": str(e)}

def get_audio_duration(filepath):
    """Get audio duration using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(filepath)],
            capture_output=True, text=True, timeout=10
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0

def generate_tts(text, output_path, run_id=""):
    """Generate TTS and return timing + metadata."""
    payload = {
        "input": text,
        "voice": VOICE,
        "speed": SPEED,
        "response_format": "mp3"
    }

    start = time.time()
    gpu_before = get_gpu_stats()

    try:
        resp = requests.post(KOKORO_URL, json=payload, timeout=300)
        elapsed = time.time() - start
        gpu_after = get_gpu_stats()

        if resp.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(resp.content)
            duration = get_audio_duration(output_path)
            file_size = os.path.getsize(output_path)

            return {
                "run_id": run_id,
                "success": True,
                "generation_time_s": round(elapsed, 3),
                "audio_duration_s": round(duration, 2),
                "realtime_factor": round(duration / elapsed, 2) if elapsed > 0 else 0,
                "file_size_bytes": file_size,
                "gpu_util_before": gpu_before.get("gpu_util_pct", "?"),
                "gpu_util_after": gpu_after.get("gpu_util_pct", "?"),
                "gpu_mem_before_mb": gpu_before.get("mem_used_mb", "?"),
                "gpu_mem_after_mb": gpu_after.get("mem_used_mb", "?"),
            }
        else:
            return {
                "run_id": run_id,
                "success": False,
                "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                "generation_time_s": round(elapsed, 3),
            }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "run_id": run_id,
            "success": False,
            "error": str(e),
            "generation_time_s": round(elapsed, 3),
        }

def monitor_gpu_during(func, interval=0.5):
    """Run func while sampling GPU stats in background."""
    gpu_samples = []
    stop = False

    import threading
    def sampler():
        while not stop:
            gpu_samples.append(get_gpu_stats())
            time.sleep(interval)

    t = threading.Thread(target=sampler, daemon=True)
    t.start()
    result = func()
    stop = True
    t.join(timeout=2)
    return result, gpu_samples

def run_sequential(text, count=10):
    """Run N generations sequentially."""
    print(f"\n{'='*60}")
    print(f"SEQUENTIAL BENCHMARK: {count} generations")
    print(f"{'='*60}")

    results = []
    total_start = time.time()

    for i in range(count):
        outpath = OUTPUT_DIR / f"seq_{i:02d}.mp3"
        print(f"  [{i+1}/{count}] Generating...", end="", flush=True)
        r = generate_tts(text, outpath, run_id=f"seq_{i}")
        results.append(r)
        if r["success"]:
            print(f" {r['generation_time_s']}s (audio: {r['audio_duration_s']}s, RTF: {r['realtime_factor']}x, GPU: {r['gpu_util_after']}%)")
        else:
            print(f" FAILED: {r.get('error', 'unknown')}")

    total_elapsed = time.time() - total_start
    return results, total_elapsed

def run_parallel(text, count=10):
    """Run N generations in parallel."""
    print(f"\n{'='*60}")
    print(f"PARALLEL BENCHMARK: {count} generations")
    print(f"{'='*60}")

    total_start = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
        futures = {}
        for i in range(count):
            outpath = OUTPUT_DIR / f"par_{i:02d}.mp3"
            f = executor.submit(generate_tts, text, outpath, f"par_{i}")
            futures[f] = i

        results = [None] * count
        for f in concurrent.futures.as_completed(futures):
            idx = futures[f]
            r = f.result()
            results[idx] = r
            if r["success"]:
                print(f"  [par_{idx}] {r['generation_time_s']}s (audio: {r['audio_duration_s']}s, RTF: {r['realtime_factor']}x)")
            else:
                print(f"  [par_{idx}] FAILED: {r.get('error', 'unknown')}")

    total_elapsed = time.time() - total_start
    return results, total_elapsed

def print_summary(label, results, total_elapsed):
    """Print summary statistics."""
    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    print(f"\n--- {label} SUMMARY ---")
    print(f"Total wall time: {total_elapsed:.2f}s")
    print(f"Successful: {len(successful)}/{len(results)}")

    if successful:
        gen_times = [r["generation_time_s"] for r in successful]
        audio_durs = [r["audio_duration_s"] for r in successful]
        rtfs = [r["realtime_factor"] for r in successful]

        total_audio = sum(audio_durs)
        avg_gen = sum(gen_times) / len(gen_times)

        print(f"Total audio generated: {total_audio:.1f}s ({total_audio/60:.1f} min)")
        print(f"Avg generation time per request: {avg_gen:.2f}s")
        print(f"Min/Max generation time: {min(gen_times):.2f}s / {max(gen_times):.2f}s")
        print(f"Avg realtime factor: {sum(rtfs)/len(rtfs):.1f}x")
        print(f"Effective throughput: {total_audio/total_elapsed:.1f}x realtime")
        print(f"Audio minutes per wall minute: {(total_audio/60)/(total_elapsed/60):.1f}")

    if failed:
        print(f"\nFailed requests:")
        for r in failed:
            print(f"  {r['run_id']}: {r.get('error', 'unknown')}")

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    text = TEXT_FILE.read_text().strip()
    word_count = len(text.split())
    print(f"Benchmark text: {word_count} words, {len(text)} characters")

    # Check Kokoro is up
    print("\nChecking Kokoro health...")
    try:
        r = requests.get("http://localhost:8880/v1/models", timeout=5)
        print(f"  Kokoro API: OK (status {r.status_code})")
    except Exception as e:
        print(f"  Kokoro API: FAILED ({e})")
        sys.exit(1)

    # Baseline GPU stats
    gpu = get_gpu_stats()
    print(f"\nBaseline GPU: {gpu['gpu_util_pct']}% util, {gpu['mem_used_mb']}MB / {gpu['mem_total_mb']}MB VRAM")

    # --- Single baseline ---
    print(f"\n{'='*60}")
    print("BASELINE: Single generation")
    print(f"{'='*60}")

    baseline_path = OUTPUT_DIR / "baseline.mp3"

    def do_baseline():
        return generate_tts(text, baseline_path, "baseline")

    baseline_result, gpu_samples = monitor_gpu_during(do_baseline, interval=0.25)

    if baseline_result["success"]:
        gpu_utils = [s.get("gpu_util_pct", 0) for s in gpu_samples if "gpu_util_pct" in s]
        peak_gpu = max(gpu_utils) if gpu_utils else "?"
        avg_gpu = sum(gpu_utils)/len(gpu_utils) if gpu_utils else "?"

        print(f"  Generation time: {baseline_result['generation_time_s']}s")
        print(f"  Audio duration: {baseline_result['audio_duration_s']}s ({baseline_result['audio_duration_s']/60:.1f} min)")
        print(f"  Realtime factor: {baseline_result['realtime_factor']}x")
        print(f"  File size: {baseline_result['file_size_bytes']/1024:.1f} KB")
        print(f"  GPU utilization during generation: avg={avg_gpu}%, peak={peak_gpu}%")
        print(f"  GPU memory: {baseline_result['gpu_mem_before_mb']}MB -> {baseline_result['gpu_mem_after_mb']}MB")
        print(f"  GPU samples collected: {len(gpu_samples)}")
    else:
        print(f"  FAILED: {baseline_result.get('error')}")
        sys.exit(1)

    # --- Sequential ---
    def do_sequential():
        return run_sequential(text, count=10)

    (seq_results, seq_total), seq_gpu_samples = monitor_gpu_during(do_sequential, interval=0.5)
    print_summary("SEQUENTIAL", seq_results, seq_total)

    if seq_gpu_samples:
        seq_gpu_utils = [s.get("gpu_util_pct", 0) for s in seq_gpu_samples if "gpu_util_pct" in s]
        if seq_gpu_utils:
            print(f"GPU during sequential: avg={sum(seq_gpu_utils)/len(seq_gpu_utils):.0f}%, peak={max(seq_gpu_utils)}%, min={min(seq_gpu_utils)}%")

    # --- Parallel ---
    def do_parallel():
        return run_parallel(text, count=10)

    (par_results, par_total), par_gpu_samples = monitor_gpu_during(do_parallel, interval=0.5)
    print_summary("PARALLEL", par_results, par_total)

    if par_gpu_samples:
        par_gpu_utils = [s.get("gpu_util_pct", 0) for s in par_gpu_samples if "gpu_util_pct" in s]
        if par_gpu_utils:
            print(f"GPU during parallel: avg={sum(par_gpu_utils)/len(par_gpu_utils):.0f}%, peak={max(par_gpu_utils)}%, min={min(par_gpu_utils)}%")

    # --- Comparison ---
    seq_successful = [r for r in seq_results if r.get("success")]
    par_successful = [r for r in par_results if r.get("success")]

    if seq_successful and par_successful:
        seq_audio_total = sum(r["audio_duration_s"] for r in seq_successful)
        par_audio_total = sum(r["audio_duration_s"] for r in par_successful)

        print(f"\n{'='*60}")
        print("COMPARISON")
        print(f"{'='*60}")
        print(f"Sequential: {seq_total:.1f}s wall time for {seq_audio_total:.1f}s audio ({seq_audio_total/seq_total:.1f}x throughput)")
        print(f"Parallel:   {par_total:.1f}s wall time for {par_audio_total:.1f}s audio ({par_audio_total/par_total:.1f}x throughput)")
        print(f"Speedup from parallelism: {seq_total/par_total:.2f}x")
        print(f"")
        print(f"If running at max tilt 24/7:")
        seq_per_hour = (3600 / seq_total) * seq_audio_total
        par_per_hour = (3600 / par_total) * par_audio_total
        print(f"  Sequential: {seq_per_hour/60:.0f} minutes of audio per hour")
        print(f"  Parallel:   {par_per_hour/60:.0f} minutes of audio per hour")
        print(f"  Sequential: {seq_per_hour/3600:.1f} hours of audio per hour")
        print(f"  Parallel:   {par_per_hour/3600:.1f} hours of audio per hour")

if __name__ == "__main__":
    main()
