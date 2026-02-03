#!/usr/bin/env python3
"""Benchmark dual Kokoro instances - do they actually double throughput?"""

import requests
import time
import subprocess
import os
import threading
import concurrent.futures
from pathlib import Path

INSTANCE_1 = "http://localhost:8880/v1/audio/speech"
INSTANCE_2 = "http://localhost:8882/v1/audio/speech"
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

def gpu_sampler(samples_list, stop_event, interval=0.25):
    while not stop_event.is_set():
        samples_list.append(get_gpu_stats())
        time.sleep(interval)

def run_test(label, tasks):
    """Run a set of tasks and collect GPU samples. tasks = list of (url, output_path, label)"""
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"{'='*60}")

    text = TEXT_FILE.read_text().strip()
    gpu_samples = []
    stop_event = threading.Event()
    sampler = threading.Thread(target=gpu_sampler, args=(gpu_samples, stop_event, 0.25), daemon=True)
    sampler.start()

    start = time.time()
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = {}
        for url, outpath, task_label in tasks:
            f = executor.submit(generate_tts, url, text, outpath, task_label)
            futures[f] = task_label

        for f in concurrent.futures.as_completed(futures):
            r = f.result()
            results.append(r)
            status = f"{r['gen_time']:.2f}s, audio={r['audio_dur']:.1f}s" if r["success"] else f"FAILED: {r.get('error','?')}"
            print(f"  [{r['label']}] {status}")

    wall_time = time.time() - start
    stop_event.set()
    sampler.join(timeout=2)

    successful = [r for r in results if r["success"]]
    gpu_utils = [s["gpu_pct"] for s in gpu_samples if s["gpu_pct"] >= 0]
    gpu_mems = [s["mem_mb"] for s in gpu_samples if s["mem_mb"] >= 0]

    total_audio = sum(r["audio_dur"] for r in successful)

    print(f"\n  Wall time: {wall_time:.2f}s")
    print(f"  Success: {len(successful)}/{len(tasks)}")
    if successful:
        gen_times = [r["gen_time"] for r in successful]
        print(f"  Total audio: {total_audio:.1f}s ({total_audio/60:.1f} min)")
        print(f"  Throughput: {total_audio/wall_time:.1f}x realtime")
        print(f"  Avg gen/req: {sum(gen_times)/len(gen_times):.2f}s")
        print(f"  Min/Max gen: {min(gen_times):.2f}s / {max(gen_times):.2f}s")
    if gpu_utils:
        print(f"  GPU: avg={sum(gpu_utils)/len(gpu_utils):.0f}%, peak={max(gpu_utils)}%, samples={len(gpu_utils)}")
    if gpu_mems:
        print(f"  VRAM: avg={sum(gpu_mems)/len(gpu_mems):.0f}MB, peak={max(gpu_mems)}MB")

    return {
        "label": label,
        "wall_time": wall_time,
        "total_audio": total_audio,
        "throughput_x": total_audio / wall_time if wall_time > 0 else 0,
        "success": len(successful),
        "total": len(tasks),
        "avg_gpu": sum(gpu_utils)/len(gpu_utils) if gpu_utils else 0,
        "peak_gpu": max(gpu_utils) if gpu_utils else 0,
        "peak_mem": max(gpu_mems) if gpu_mems else 0,
        "results": results,
    }

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    text = TEXT_FILE.read_text().strip()

    # Check both instances
    for name, port in [("Instance 1", 8880), ("Instance 2", 8882)]:
        try:
            r = requests.get(f"http://localhost:{port}/v1/models", timeout=5)
            print(f"{name} (:{port}): OK")
        except:
            print(f"{name} (:{port}): FAILED - exiting")
            return

    gpu = get_gpu_stats()
    print(f"Baseline GPU: {gpu['gpu_pct']}% util, {gpu['mem_mb']}MB VRAM\n")

    # Warmup both instances
    print("Warming up both instances...")
    for name, url in [("inst1", INSTANCE_1), ("inst2", INSTANCE_2)]:
        r = generate_tts(url, text, OUTPUT_DIR / f"warmup_{name}.mp3", f"warmup_{name}")
        if r["success"]:
            print(f"  {name}: {r['gen_time']:.2f}s, audio={r['audio_dur']:.1f}s")
        else:
            print(f"  {name}: FAILED - {r.get('error')}")
            return

    time.sleep(2)

    # ---- Test 1: Single instance, 1 request ----
    t1 = run_test("Single instance, 1 request", [
        (INSTANCE_1, OUTPUT_DIR / "t1_0.mp3", "inst1_req0"),
    ])

    time.sleep(2)

    # ---- Test 2: Single instance, 5 sequential ----
    print(f"\n{'='*60}")
    print("TEST: Single instance, 5 sequential")
    print(f"{'='*60}")

    gpu_samples = []
    stop_event = threading.Event()
    sampler_thread = threading.Thread(target=gpu_sampler, args=(gpu_samples, stop_event, 0.25), daemon=True)
    sampler_thread.start()

    seq_start = time.time()
    seq_results = []
    for i in range(5):
        r = generate_tts(INSTANCE_1, text, OUTPUT_DIR / f"t2_seq_{i}.mp3", f"inst1_seq_{i}")
        seq_results.append(r)
        status = f"{r['gen_time']:.2f}s" if r["success"] else f"FAILED"
        print(f"  [{r['label']}] {status}")
    seq_wall = time.time() - seq_start
    stop_event.set()
    sampler_thread.join(timeout=2)

    seq_audio = sum(r["audio_dur"] for r in seq_results if r["success"])
    seq_gpu = [s["gpu_pct"] for s in gpu_samples if s["gpu_pct"] >= 0]
    print(f"\n  Wall time: {seq_wall:.2f}s")
    print(f"  Total audio: {seq_audio:.1f}s ({seq_audio/60:.1f} min)")
    print(f"  Throughput: {seq_audio/seq_wall:.1f}x realtime")
    if seq_gpu:
        print(f"  GPU: avg={sum(seq_gpu)/len(seq_gpu):.0f}%, peak={max(seq_gpu)}%")

    t2 = {"label": "Single inst, 5 sequential", "wall_time": seq_wall, "total_audio": seq_audio,
           "throughput_x": seq_audio/seq_wall, "avg_gpu": sum(seq_gpu)/len(seq_gpu) if seq_gpu else 0,
           "peak_gpu": max(seq_gpu) if seq_gpu else 0}

    time.sleep(2)

    # ---- Test 3: Dual instance, 1 each simultaneous ----
    t3 = run_test("Dual instances, 1 req each (simultaneous)", [
        (INSTANCE_1, OUTPUT_DIR / "t3_inst1.mp3", "inst1"),
        (INSTANCE_2, OUTPUT_DIR / "t3_inst2.mp3", "inst2"),
    ])

    time.sleep(2)

    # ---- Test 4: Dual instance, 5 each (round-robin sequential per instance, parallel across) ----
    print(f"\n{'='*60}")
    print("TEST: Dual instances, 5 req each (sequential per instance, parallel across)")
    print(f"{'='*60}")

    gpu_samples_t4 = []
    stop_event_t4 = threading.Event()
    sampler_t4 = threading.Thread(target=gpu_sampler, args=(gpu_samples_t4, stop_event_t4, 0.25), daemon=True)
    sampler_t4.start()

    def run_sequential_on_instance(url, instance_name, count):
        results = []
        for i in range(count):
            r = generate_tts(url, text, OUTPUT_DIR / f"t4_{instance_name}_{i}.mp3", f"{instance_name}_seq_{i}")
            results.append(r)
            status = f"{r['gen_time']:.2f}s" if r["success"] else "FAILED"
            print(f"  [{r['label']}] {status}")
        return results

    t4_start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_sequential_on_instance, INSTANCE_1, "inst1", 5)
        f2 = executor.submit(run_sequential_on_instance, INSTANCE_2, "inst2", 5)
        r1 = f1.result()
        r2 = f2.result()
    t4_wall = time.time() - t4_start
    stop_event_t4.set()
    sampler_t4.join(timeout=2)

    all_r = r1 + r2
    t4_audio = sum(r["audio_dur"] for r in all_r if r["success"])
    t4_success = len([r for r in all_r if r["success"]])
    t4_gpu = [s["gpu_pct"] for s in gpu_samples_t4 if s["gpu_pct"] >= 0]
    t4_mem = [s["mem_mb"] for s in gpu_samples_t4 if s["mem_mb"] >= 0]

    print(f"\n  Wall time: {t4_wall:.2f}s")
    print(f"  Success: {t4_success}/10")
    print(f"  Total audio: {t4_audio:.1f}s ({t4_audio/60:.1f} min)")
    print(f"  Throughput: {t4_audio/t4_wall:.1f}x realtime")
    if t4_gpu:
        print(f"  GPU: avg={sum(t4_gpu)/len(t4_gpu):.0f}%, peak={max(t4_gpu)}%")
    if t4_mem:
        print(f"  VRAM: peak={max(t4_mem)}MB")

    t4 = {"label": "Dual inst, 5+5 sequential/parallel", "wall_time": t4_wall, "total_audio": t4_audio,
           "throughput_x": t4_audio/t4_wall, "success": t4_success, "total": 10,
           "avg_gpu": sum(t4_gpu)/len(t4_gpu) if t4_gpu else 0, "peak_gpu": max(t4_gpu) if t4_gpu else 0,
           "peak_mem": max(t4_mem) if t4_mem else 0}

    time.sleep(2)

    # ---- Test 5: Triple instances (start a 3rd) ----
    # We'll test this only if dual works well

    # ---- SUMMARY ----
    print(f"\n\n{'='*80}")
    print("FINAL COMPARISON")
    print(f"{'='*80}")
    print(f"{'Test':<45} | {'Wall(s)':>8} | {'Audio(s)':>9} | {'Throughput':>10} | {'GPU avg':>8} | {'GPU pk':>7}")
    print(f"{'-'*45}-+-{'-'*8}-+-{'-'*9}-+-{'-'*10}-+-{'-'*8}-+-{'-'*7}")

    tests = [
        ("1x inst, 1 req", t1),
        ("1x inst, 5 seq", t2),
        ("2x inst, 1+1 parallel", t3),
        ("2x inst, 5+5 seq/parallel", t4),
    ]

    for name, t in tests:
        print(f"{name:<45} | {t['wall_time']:>7.1f}s | {t['total_audio']:>8.1f}s | {t['throughput_x']:>8.1f}x  | {t.get('avg_gpu',0):>6.0f}%  | {t.get('peak_gpu',0):>5}%")

    # Capacity estimate
    print(f"\n--- CAPACITY AT MAX THROUGHPUT ---")
    best = max(tests, key=lambda x: x[1]["throughput_x"])
    bt = best[1]
    print(f"Best config: {best[0]}")
    print(f"Throughput: {bt['throughput_x']:.1f}x realtime")
    audio_per_hour = 3600 * bt['throughput_x']
    print(f"Audio per hour: {audio_per_hour/60:.0f} minutes ({audio_per_hour/3600:.1f} hours)")
    print(f"Peak GPU: {bt.get('peak_gpu',0)}%")
    print(f"Peak VRAM: {bt.get('peak_mem',0)}MB")

    # Single instance comparison
    single_tp = t2["throughput_x"]
    dual_tp = t4["throughput_x"]
    print(f"\nSingle instance throughput: {single_tp:.1f}x")
    print(f"Dual instance throughput:   {dual_tp:.1f}x")
    print(f"Scaling factor: {dual_tp/single_tp:.2f}x (1.0 = no benefit, 2.0 = perfect scaling)")

if __name__ == "__main__":
    main()
