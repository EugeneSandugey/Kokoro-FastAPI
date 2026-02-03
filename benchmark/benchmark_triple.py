#!/usr/bin/env python3
"""Benchmark 1, 2, 3, and 4 Kokoro instances to find the scaling curve."""

import requests
import time
import subprocess
import os
import threading
import concurrent.futures
from pathlib import Path

INSTANCES = {
    1: ["http://localhost:8880/v1/audio/speech"],
    2: ["http://localhost:8880/v1/audio/speech", "http://localhost:8882/v1/audio/speech"],
    3: ["http://localhost:8880/v1/audio/speech", "http://localhost:8882/v1/audio/speech",
        "http://localhost:8883/v1/audio/speech"],
}
VOICE = "af_heart"
SPEED = 1.25
OUTPUT_DIR = Path(__file__).parent / "output"
TEXT_FILE = Path(__file__).parent / "benchmark_text.txt"
REQS_PER_INSTANCE = 5

def get_gpu_stats():
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        parts = result.stdout.strip().split(", ")
        return {"gpu_pct": int(parts[0]), "mem_mb": int(parts[1])}
    except:
        return {"gpu_pct": -1, "mem_mb": -1}

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

def generate_tts(url, text, output_path, label=""):
    payload = {"input": text, "voice": VOICE, "speed": SPEED, "response_format": "mp3"}
    start = time.time()
    try:
        resp = requests.post(url, json=payload, timeout=300)
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

def run_sequential_on_instance(url, text, instance_name, count, output_dir):
    results = []
    for i in range(count):
        r = generate_tts(url, text, output_dir / f"{instance_name}_{i}.mp3", f"{instance_name}_req{i}")
        results.append(r)
    return results

