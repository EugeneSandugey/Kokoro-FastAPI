#!/usr/bin/env python3
"""Prove whether requests actually run in parallel using subprocesses (not threads).
Each request is a completely separate Python process - zero shared state."""

import subprocess
import time
import json
import sys
from pathlib import Path

PORTS = [8880, 8882, 8883, 8884, 8886]
TEXT = Path(__file__).parent.joinpath("benchmark_text.txt").read_text().strip()
OUTPUT_DIR = Path(__file__).parent / "output"

# Write a tiny worker script that each subprocess will run
WORKER = '''
import requests, sys, time, json
port = int(sys.argv[1])
text = sys.argv[2]
outpath = sys.argv[3]
start = time.time()
print(json.dumps({"port": port, "event": "start", "time": f"{start:.3f}"}), flush=True)
r = requests.post(f"http://localhost:{port}/v1/audio/speech",
    json={"input": text, "voice": "af_heart", "speed": 1.25, "response_format": "mp3"}, timeout=300)
elapsed = time.time() - start
with open(outpath, "wb") as f:
    f.write(r.content)
print(json.dumps({"port": port, "event": "done", "elapsed": f"{elapsed:.3f}", "size": len(r.content), "status": r.status_code}), flush=True)
'''

WORKER_FILE = OUTPUT_DIR / "_worker.py"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
WORKER_FILE.write_text(WORKER)

n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
ports = PORTS[:n]

print(f"Launching {n} SEPARATE PROCESSES to {n} instances...")
print(f"Each process is independent - zero shared state, no GIL\n")

# Start GPU monitor
gpu_proc = subprocess.Popen(
    ["bash", "-c", "while true; do echo \"$(date +%T),$(nvidia-smi --query-gpu=utilization.gpu,memory.used,power.draw --format=csv,noheader,nounits)\"; sleep 1; done"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
)

time.sleep(1)

# Launch all subprocesses simultaneously
procs = []
t0 = time.time()
for port in ports:
    outpath = str(OUTPUT_DIR / f"proof_{port}.mp3")
    p = subprocess.Popen(
        [sys.executable, str(WORKER_FILE), str(port), TEXT, outpath],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    procs.append((port, p))

print(f"All {n} processes launched at T+0.000s")
print(f"Waiting for completion...\n")

# Collect results
for port, p in procs:
    stdout, stderr = p.communicate(timeout=300)
    for line in stdout.strip().split("\n"):
        if line.strip():
            try:
                d = json.loads(line)
                if d["event"] == "start":
                    rel = float(d["time"]) - t0
                    print(f"  :{d['port']} STARTED at T+{rel:.3f}s")
                elif d["event"] == "done":
                    print(f"  :{d['port']} DONE    in {d['elapsed']}s (status={d['status']}, size={d['size']})")
            except:
                print(f"  :{port} raw: {line}")

wall = time.time() - t0
print(f"\nTotal wall time: {wall:.2f}s")

# Stop GPU monitor and print
gpu_proc.terminate()
gpu_out = gpu_proc.stdout.read()
print(f"\n=== GPU during test ===")
for line in gpu_out.strip().split("\n"):
    print(f"  {line}")
