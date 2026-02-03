#!/usr/bin/env python3
"""Honest benchmark with continuous nvidia-smi monitoring.
Uses nvidia-smi dmon for real sustained GPU readings, not point samples."""

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
        r = generate_tts(port, text, OUTPUT_DIR / f"honest_p{port}_{i:02d}.mp3", f":{port}_r{i}")
        results.append(r)
    return results

def start_gpu_monitor():
    """Start nvidia-smi dmon which gives 1-second continuous readings.
    This is WAY more accurate than point-in-time nvidia-smi queries."""
    proc = subprocess.Popen(
        ["nvidia-smi", "dmon", "-s", "pucm", "-d", "1"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    return proc

def parse_dmon_output(output_lines):
    """Parse nvidia-smi dmon output for GPU utilization, memory, power, temp."""
    readings = []
    for line in output_lines:
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        parts = line.split()
        if len(parts) >= 10:
            try:
                readings.append({
                    "gpu_pct": int(parts[3]),      # sm (streaming multiprocessor) utilization
                    "mem_util_pct": int(parts[4]),  # mem utilization (bandwidth, not capacity)
                    "power_w": int(parts[1]),       # power draw
                    "temp_c": int(parts[2]),        # temperature
                    "mem_used_mb": int(parts[7]),   # fb (framebuffer) memory used
                })
            except (ValueError, IndexError):
                pass
    return readings

def benchmark(instance_count, text, reqs_per):
    ports = PORTS[:instance_count]
    total_reqs = instance_count * reqs_per

    print(f"\n{'='*70}")
    print(f"STRESS TEST: {instance_count} instances x {reqs_per} req = {total_reqs} total")
    print(f"{'='*70}")

    # Start continuous GPU monitor BEFORE the test
    gpu_proc = start_gpu_monitor()
    time.sleep(2)  # Let it stabilize

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

    # Stop GPU monitor and collect readings
    time.sleep(1)
    gpu_proc.terminate()
    gpu_output = gpu_proc.stdout.read()
    gpu_readings = parse_dmon_output(gpu_output.split("\n"))

    successful = [r for r in all_results if r["success"]]
    failed = [r for r in all_results if not r["success"]]
    total_audio = sum(r["audio_dur"] for r in successful)
    gen_times = [r["gen_time"] for r in successful]

    print(f"\n  --- Results ---")
    print(f"  Wall time:     {wall_time:.1f}s ({wall_time/60:.1f} min)")
    print(f"  Success:       {len(successful)}/{total_reqs}")

    if successful:
        print(f"  Total audio:   {total_audio:.0f}s ({total_audio/60:.1f} min)")
        print(f"  Throughput:    {total_audio/wall_time:.1f}x realtime")
        print(f"  Avg gen/req:   {sum(gen_times)/len(gen_times):.2f}s")
        print(f"  Min/Max gen:   {min(gen_times):.2f}s / {max(gen_times):.2f}s")

    if gpu_readings:
        gpu_utils = [r["gpu_pct"] for r in gpu_readings]
        mem_utils = [r["mem_util_pct"] for r in gpu_readings]
        powers = [r["power_w"] for r in gpu_readings]
        temps = [r["temp_c"] for r in gpu_readings]
        mems = [r["mem_used_mb"] for r in gpu_readings]

        print(f"\n  --- GPU (nvidia-smi dmon, {len(gpu_readings)} samples @ 1Hz) ---")
        print(f"  SM Utilization: avg={sum(gpu_utils)/len(gpu_utils):.0f}%, peak={max(gpu_utils)}%, min={min(gpu_utils)}%")
        print(f"  Mem Bandwidth:  avg={sum(mem_utils)/len(mem_utils):.0f}%, peak={max(mem_utils)}%")
        print(f"  VRAM Used:      avg={sum(mems)/len(mems):.0f}MB, peak={max(mems)}MB")
        print(f"  Temperature:    avg={sum(temps)/len(temps):.0f}°C, peak={max(temps)}°C")
        print(f"  Power:          avg={sum(powers)/len(powers):.0f}W, peak={max(powers)}W")
    else:
        print(f"\n  (No GPU readings captured)")

    return {
        "instances": instance_count,
        "wall_time": wall_time,
        "total_audio": total_audio,
        "throughput_x": total_audio / wall_time if wall_time > 0 else 0,
        "success": len(successful),
        "total": total_reqs,
        "avg_gen": sum(gen_times)/len(gen_times) if gen_times else 0,
        "max_gen": max(gen_times) if gen_times else 0,
        "avg_gpu": sum([r["gpu_pct"] for r in gpu_readings])/len(gpu_readings) if gpu_readings else 0,
        "peak_gpu": max([r["gpu_pct"] for r in gpu_readings]) if gpu_readings else 0,
        "avg_power": sum([r["power_w"] for r in gpu_readings])/len(gpu_readings) if gpu_readings else 0,
        "peak_power": max([r["power_w"] for r in gpu_readings]) if gpu_readings else 0,
        "peak_temp": max([r["temp_c"] for r in gpu_readings]) if gpu_readings else 0,
        "peak_mem": max([r["mem_used_mb"] for r in gpu_readings]) if gpu_readings else 0,
        "avg_mem_bw": sum([r["mem_util_pct"] for r in gpu_readings])/len(gpu_readings) if gpu_readings else 0,
        "peak_mem_bw": max([r["mem_util_pct"] for r in gpu_readings]) if gpu_readings else 0,
    }

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    text = TEXT_FILE.read_text().strip()

    # Check instances
    for port in PORTS:
        try:
            requests.get(f"http://localhost:{port}/v1/models", timeout=5)
            print(f"  :{port} OK")
        except:
            print(f"  :{port} DOWN")

    # Warmup
    print("\nWarming up...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futs = {executor.submit(generate_tts, p, text, OUTPUT_DIR / f"warmup_{p}.mp3", ""): p for p in PORTS}
        for f in concurrent.futures.as_completed(futs):
            r = f.result()
            print(f"  :{futs[f]} {'OK' if r['success'] else 'FAIL'}")
    time.sleep(3)

    # Run tests
    results = {}
    for n in [1, 2, 3, 4, 5]:
        results[n] = benchmark(n, text, REQS_PER_INSTANCE)
        time.sleep(5)

    # Summary
    print(f"\n\n{'='*110}")
    print("HONEST SCALING SUMMARY (nvidia-smi dmon continuous monitoring)")
    print(f"{'='*110}")
    print(f"{'Inst':>5} | {'OK/Tot':>7} | {'Wall':>8} | {'AvgGen':>7} | {'MaxGen':>7} | {'Through':>9} | {'GPU avg':>8} | {'GPU pk':>7} | {'MemBW avg':>9} | {'Power avg':>10} | {'Scale':>6}")
    print(f"{'-'*5}-+-{'-'*7}-+-{'-'*8}-+-{'-'*7}-+-{'-'*7}-+-{'-'*9}-+-{'-'*8}-+-{'-'*7}-+-{'-'*9}-+-{'-'*10}-+-{'-'*6}")

    baseline_tp = results[1]["throughput_x"]
    for n in [1, 2, 3, 4, 5]:
        r = results[n]
        scale = r["throughput_x"] / baseline_tp if baseline_tp > 0 else 0
        print(f"{n:>5} | {r['success']}/{r['total']:>3}  | {r['wall_time']:>6.0f}s  | {r['avg_gen']:>5.2f}s | {r['max_gen']:>5.2f}s | {r['throughput_x']:>7.1f}x  | {r['avg_gpu']:>6.0f}%  | {r['peak_gpu']:>5}%  | {r['avg_mem_bw']:>7.0f}%  | {r['avg_power']:>7.0f}W    | {scale:>5.2f}x")

    # Marginal analysis
    print(f"\n--- MARGINAL SCALING ---")
    for n in [1, 2, 3, 4, 5]:
        tp = results[n]["throughput_x"]
        if n == 1:
            print(f"  {n} inst: {tp:.1f}x (baseline)")
        else:
            prev = results[n-1]["throughput_x"]
            marginal = tp - prev
            pct = marginal / baseline_tp * 100
            print(f"  {n} inst: {tp:.1f}x (+{marginal:.1f}x, +{pct:.0f}% of baseline) | GPU avg: {results[n]['avg_gpu']:.0f}%")

    # What's the actual bottleneck?
    print(f"\n--- BOTTLENECK ANALYSIS ---")
    r5 = results[5]
    print(f"At 5 instances:")
    print(f"  GPU compute (SM):  {r5['avg_gpu']:.0f}% avg, {r5['peak_gpu']}% peak")
    print(f"  GPU mem bandwidth: {r5['avg_mem_bw']:.0f}% avg, {r5['peak_mem_bw']}% peak")
    print(f"  Power:             {r5['avg_power']:.0f}W avg, {r5['peak_power']}W peak")
    if r5['avg_gpu'] < 70:
        print(f"  >> GPU compute is NOT saturated. Bottleneck is likely CPU/Python/uvicorn.")
    elif r5['avg_gpu'] < 90:
        print(f"  >> GPU moderately loaded. Could be mixed GPU+CPU bottleneck.")
    else:
        print(f"  >> GPU is saturated. Compute-bound.")

if __name__ == "__main__":
    main()
