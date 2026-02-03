#!/usr/bin/env python3
"""Stress test: 1-5 instances, 20 req each. Find the wall."""

import requests
import time
import subprocess
import threading
import concurrent.futures
from pathlib import Path

PORTS = [8880, 8882, 8883, 8884, 8886]
VOICE = "af_heart"
SPEED = 1.25
OUTPUT_DIR = Path(__file__).parent / "output"
TEXT_FILE = Path(__file__).parent / "benchmark_text.txt"
REQS_PER_INSTANCE = 20

def get_gpu_stats():
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        parts = [p.strip() for p in result.stdout.strip().split(", ")]
        return {"gpu_pct": int(parts[0]), "mem_mb": int(parts[1]), "mem_total": int(parts[2]),
                "temp_c": int(parts[3]), "power_w": float(parts[4])}
    except:
        return {"gpu_pct": -1, "mem_mb": -1, "mem_total": -1, "temp_c": -1, "power_w": -1}

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

def generate_tts(port, text, output_path, label=""):
    url = f"http://localhost:{port}/v1/audio/speech"
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
        return {"label": label, "success": False, "gen_time": time.time() - start, "error": str(e)[:100]}

def run_sequential_on_port(port, text, count):
    results = []
    for i in range(count):
        r = generate_tts(port, text, OUTPUT_DIR / f"stress_p{port}_{i:02d}.mp3", f":{port}_r{i}")
        results.append(r)
    return results

