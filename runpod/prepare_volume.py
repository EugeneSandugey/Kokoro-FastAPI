#!/usr/bin/env python3
"""
One-time volume preparation for F5-TTS RunPod training.

Run this INSIDE a utility pod that has the network volume mounted at /workspace.
It prepares the dataset with correct paths for the Docker container layout.

Usage (from inside utility pod):
    python /workspace/prepare_volume.py prepare --data-source /workspace/upload/
    python /workspace/prepare_volume.py verify

Local usage (upload data to volume via rsync/scp first):
    1. Launch a utility pod (any cheap GPU or CPU) with the network volume
    2. rsync/scp local data to the pod
    3. Run this script inside the pod
    4. Terminate the pod
"""

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

VOLUME = "/workspace"
F5_ROOT = "/app/F5-TTS"
DATA_DIR = f"{VOLUME}/data"


def prepare(args):
    """Prepare the network volume with training data."""
    source = Path(args.data_source)

    print("=== Volume Preparation ===")
    print(f"Source: {source}")
    print(f"Volume: {VOLUME}")
    print()

    # Create directory structure
    os.makedirs(f"{DATA_DIR}/kokoro_libri", exist_ok=True)
    os.makedirs(f"{DATA_DIR}/kokoro_libri_pinyin", exist_ok=True)
    os.makedirs(f"{DATA_DIR}/Emilia_ZH_EN_pinyin", exist_ok=True)
    os.makedirs(f"{VOLUME}/pretrained", exist_ok=True)
    os.makedirs(f"{VOLUME}/results", exist_ok=True)
    os.makedirs(f"{VOLUME}/status", exist_ok=True)
    os.makedirs(f"{VOLUME}/runs", exist_ok=True)

    # 1. Copy WAV files
    wav_source = source / "kokoro_libri"
    if wav_source.exists():
        wav_count = len(list(wav_source.glob("*.wav")))
        print(f"[1/5] Copying {wav_count} WAV files...")
        # Use rsync for efficiency (skip existing)
        subprocess.run(
            ["rsync", "-av", "--progress", f"{wav_source}/", f"{DATA_DIR}/kokoro_libri/"],
            check=True,
        )
    else:
        print(f"[1/5] SKIP: No WAV source at {wav_source}")

    # 2. Copy CSV and rewrite paths
    csv_source = source / "kokoro_libri.csv"
    if csv_source.exists():
        print("[2/5] Rewriting CSV with container paths...")
        rewrite_csv(str(csv_source), f"{DATA_DIR}/kokoro_libri.csv")
    else:
        print(f"[2/5] SKIP: No CSV at {csv_source}")

    # 3. Re-prepare tokenized dataset (or copy if pre-prepared)
    arrow_source = source / "kokoro_libri_pinyin" / "raw.arrow"
    if csv_source.exists() and os.path.exists(f"{F5_ROOT}/src/f5_tts/train/datasets/prepare_csv_wavs.py"):
        print("[3/5] Re-preparing tokenized dataset with corrected paths...")
        prepare_dataset()
    elif arrow_source.exists():
        print("[3/5] Copying pre-prepared tokenized dataset...")
        for f in (source / "kokoro_libri_pinyin").iterdir():
            shutil.copy2(f, f"{DATA_DIR}/kokoro_libri_pinyin/")
        print("  WARNING: Arrow file may have wrong paths. Run verify to check.")
    else:
        print("[3/5] SKIP: No tokenized dataset source found")

    # 4. Copy vocab files
    vocab_source = source / "Emilia_ZH_EN_pinyin" / "vocab.txt"
    if vocab_source.exists():
        print("[4/5] Copying Emilia vocab...")
        shutil.copy2(vocab_source, f"{DATA_DIR}/Emilia_ZH_EN_pinyin/vocab.txt")
    else:
        print(f"[4/5] SKIP: No Emilia vocab at {vocab_source}")

    # Also ensure kokoro_libri_pinyin has vocab.txt
    kl_vocab = source / "kokoro_libri_pinyin" / "vocab.txt"
    if kl_vocab.exists() and not os.path.exists(f"{DATA_DIR}/kokoro_libri_pinyin/vocab.txt"):
        shutil.copy2(kl_vocab, f"{DATA_DIR}/kokoro_libri_pinyin/vocab.txt")

    # 5. Copy pretrained weights
    pretrained_source = source / "pretrained_model.safetensors"
    if pretrained_source.exists():
        print("[5/5] Copying pretrained weights...")
        shutil.copy2(pretrained_source, f"{VOLUME}/pretrained/pretrained_model.safetensors")
    else:
        print(f"[5/5] SKIP: No pretrained weights at {pretrained_source}")

    print("\nPreparation complete. Run 'verify' to check everything.")


