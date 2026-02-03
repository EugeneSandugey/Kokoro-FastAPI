#!/usr/bin/env python3
"""Download Gemini Flash 2.0 Speech dataset to NAS."""
import time
import os

# Use HF cache on NAS to avoid filling local disk
os.environ["HF_DATASETS_CACHE"] = "/mnt/p/AI-Training-Data/.hf_cache"

from datasets import load_dataset

OUTPUT_DIR = "/mnt/p/AI-Training-Data/gemini-flash-2.0-speech"

print(f"Downloading Gemini Flash 2.0 Speech dataset...")
print(f"Output: {OUTPUT_DIR}")
print(f"HF cache: {os.environ['HF_DATASETS_CACHE']}")
print()

start = time.time()
ds = load_dataset("shb777/gemini-flash-2.0-speech", split="train")
elapsed = time.time() - start
print(f"\nDataset loaded in {elapsed:.0f}s ({elapsed/60:.1f} min)")
print(f"Rows: {len(ds)}")
print(f"Columns: {ds.column_names}")

# Save to disk in arrow format (fast, queryable)
print(f"\nSaving to {OUTPUT_DIR}...")
start2 = time.time()
ds.save_to_disk(OUTPUT_DIR)
elapsed2 = time.time() - start2
print(f"Saved in {elapsed2:.0f}s ({elapsed2/60:.1f} min)")

total = time.time() - start
print(f"\nTotal time: {total:.0f}s ({total/60:.1f} min)")
print(f"Done! Dataset at: {OUTPUT_DIR}")
