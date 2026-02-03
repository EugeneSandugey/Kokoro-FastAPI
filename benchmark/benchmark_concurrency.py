#!/usr/bin/env python3
"""Kokoro TTS Concurrency Benchmark - Find the concurrency sweet spot."""

import requests
import time
import subprocess
import os
import threading
import concurrent.futures
from pathlib import Path

KOKORO_URL = "http://localhost:8880/v1/audio/speech"
VOICE = "af_heart"
SPEED = 1.25
OUTPUT_DIR = Path(__file__).parent / "output"
TEXT_FILE = Path(__file__).parent / "benchmark_text.txt"

def get_gpu_stats():
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        parts = result.stdout.strip().split(", ")
        return {"gpu_pct": int(parts[0]), "mem_mb": int(parts[1]), "mem_total": int(parts[2])}
    except:
        return {"gpu_pct": -1, "mem_mb": -1, "mem_total": -1}

def get_audio_duration(filepath):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(filepath)],
            capture_output=True, text=True, timeout=10
        )
        return float(result.stdout.strip())
    except:
        return 0.0

def generate_tts(text, output_path, label=""):
    payload = {"input": text, "voice": VOICE, "speed": SPEED, "response_format": "mp3"}
    start = time.time()
    try:
        resp = requests.post(KOKORO_URL, json=payload, timeout=300)
        elapsed = time.time() - start
        if resp.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(resp.content)
            duration = get_audio_duration(output_path)
            return {"label": label, "success": True, "gen_time": elapsed, "audio_dur": duration}
        else:
            return {"label": label, "success": False, "gen_time": elapsed, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"label": label, "success": False, "gen_time": time.time() - start, "error": str(e)}

def run_concurrent_batch(text, concurrency, batch_label=""):
    """Run `concurrency` requests simultaneously, return results + GPU samples."""
    gpu_samples = []
    stop_sampling = False

    def sampler():
        while not stop_sampling:
            gpu_samples.append(get_gpu_stats())
            time.sleep(0.25)

    t = threading.Thread(target=sampler, daemon=True)
    t.start()

    start = time.time()
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for i in range(concurrency):
            outpath = OUTPUT_DIR / f"{batch_label}_{i:02d}.mp3"
            futures.append(executor.submit(generate_tts, text, outpath, f"{batch_label}_{i}"))
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    wall_time = time.time() - start
    stop_sampling = True
    t.join(timeout=2)

    return results, wall_time, gpu_samples

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    text = TEXT_FILE.read_text().strip()
    word_count = len(text.split())

    print(f"Text: {word_count} words, {len(text)} chars")
    print(f"Kokoro API: ", end="")
    try:
        requests.get("http://localhost:8880/v1/models", timeout=5)
        print("OK")
    except:
        print("FAILED - exiting")
        return

    baseline_gpu = get_gpu_stats()
    print(f"Baseline GPU: {baseline_gpu['gpu_pct']}% util, {baseline_gpu['mem_mb']}MB VRAM\n")

    # Warmup
    print("Warmup run...", end="", flush=True)
    warmup = generate_tts(text, OUTPUT_DIR / "warmup.mp3", "warmup")
    if warmup["success"]:
        print(f" {warmup['gen_time']:.2f}s, audio={warmup['audio_dur']:.1f}s")
        audio_dur_per_req = warmup["audio_dur"]
    else:
        print(f" FAILED: {warmup.get('error')}")
        return

    # Test concurrency levels: 1, 2, 3, 4, 5, 8, 10
    concurrency_levels = [1, 2, 3, 4, 5, 8, 10]
    all_results = {}

    for c in concurrency_levels:
        print(f"\n{'='*60}")
        print(f"CONCURRENCY = {c}")
        print(f"{'='*60}")

        # Small pause between tests to let GPU cool
        time.sleep(2)

        results, wall_time, gpu_samples = run_concurrent_batch(text, c, f"c{c}")

        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        gpu_utils = [s["gpu_pct"] for s in gpu_samples if s["gpu_pct"] >= 0]
        avg_gpu = sum(gpu_utils) / len(gpu_utils) if gpu_utils else 0
        peak_gpu = max(gpu_utils) if gpu_utils else 0

        total_audio = sum(r["audio_dur"] for r in successful)
        avg_gen = sum(r["gen_time"] for r in successful) / len(successful) if successful else 0

        print(f"  Success: {len(successful)}/{c}")
        print(f"  Failed:  {len(failed)}/{c}")
        if failed:
            for f in failed:
                print(f"    {f['label']}: {f.get('error', '?')}")

        if successful:
            gen_times = [r["gen_time"] for r in successful]
            print(f"  Wall time:      {wall_time:.2f}s")
            print(f"  Avg gen/req:    {avg_gen:.2f}s")
            print(f"  Min/Max gen:    {min(gen_times):.2f}s / {max(gen_times):.2f}s")
            print(f"  Total audio:    {total_audio:.1f}s ({total_audio/60:.1f} min)")
            print(f"  Throughput:     {total_audio/wall_time:.1f}x realtime")
            print(f"  GPU avg/peak:   {avg_gpu:.0f}% / {peak_gpu}%")

        all_results[c] = {
            "concurrency": c,
            "wall_time": wall_time,
            "success_count": len(successful),
            "fail_count": len(failed),
            "total_audio": total_audio,
            "throughput_x": total_audio / wall_time if wall_time > 0 else 0,
            "avg_gen_time": avg_gen,
            "avg_gpu": avg_gpu,
            "peak_gpu": peak_gpu,
        }

    # Final summary table
    print(f"\n\n{'='*80}")
    print("CONCURRENCY COMPARISON TABLE")
    print(f"{'='*80}")
    print(f"{'Conc':>5} | {'OK/Tot':>7} | {'Wall(s)':>8} | {'AvgGen(s)':>10} | {'Throughput':>10} | {'GPU avg':>8} | {'GPU pk':>7}")
    print(f"{'-'*5}-+-{'-'*7}-+-{'-'*8}-+-{'-'*10}-+-{'-'*10}-+-{'-'*8}-+-{'-'*7}")

    for c in concurrency_levels:
        r = all_results[c]
        print(f"{r['concurrency']:>5} | {r['success_count']}/{c:>2}    | {r['wall_time']:>7.1f}s | {r['avg_gen_time']:>9.2f}s | {r['throughput_x']:>8.1f}x  | {r['avg_gpu']:>6.0f}%  | {r['peak_gpu']:>5}%")

    # Capacity estimate
    best = max(all_results.values(), key=lambda x: x["throughput_x"])
    print(f"\n--- CAPACITY ESTIMATE ---")
    print(f"Best throughput: {best['throughput_x']:.1f}x realtime at concurrency={best['concurrency']}")
    print(f"Audio duration per request: ~{audio_dur_per_req:.0f}s ({audio_dur_per_req/60:.1f} min)")
    print(f"")

    # Requests per hour at best throughput
    reqs_per_hour = (3600 / best['wall_time']) * best['success_count']
    audio_per_hour_min = (3600 * best['throughput_x']) / 60
    print(f"At best concurrency ({best['concurrency']}):")
    print(f"  Requests/hour (2-min each): {reqs_per_hour:.0f}")
    print(f"  Audio minutes/hour: {audio_per_hour_min:.0f}")
    print(f"  Audio hours/hour: {audio_per_hour_min/60:.1f}")

if __name__ == "__main__":
    main()