def benchmark_n_instances(n, text, reqs_per_instance):
    urls = INSTANCES[n]
    print(f"\n{'='*60}")
    print(f"{n} INSTANCE(S), {reqs_per_instance} req each = {n * reqs_per_instance} total requests")
    print(f"{'='*60}")

    # GPU sampling
    gpu_samples = []
    stop = threading.Event()
    def sampler():
        while not stop.is_set():
            gpu_samples.append(get_gpu_stats())
            time.sleep(0.25)
    t = threading.Thread(target=sampler, daemon=True)
    t.start()

    start = time.time()
    all_results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as executor:
        futures = []
        for i, url in enumerate(urls):
            futures.append(executor.submit(
                run_sequential_on_instance, url, text, f"inst{i+1}", reqs_per_instance, OUTPUT_DIR
            ))
        for f in concurrent.futures.as_completed(futures):
            all_results.extend(f.result())

    wall_time = time.time() - start
    stop.set()
    t.join(timeout=2)

    successful = [r for r in all_results if r["success"]]
    failed = [r for r in all_results if not r["success"]]
    gpu_utils = [s["gpu_pct"] for s in gpu_samples if s["gpu_pct"] >= 0]
    gpu_mems = [s["mem_mb"] for s in gpu_samples if s["mem_mb"] >= 0]

    total_audio = sum(r["audio_dur"] for r in successful)
    gen_times = [r["gen_time"] for r in successful]

    print(f"  Success: {len(successful)}/{n * reqs_per_instance}")
    if failed:
        for f in failed:
            print(f"    FAILED: {f['label']} - {f.get('error','?')}")
    print(f"  Wall time: {wall_time:.2f}s")
    if successful:
        print(f"  Total audio: {total_audio:.1f}s ({total_audio/60:.1f} min)")
        print(f"  Throughput: {total_audio/wall_time:.1f}x realtime")
        print(f"  Avg gen/req: {sum(gen_times)/len(gen_times):.2f}s")
        print(f"  Min/Max gen: {min(gen_times):.2f}s / {max(gen_times):.2f}s")
    if gpu_utils:
        print(f"  GPU: avg={sum(gpu_utils)/len(gpu_utils):.0f}%, peak={max(gpu_utils)}%")
    if gpu_mems:
        print(f"  VRAM: peak={max(gpu_mems)}MB")

    return {
        "instances": n,
        "wall_time": wall_time,
        "total_audio": total_audio,
        "throughput_x": total_audio / wall_time if wall_time > 0 else 0,
        "success": len(successful),
        "total": n * reqs_per_instance,
        "avg_gen": sum(gen_times)/len(gen_times) if gen_times else 0,
        "avg_gpu": sum(gpu_utils)/len(gpu_utils) if gpu_utils else 0,
        "peak_gpu": max(gpu_utils) if gpu_utils else 0,
        "peak_mem": max(gpu_mems) if gpu_mems else 0,
    }

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    text = TEXT_FILE.read_text().strip()

    # Check all instances
    for n, urls in INSTANCES.items():
        for i, url in enumerate(urls):
            port = url.split(":")[2].split("/")[0]
            try:
                requests.get(f"http://localhost:{port}/v1/models", timeout=5)
                print(f"Instance {i+1} (:{port}): OK")
            except:
                print(f"Instance {i+1} (:{port}): FAILED")
                return

    gpu = get_gpu_stats()
    print(f"\nBaseline: {gpu['gpu_pct']}% GPU, {gpu['mem_mb']}MB VRAM")

    # Warmup all
    print("\nWarming up all instances...")
    for n, urls in INSTANCES.items():
        for i, url in enumerate(urls):
            r = generate_tts(url, text, OUTPUT_DIR / f"warmup_inst{i+1}.mp3", f"warmup")
            if r["success"]:
                print(f"  inst{i+1}: {r['gen_time']:.2f}s")
            break  # Only warmup once per instance
    # Actually warmup all
    for url_idx, url in enumerate(INSTANCES[3]):
        r = generate_tts(url, text, OUTPUT_DIR / f"warmup_all_{url_idx}.mp3", f"warmup_{url_idx}")
        print(f"  Warmup inst{url_idx+1}: {'OK' if r['success'] else 'FAIL'} {r['gen_time']:.2f}s")

    time.sleep(3)

    results = {}
    for n in [1, 2, 3]:
        results[n] = benchmark_n_instances(n, text, REQS_PER_INSTANCE)
        time.sleep(3)  # Cool down between tests

    # Summary
    print(f"\n\n{'='*80}")
    print("SCALING COMPARISON")
    print(f"{'='*80}")
    print(f"{'Instances':>10} | {'OK/Tot':>7} | {'Wall(s)':>8} | {'AvgGen(s)':>10} | {'Throughput':>10} | {'GPU avg':>8} | {'GPU pk':>7} | {'VRAM pk':>8} | {'Scale':>6}")
    print(f"{'-'*10}-+-{'-'*7}-+-{'-'*8}-+-{'-'*10}-+-{'-'*10}-+-{'-'*8}-+-{'-'*7}-+-{'-'*8}-+-{'-'*6}")

    baseline_tp = results[1]["throughput_x"]
    for n in [1, 2, 3]:
        r = results[n]
        scale = r["throughput_x"] / baseline_tp if baseline_tp > 0 else 0
        print(f"{r['instances']:>10} | {r['success']}/{r['total']:>2}   | {r['wall_time']:>7.1f}s | {r['avg_gen']:>9.2f}s | {r['throughput_x']:>8.1f}x  | {r['avg_gpu']:>6.0f}%  | {r['peak_gpu']:>5}%  | {r['peak_mem']:>6}MB | {scale:>5.2f}x")

    best = max(results.values(), key=lambda x: x["throughput_x"])
    print(f"\n--- MAX CAPACITY (RTX 4090) ---")
    print(f"Best: {best['instances']} instances at {best['throughput_x']:.1f}x realtime")
    audio_hr = 3600 * best['throughput_x']
    print(f"Audio per hour: {audio_hr/3600:.1f} hours")
    print(f"If avg request = 30s audio: {audio_hr/30:.0f} requests/hour")
    print(f"If avg request = 2min audio: {audio_hr/120:.0f} requests/hour")
    print(f"GPU headroom remaining: {100 - best['peak_gpu']}% (peak was {best['peak_gpu']}%)")
    print(f"VRAM headroom remaining: {24564 - best['peak_mem']}MB")

if __name__ == "__main__":
    main()