def benchmark(instance_count, text, reqs_per):
    ports = PORTS[:instance_count]
    total_reqs = instance_count * reqs_per

    print(f"\n{'='*70}")
    print(f"STRESS TEST: {instance_count} instances x {reqs_per} req = {total_reqs} total")
    print(f"Expected audio: ~{total_reqs * 127 / 60:.0f} minutes ({total_reqs * 127 / 3600:.1f} hours)")
    print(f"{'='*70}")

    # GPU sampling
    gpu_samples = []
    stop = threading.Event()
    def sampler():
        while not stop.is_set():
            gpu_samples.append(get_gpu_stats())
            time.sleep(0.5)
    t = threading.Thread(target=sampler, daemon=True)
    t.start()

    start = time.time()
    all_results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=instance_count) as executor:
        futures = []
        for port in ports:
            futures.append(executor.submit(run_sequential_on_port, port, text, reqs_per))

        completed = 0
        for f in concurrent.futures.as_completed(futures):
            batch = f.result()
            all_results.extend(batch)
            completed += 1
            ok = len([r for r in batch if r["success"]])
            fail = len([r for r in batch if not r["success"]])
            print(f"  Instance {completed}/{instance_count} done: {ok} ok, {fail} failed")

    wall_time = time.time() - start
    stop.set()
    t.join(timeout=2)

    successful = [r for r in all_results if r["success"]]
    failed = [r for r in all_results if not r["success"]]
    gpu_utils = [s["gpu_pct"] for s in gpu_samples if s["gpu_pct"] >= 0]
    gpu_mems = [s["mem_mb"] for s in gpu_samples if s["mem_mb"] >= 0]
    gpu_temps = [s["temp_c"] for s in gpu_samples if s["temp_c"] >= 0]
    gpu_power = [s["power_w"] for s in gpu_samples if s["power_w"] >= 0]

    total_audio = sum(r["audio_dur"] for r in successful)
    gen_times = [r["gen_time"] for r in successful]

    print(f"\n  --- Results ---")
    print(f"  Wall time:    {wall_time:.1f}s ({wall_time/60:.1f} min)")
    print(f"  Success:      {len(successful)}/{total_reqs}")
    if failed:
        # Group failures by error
        errors = {}
        for f in failed:
            e = f.get("error", "unknown")
            errors[e] = errors.get(e, 0) + 1
        for e, c in errors.items():
            print(f"  Failures:     {c}x {e}")

    if successful:
        print(f"  Total audio:  {total_audio:.0f}s ({total_audio/60:.1f} min, {total_audio/3600:.2f} hr)")
        print(f"  Throughput:   {total_audio/wall_time:.1f}x realtime")
        print(f"  Avg gen/req:  {sum(gen_times)/len(gen_times):.2f}s")
        print(f"  Min/Max gen:  {min(gen_times):.2f}s / {max(gen_times):.2f}s")

    if gpu_utils:
        print(f"  GPU compute:  avg={sum(gpu_utils)/len(gpu_utils):.0f}%, peak={max(gpu_utils)}%, min={min(gpu_utils)}%")
    if gpu_mems:
        print(f"  VRAM:         avg={sum(gpu_mems)/len(gpu_mems):.0f}MB, peak={max(gpu_mems)}MB")
    if gpu_temps:
        print(f"  Temperature:  avg={sum(gpu_temps)/len(gpu_temps):.0f}°C, peak={max(gpu_temps)}°C")
    if gpu_power:
        print(f"  Power draw:   avg={sum(gpu_power)/len(gpu_power):.0f}W, peak={max(gpu_power):.0f}W")

    return {
        "instances": instance_count,
        "reqs_per": reqs_per,
        "total_reqs": total_reqs,
        "wall_time": wall_time,
        "success": len(successful),
        "failed": len(failed),
        "total_audio": total_audio,
        "throughput_x": total_audio / wall_time if wall_time > 0 else 0,
        "avg_gen": sum(gen_times)/len(gen_times) if gen_times else 0,
        "min_gen": min(gen_times) if gen_times else 0,
        "max_gen": max(gen_times) if gen_times else 0,
        "avg_gpu": sum(gpu_utils)/len(gpu_utils) if gpu_utils else 0,
        "peak_gpu": max(gpu_utils) if gpu_utils else 0,
        "peak_mem": max(gpu_mems) if gpu_mems else 0,
        "avg_temp": sum(gpu_temps)/len(gpu_temps) if gpu_temps else 0,
        "peak_temp": max(gpu_temps) if gpu_temps else 0,
        "avg_power": sum(gpu_power)/len(gpu_power) if gpu_power else 0,
        "peak_power": max(gpu_power) if gpu_power else 0,
    }

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    text = TEXT_FILE.read_text().strip()

    # Check all instances
    print("Checking instances...")
    for port in PORTS:
        try:
            requests.get(f"http://localhost:{port}/v1/models", timeout=5)
            print(f"  :{port} OK")
        except:
            print(f"  :{port} FAILED")
            return

    gpu = get_gpu_stats()
    print(f"\nBaseline: {gpu['gpu_pct']}% GPU, {gpu['mem_mb']}MB VRAM, {gpu['temp_c']}°C, {gpu['power_w']}W\n")

    # Warmup all instances
    print("Warming up all 5 instances...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futs = {executor.submit(generate_tts, p, text, OUTPUT_DIR / f"warmup_{p}.mp3", f"warmup_{p}"): p for p in PORTS}
        for f in concurrent.futures.as_completed(futs):
            r = f.result()
            print(f"  :{futs[f]} {'OK' if r['success'] else 'FAIL'} {r['gen_time']:.2f}s")

    time.sleep(3)

    # Run 1 through 5 instances
    results = {}
    for n in [1, 2, 3, 4, 5]:
        results[n] = benchmark(n, text, REQS_PER_INSTANCE)
        time.sleep(5)  # Cool down between tests

    # Final summary
    print(f"\n\n{'='*100}")
    print("STRESS TEST SCALING SUMMARY")
    print(f"{'='*100}")
    print(f"{'Inst':>5} | {'Reqs':>5} | {'OK/Tot':>7} | {'Wall':>8} | {'AvgGen':>7} | {'MaxGen':>7} | {'Through':>9} | {'GPU avg':>8} | {'GPU pk':>7} | {'Temp pk':>8} | {'Power pk':>9} | {'Scale':>6}")
    print(f"{'-'*5}-+-{'-'*5}-+-{'-'*7}-+-{'-'*8}-+-{'-'*7}-+-{'-'*7}-+-{'-'*9}-+-{'-'*8}-+-{'-'*7}-+-{'-'*8}-+-{'-'*9}-+-{'-'*6}")

    baseline_tp = results[1]["throughput_x"]
    for n in [1, 2, 3, 4, 5]:
        r = results[n]
        scale = r["throughput_x"] / baseline_tp if baseline_tp > 0 else 0
        print(f"{r['instances']:>5} | {r['total_reqs']:>5} | {r['success']}/{r['total_reqs']:>3}  | {r['wall_time']:>6.0f}s  | {r['avg_gen']:>5.2f}s | {r['max_gen']:>5.2f}s | {r['throughput_x']:>7.1f}x  | {r['avg_gpu']:>6.0f}%  | {r['peak_gpu']:>5}%  | {r['peak_temp']:>5}°C  | {r['peak_power']:>6.0f}W   | {scale:>5.2f}x")

    # Capacity projections
    best = max(results.values(), key=lambda x: x["throughput_x"])
    diminishing = None
    for n in [2, 3, 4, 5]:
        prev_tp = results[n-1]["throughput_x"]
        curr_tp = results[n]["throughput_x"]
        marginal = (curr_tp - prev_tp) / baseline_tp if baseline_tp > 0 else 0
        if marginal < 0.5:  # Less than 50% marginal scaling
            diminishing = n
            break

    print(f"\n--- CAPACITY ANALYSIS ---")
    print(f"Peak throughput: {best['throughput_x']:.1f}x realtime at {best['instances']} instances")
    print(f"Audio per hour: {3600 * best['throughput_x'] / 3600:.1f} hours")
    print(f"Peak GPU: {best['peak_gpu']}%")
    print(f"Peak temp: {best['peak_temp']}°C")
    print(f"Peak power: {best['peak_power']:.0f}W")
    if diminishing:
        print(f"Diminishing returns start at: {diminishing} instances")
    print(f"\nIf avg request = 30s:  {3600 * best['throughput_x'] / 30:.0f} requests/hour")
    print(f"If avg request = 2min: {3600 * best['throughput_x'] / 120:.0f} requests/hour")

    # Per-instance marginal analysis
    print(f"\n--- MARGINAL SCALING PER INSTANCE ---")
    for n in [1, 2, 3, 4, 5]:
        tp = results[n]["throughput_x"]
        if n == 1:
            print(f"  {n} inst: {tp:.1f}x (baseline)")
        else:
            prev = results[n-1]["throughput_x"]
            marginal = tp - prev
            pct = marginal / baseline_tp * 100
            print(f"  {n} inst: {tp:.1f}x (+{marginal:.1f}x, +{pct:.0f}% of baseline)")

if __name__ == "__main__":
    main()