def rewrite_csv(input_csv: str, output_csv: str):
    """Rewrite CSV audio paths to match container layout."""
    rows_written = 0
    with open(input_csv, "r") as fin, open(output_csv + ".tmp", "w", newline="") as fout:
        reader = csv.reader(fin, delimiter="|")
        writer = csv.writer(fout, delimiter="|")

        header = next(reader)
        writer.writerow(header)

        for row in reader:
            old_path = row[0].strip()
            filename = os.path.basename(old_path)
            new_path = f"{F5_ROOT}/data/kokoro_libri/{filename}"
            writer.writerow([new_path] + row[1:])
            rows_written += 1

    os.rename(output_csv + ".tmp", output_csv)
    print(f"  Rewrote {rows_written} rows with {F5_ROOT}/data/... paths")


def prepare_dataset():
    """Run F5-TTS dataset preparation with corrected paths."""
    cmd = [
        "python",
        f"{F5_ROOT}/src/f5_tts/train/datasets/prepare_csv_wavs.py",
        f"{DATA_DIR}/kokoro_libri.csv",
        f"{DATA_DIR}/kokoro_libri_pinyin",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: Dataset preparation failed:\n{result.stderr}")
        sys.exit(1)
    print(f"  Dataset prepared successfully")


def verify(args=None):
    """Verify all required files exist and paths are correct."""
    print("=== Volume Verification ===\n")

    checks = {
        "WAV files": f"{DATA_DIR}/kokoro_libri/",
        "Tokenized dataset": f"{DATA_DIR}/kokoro_libri_pinyin/raw.arrow",
        "Duration JSON": f"{DATA_DIR}/kokoro_libri_pinyin/duration.json",
        "KL vocab": f"{DATA_DIR}/kokoro_libri_pinyin/vocab.txt",
        "Emilia vocab": f"{DATA_DIR}/Emilia_ZH_EN_pinyin/vocab.txt",
        "Pretrained weights": f"{VOLUME}/pretrained/pretrained_model.safetensors",
        "Results dir": f"{VOLUME}/results/",
        "Status dir": f"{VOLUME}/status/",
    }

    all_ok = True
    for name, path in checks.items():
        if os.path.exists(path):
            if os.path.isdir(path):
                count = len(os.listdir(path))
                print(f"  OK  {name}: {path} ({count} items)")
            else:
                size_mb = os.path.getsize(path) / 1024 / 1024
                print(f"  OK  {name}: {path} ({size_mb:.1f} MB)")
        else:
            print(f"  MISSING  {name}: {path}")
            all_ok = False

    # Check WAV file count
    wav_dir = Path(f"{DATA_DIR}/kokoro_libri")
    if wav_dir.exists():
        wav_count = len(list(wav_dir.glob("*.wav")))
        txt_count = len(list(wav_dir.glob("*.txt")))
        print(f"\n  WAV files: {wav_count}")
        print(f"  TXT files: {txt_count}")

    # Verify arrow paths point to container layout
    arrow_path = f"{DATA_DIR}/kokoro_libri_pinyin/raw.arrow"
    if os.path.exists(arrow_path):
        try:
            from datasets import Dataset
            ds = Dataset.from_file(arrow_path)
            sample_path = ds[0]["audio_path"]
            if sample_path.startswith(F5_ROOT):
                print(f"\n  Arrow paths: OK (start with {F5_ROOT})")
            else:
                print(f"\n  Arrow paths: WRONG (got: {sample_path})")
                print(f"  Expected prefix: {F5_ROOT}/data/kokoro_libri/")
                all_ok = False
            print(f"  Dataset samples: {len(ds)}")
        except Exception as e:
            print(f"\n  Arrow check failed: {e}")
            all_ok = False

    print()
    if all_ok:
        print("All checks passed!")
    else:
        print("Some checks FAILED. Fix issues before running training.")

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="F5-TTS RunPod Volume Preparation")
    subparsers = parser.add_subparsers(dest="command")

    p_prepare = subparsers.add_parser("prepare", help="Prepare volume with training data")
    p_prepare.add_argument("--data-source", required=True, help="Path to source data directory")

    subparsers.add_parser("verify", help="Verify volume contents")

    args = parser.parse_args()

    if args.command == "prepare":
        prepare(args)
    elif args.command == "verify":
        verify(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
