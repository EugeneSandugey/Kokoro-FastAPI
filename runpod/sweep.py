#!/usr/bin/env python3
"""
F5-TTS RunPod Sweep Launcher

Launch parallel hyperparameter sweeps on RunPod with shared Network Volumes.

Usage:
    python sweep.py launch --config configs/lr_sweep.yaml
    python sweep.py launch --config configs/lr_sweep.yaml --dry-run
    python sweep.py monitor --manifest sweep_20260207_123456.json
    python sweep.py cleanup --manifest sweep_20260207_123456.json
    python sweep.py results --manifest sweep_20260207_123456.json
    python sweep.py status   # Quick status of all running pods
"""

import argparse
import itertools
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml

try:
    import runpod
except ImportError:
    print("ERROR: runpod package not installed. Run: pip install runpod")
    sys.exit(1)

REST_API_BASE = "https://rest.runpod.io/v1"


# ---- Configuration ----

def load_api_key():
    """Load RunPod API key from environment or config file."""
    key = os.environ.get("RUNPOD_API_KEY")
    if key:
        return key

    # Try loading from config file
    config_path = Path(__file__).parent / ".runpod_key"
    if config_path.exists():
        return config_path.read_text().strip()

    # Try secret manager
    import subprocess
    try:
        result = subprocess.run(
            ["get-secret", "RUNPOD_API_KEY"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    print("ERROR: RunPod API key not found.")
    print("Set RUNPOD_API_KEY env var, or create runpod/.runpod_key file")
    sys.exit(1)


class SweepConfig:
    """Parse sweep config YAML into individual run configurations."""

    def __init__(self, config_path: str):
        with open(config_path) as f:
            self.raw = yaml.safe_load(f)

        self.runpod = self.raw["runpod"]
        self.sweep = self.raw.get("sweep", {})
        self.fixed = self.raw.get("fixed", {})

    def generate_runs(self) -> list[dict]:
        """Generate all combinations of sweep parameters (grid search)."""
        if not self.sweep:
            # No sweep params = single run with fixed params
            run = {**self.fixed, "RUN_NAME": "single_run"}
            return [run]

        param_names = list(self.sweep.keys())
        param_values = [
            self.sweep[k] if isinstance(self.sweep[k], list) else [self.sweep[k]]
            for k in param_names
        ]

        runs = []
        for combo in itertools.product(*param_values):
            params = dict(zip(param_names, combo))
            merged = {**self.fixed, **params}

            # Generate descriptive run name
            name_parts = []
            for k, v in params.items():
                # Shorten key names for readability
                short_key = k.lower().replace("learning_rate", "lr").replace("batch_size", "bs").replace("epochs", "ep")
                name_parts.append(f"{short_key}{v}")
            run_name = "sweep_" + "_".join(name_parts)
            merged["RUN_NAME"] = run_name

            runs.append(merged)

        return runs

    def estimate_cost(self, runs: list[dict]) -> float:
        """Estimate total cost for all runs."""
        rate = self.runpod.get("cost_per_hour", 0.22)
        hours = self.runpod.get("estimated_hours_per_run", 0.5)
        return len(runs) * rate * hours


# ---- Pod Management ----

def create_pod(run_params: dict, runpod_config: dict) -> dict:
    """Create a single RunPod pod for one sweep configuration.

    Uses REST API when interruptible (spot) is requested, since the Python SDK
    doesn't support the interruptible parameter. Falls back to SDK otherwise.
    """
    env = {k.upper(): str(v) for k, v in run_params.items()}
    name = f"f5-{run_params['RUN_NAME'][:45]}"
    interruptible = runpod_config.get("interruptible", False)

    if interruptible:
        # REST API supports interruptible/spot instances
        payload = {
            "name": name,
            "imageName": runpod_config["image"],
            "gpuTypeIds": [runpod_config["gpu_type"]],
            "gpuTypePriority": "availability",
            "cloudType": runpod_config.get("cloud_type", "SECURE"),
            "interruptible": True,
            "gpuCount": 1,
            "containerDiskInGb": runpod_config.get("container_disk_gb", 20),
            "volumeInGb": 0,
            "networkVolumeId": runpod_config["network_volume_id"],
            "volumeMountPath": "/workspace",
            "env": env,
            "ports": ["22/tcp"],
            "minRAMPerGPU": runpod_config.get("min_memory_gb", 24),
            "supportPublicIp": True,
        }
        if runpod_config.get("data_center_id"):
            payload["dataCenterIds"] = [runpod_config["data_center_id"]]
        if runpod_config.get("allowed_cuda_versions"):
            payload["allowedCudaVersions"] = runpod_config["allowed_cuda_versions"]

        resp = requests.post(
            f"{REST_API_BASE}/pods",
            headers={
                "Authorization": f"Bearer {runpod.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"REST API error {resp.status_code}: {resp.text}")
        return resp.json()
    else:
        # Use SDK for non-spot pods
        pod = runpod.create_pod(
            name=name,
            image_name=runpod_config["image"],
            gpu_type_id=runpod_config["gpu_type"],
            cloud_type=runpod_config.get("cloud_type", "SECURE"),
            gpu_count=1,
            container_disk_in_gb=runpod_config.get("container_disk_gb", 20),
            network_volume_id=runpod_config["network_volume_id"],
            volume_mount_path="/workspace",
            env=env,
            data_center_id=runpod_config.get("data_center_id"),
            min_memory_in_gb=runpod_config.get("min_memory_gb", 24),
        )
        return pod


def get_all_pods() -> list[dict]:
    """Get all pods in the account."""
    return runpod.get_pods()


# ---- Commands ----

def cmd_launch(args):
    """Launch a sweep (create pods for all parameter combinations)."""
    config = SweepConfig(args.config)
    runs = config.generate_runs()

    print(f"=== F5-TTS Sweep Launcher ===")
    print(f"Config:    {args.config}")
    print(f"Image:     {config.runpod['image']}")
    print(f"GPU:       {config.runpod['gpu_type']}")
    print(f"Volume:    {config.runpod['network_volume_id']}")
    print(f"Runs:      {len(runs)}")
    print()

    # Show all runs
    print("Runs to launch:")
    print(f"{'#':<4} {'Run Name':<45} {'Key Params'}")
    print("-" * 90)
    for i, run in enumerate(runs, 1):
        # Show only sweep params (not fixed)
        sweep_params = {k: v for k, v in run.items()
                       if k not in config.fixed and k != "RUN_NAME"}
        param_str = ", ".join(f"{k}={v}" for k, v in sweep_params.items())
        print(f"{i:<4} {run['RUN_NAME']:<45} {param_str}")

    print()
    cost = config.estimate_cost(runs)
    print(f"Estimated cost: ${cost:.2f} ({len(runs)} pods × "
          f"${config.runpod.get('cost_per_hour', 0.22)}/hr × "
          f"{config.runpod.get('estimated_hours_per_run', 0.5)}hr)")

    if args.dry_run:
        print("\n[DRY RUN] No pods created.")
        return

    print()
    response = input("Launch? [y/N] ").strip().lower()
    if response != "y":
        print("Aborted.")
        return

    # Launch all pods
    manifest = {
        "started_at": datetime.utcnow().isoformat(),
        "config_file": str(args.config),
        "config": config.raw,
        "pods": [],
    }

    print()
    for i, run in enumerate(runs, 1):
        name = run["RUN_NAME"]
        print(f"[{i}/{len(runs)}] Creating {name}...", end=" ", flush=True)
        try:
            pod = create_pod(run, config.runpod)
            pod_id = pod["id"]
            print(f"OK (id={pod_id})")
            manifest["pods"].append({
                "id": pod_id,
                "run_name": name,
                "params": run,
                "status": "created",
                "created_at": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            print(f"FAILED: {e}")
            manifest["pods"].append({
                "run_name": name,
                "params": run,
                "status": "create_failed",
                "error": str(e),
            })

    # Save manifest
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    manifest_path = Path(__file__).parent / f"sweep_{timestamp}.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    created = sum(1 for p in manifest["pods"] if p["status"] == "created")
    print(f"\nPods launched: {created}/{len(runs)}")
    print(f"Manifest: {manifest_path}")
    print(f"\nMonitor with: python sweep.py monitor --manifest {manifest_path}")


def cmd_monitor(args):
    """Monitor a running sweep."""
    with open(args.manifest) as f:
        manifest = json.load(f)

    pods = [p for p in manifest["pods"] if "id" in p]
    if not pods:
        print("No pods found in manifest.")
        return

    poll_interval = args.interval or 30
    print(f"Monitoring {len(pods)} pods (poll every {poll_interval}s)")
    print(f"Press Ctrl+C to stop monitoring (pods keep running)\n")

    try:
        while True:
            completed = 0
            print(f"\n--- {datetime.utcnow().strftime('%H:%M:%S')} ---")
            print(f"{'Run Name':<45} {'Status':<12} {'Uptime':<10}")
            print("-" * 70)

            for pod_entry in pods:
                pod_id = pod_entry["id"]
                name = pod_entry["run_name"]
                try:
                    pod = runpod.get_pod(pod_id)
                    status = pod.get("desiredStatus", "UNKNOWN")
                    runtime = pod.get("runtime", {})
                    uptime = runtime.get("uptimeInSeconds", 0) if runtime else 0
                    uptime_str = f"{uptime // 60}m{uptime % 60}s" if uptime else "-"

                    if status in ("EXITED", "TERMINATED"):
                        completed += 1

                    print(f"{name:<45} {status:<12} {uptime_str:<10}")
                except Exception as e:
                    print(f"{name:<45} {'ERROR':<12} {str(e)[:30]}")

            print(f"\nCompleted: {completed}/{len(pods)}")

            if completed >= len(pods):
                print("\nAll pods finished!")
                break

            time.sleep(poll_interval)

    except KeyboardInterrupt:
        print("\nMonitoring stopped. Pods still running.")


def cmd_cleanup(args):
    """Terminate all pods from a sweep."""
    with open(args.manifest) as f:
        manifest = json.load(f)

    pods = [p for p in manifest["pods"] if "id" in p]
    if not pods:
        print("No pods found in manifest.")
        return

    print(f"Will terminate {len(pods)} pods:")
    for p in pods:
        print(f"  {p['run_name']} ({p['id']})")

    response = input("\nTerminate all? [y/N] ").strip().lower()
    if response != "y":
        print("Aborted.")
        return

    for p in pods:
        print(f"Terminating {p['run_name']}...", end=" ", flush=True)
        try:
            runpod.terminate_pod(p["id"])
            print("OK")
        except Exception as e:
            print(f"Error: {e}")


def cmd_results(args):
    """Show results from a completed sweep (reads status files via pod logs)."""
    with open(args.manifest) as f:
        manifest = json.load(f)

    pods = [p for p in manifest["pods"] if "id" in p]

    print(f"=== Sweep Results ===")
    print(f"Started: {manifest.get('started_at', 'unknown')}")
    print()
    print(f"{'Run Name':<45} {'Status':<10} {'LR':<10} {'BS':<8} {'Final Loss'}")
    print("-" * 90)

    for pod_entry in pods:
        name = pod_entry["run_name"]
        params = pod_entry.get("params", {})
        lr = params.get("LEARNING_RATE", "?")
        bs = params.get("BATCH_SIZE", "?")

        # Try to get pod status
        try:
            pod = runpod.get_pod(pod_entry["id"])
            status = pod.get("desiredStatus", "UNKNOWN")
        except Exception:
            status = "TERMINATED"

        # TODO: Parse train.log from volume for final loss
        # For now, show what we know from the API
        print(f"{name:<45} {status:<10} {lr:<10} {bs:<8}")

    print()
    print("Note: For detailed results (loss curves, checkpoints), check the network volume:")
    print("  /workspace/results/<run_name>/train.log")
    print("  /workspace/status/<run_name>.done")


def cmd_status(args):
    """Quick status of all running pods."""
    pods = get_all_pods()

    f5_pods = [p for p in pods if p.get("name", "").startswith("f5-")]

    if not f5_pods:
        print("No F5-TTS pods found.")
        return

    print(f"=== F5-TTS Pods ({len(f5_pods)}) ===")
    print(f"{'Name':<50} {'Status':<12} {'GPU':<20} {'Uptime'}")
    print("-" * 95)

    for pod in f5_pods:
        name = pod.get("name", "?")
        status = pod.get("desiredStatus", "?")
        gpu = pod.get("machine", {}).get("gpuDisplayName", "?") if pod.get("machine") else "?"
        runtime = pod.get("runtime", {})
        uptime = runtime.get("uptimeInSeconds", 0) if runtime else 0
        uptime_str = f"{uptime // 60}m" if uptime else "-"
        print(f"{name:<50} {status:<12} {gpu:<20} {uptime_str}")


# ---- Main ----

def main():
    parser = argparse.ArgumentParser(
        description="F5-TTS RunPod Sweep Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # launch
    p_launch = subparsers.add_parser("launch", help="Launch a sweep")
    p_launch.add_argument("--config", required=True, help="Sweep config YAML")
    p_launch.add_argument("--dry-run", action="store_true", help="Preview without creating pods")

    # monitor
    p_monitor = subparsers.add_parser("monitor", help="Monitor a running sweep")
    p_monitor.add_argument("--manifest", required=True, help="Sweep manifest JSON")
    p_monitor.add_argument("--interval", type=int, default=30, help="Poll interval (seconds)")

    # cleanup
    p_cleanup = subparsers.add_parser("cleanup", help="Terminate all pods from a sweep")
    p_cleanup.add_argument("--manifest", required=True, help="Sweep manifest JSON")

    # results
    p_results = subparsers.add_parser("results", help="Show sweep results")
    p_results.add_argument("--manifest", required=True, help="Sweep manifest JSON")

    # status
    subparsers.add_parser("status", help="Quick status of all F5-TTS pods")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Init RunPod API
    runpod.api_key = load_api_key()

    commands = {
        "launch": cmd_launch,
        "monitor": cmd_monitor,
        "cleanup": cmd_cleanup,
        "results": cmd_results,
        "status": cmd_status,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
