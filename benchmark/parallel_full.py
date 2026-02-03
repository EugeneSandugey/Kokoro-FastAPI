#!/usr/bin/env python3
"""Full parallel benchmark using subprocesses. Each instance gets its own process
doing sequential requests, all processes run simultaneously."""

import subprocess
import time
import json
import sys
from pathlib import Path

PORTS = [8880, 8882, 8883, 8884, 8886]
TEXT = Path(__file__).parent.joinpath("benchmark_text.txt").read_text().strip()
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WORKER = '''
import requests, sys, time, json, subprocess
port = int(sys.argv[1])
text = sys.argv[2]
count = int(sys.argv[3])
outdir = sys.argv[4]

results = []
for i in range(count):
    start = time.time()
    r = requests.post(f"http://localhost:{port}/v1/audio/speech",
        json={"input": text, "voice": "af_heart", "speed": 1.25, "response_format": "mp3"}, timeout=300)
    elapsed = time.time() - start
    outpath = f"{outdir}/full_{port}_{i:02d}.mp3"
    with open(outpath, "wb") as f:
        f.write(r.content)
    dur = 0
    try:
        p = subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",outpath],
            capture_output=True, text=True, timeout=10)
        dur = float(p.stdout.strip())
    except: pass
    results.append({"i": i, "elapsed": round(elapsed, 3), "dur": round(dur, 1), "ok": r.status_code == 200})

print(json.dumps({"port": port, "results": results}))
'''

WORKER_FILE = OUTPUT_DIR / "_full_worker.py"
WORKER_FILE.write_text(WORKER)

n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
reqs = int(sys.argv[2]) if len(sys.argv) > 2 else 20
ports = PORTS[:n]

print(f"=== {n} instances x {reqs} sequential reqs = {n*reqs} total ===")
print(f"Each instance runs in its OWN subprocess (true parallelism)\n")

# GPU monitor
gpu_proc = subprocess.Popen(
    ["bash", "-c", "while true; do echo \"$(date +%T),$(nvidia-smi --query-gpu=utilization.gpu,memory.used,power.draw --format=csv,noheader,nounits)\"; sleep 1; done"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
)
time.sleep(1)

# Launch all
t0 = time.time()
procs = []
for port in ports:
    p = subprocess.Popen(
        [sys.executable, str(WORKER_FILE), str(port), TEXT, str(reqs), str(OUTPUT_DIR)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    procs.append((port, p))

print(f"All {n} processes launched. Running {reqs} requests each...\n")

# Wait and collect
all_results = {}
for port, p in procs:
    stdout, stderr = p.communicate(timeout=600)
    try:
        data = json.loads(stdout.strip())
        all_results[port] = data["results"]
        ok = sum(1 for r in data["results"] if r["ok"])
        times = [r["elapsed"] for r in data["results"]]
        print(f"  :{port} done - {ok}/{reqs} ok, avg={sum(times)/len(times):.2f}s, min={min(times):.2f}s, max={max(times):.2f}s")
    except Exception as e:
        print(f"  :{port} ERROR: {e}")
        if stderr:
            print(f"    stderr: {stderr[:200]}")

wall = time.time() - t0

# Stop GPU
gpu_proc.terminate()
gpu_out = gpu_proc.stdout.read()

# Summary
total_ok = sum(sum(1 for r in results if r["ok"]) for results in all_results.values())
total_audio = sum(sum(r["dur"] for r in results) for results in all_results.values())
all_times = [r["elapsed"] for results in all_results.values() for r in results]

print(f"\n{'='*60}")
print(f"RESULTS: {n} instances x {reqs} reqs")
print(f"{'='*60}")
print(f"Wall time:     {wall:.1f}s ({wall/60:.1f} min)")
print(f"Success:       {total_ok}/{n*reqs}")
print(f"Total audio:   {total_audio:.0f}s ({total_audio/60:.1f} min)")
print(f"Throughput:    {total_audio/wall:.1f}x realtime")
print(f"Avg gen/req:   {sum(all_times)/len(all_times):.2f}s")
print(f"Min/Max gen:   {min(all_times):.2f}s / {max(all_times):.2f}s")

# GPU summary
gpu_lines = gpu_out.strip().split("\n")
gpu_pcts = []
gpu_powers = []
for line in gpu_lines:
    parts = line.split(",")
    if len(parts) >= 3:
        try:
            gpu_pcts.append(int(parts[1].strip()))
            gpu_powers.append(float(parts[3].strip()))
        except:
            pass

if gpu_pcts:
    print(f"\nGPU utilization: avg={sum(gpu_pcts)/len(gpu_pcts):.0f}%, min={min(gpu_pcts)}%, max={max(gpu_pcts)}%")
    print(f"Power:           avg={sum(gpu_powers)/len(gpu_powers):.0f}W, max={max(gpu_powers):.0f}W")
    print(f"Samples:         {len(gpu_pcts)} readings at 1Hz")
    print(f"\nRaw GPU log (every second):")
    for line in gpu_lines[-30:]:  # Last 30 readings
        print(f"  {line}")
