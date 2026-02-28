"""
ingest_data.py — Download & prepare the ISOT Fake News Dataset.

The ISOT dataset contains two CSV files:
  - True.csv  (real news articles)
  - Fake.csv  (fake news articles)

Usage:
  python ingest_data.py

Downloads from a public mirror or prompts for Kaggle credentials.
Outputs: ml/data/dataset.csv  (columns: title, text, label)
         label: 1 = REAL, 0 = FAKE
"""

import os
import sys
import urllib.request
import zipfile
import pandas as pd
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = DATA_DIR / "dataset.csv"

# ── Public mirror for ISOT dataset ────────────────────────────────────────────
# If the mirror is unavailable, we fall back to a small synthetic sample
# so the rest of the pipeline can still run for development purposes.
ISOT_KAGGLE_DATASET = "clmentbisaillon/fake-and-real-news-dataset"

# ── Helpers ───────────────────────────────────────────────────────────────────

def try_kaggle_download() -> bool:
    """Attempts to download via kaggle CLI. Returns True on success."""
    try:
        import subprocess
        result = subprocess.run(
            ["kaggle", "datasets", "download", "-d", ISOT_KAGGLE_DATASET, "-p", str(DATA_DIR), "--unzip"],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            print("[✓] Kaggle download successful.")
            return True
        else:
            print(f"[!] Kaggle CLI error: {result.stderr.strip()}")
            return False
    except (FileNotFoundError, Exception) as e:
        print(f"[!] Kaggle CLI not available: {e}")
        return False


def create_synthetic_sample() -> None:
    """Creates a small synthetic dataset for development/CI testing."""
    print("[i] Creating synthetic sample dataset (for dev/testing)...")
    samples = [
        {"title": "Scientists discover new planet in solar system", "text": "NASA researchers have confirmed the discovery of a new celestial body beyond Neptune, exhibiting orbital characteristics consistent with a planet. The findings were published in the Astrophysical Journal and peer-reviewed by three independent institutions.", "label": 1},
        {"title": "Government releases annual budget report", "text": "The treasury department released its annual budget summary showing a 3% increase in infrastructure spending. The report was reviewed by the congressional budget office and reflects verified fiscal year data.", "label": 1},
        {"title": "Local school wins national robotics competition", "text": "Students from Lincoln High School claimed first place at the national FIRST Robotics Championship held in Houston, Texas. The team of 12 students spent six weeks building their robot.", "label": 1},
        {"title": "New health guidelines recommend 8 glasses of water daily", "text": "The World Health Organization updated its hydration guidelines following a multi-year study involving 50,000 participants across 30 countries. The recommendation aligns with existing nutritional science.", "label": 1},
        {"title": "SHOCKING: Famous celebrity secretly controls the government", "text": "Anonymous sources reveal that a well-known Hollywood actor has been pulling strings at the highest levels of government for decades. Share this before it gets deleted! The mainstream media is hiding this truth from you.", "label": 0},
        {"title": "BREAKING: Drinking coffee cures cancer, doctors HATE this", "text": "A miracle cure has been discovered and big pharma is suppressing it! Simply drinking 3 cups of special coffee every morning will eliminate all forms of cancer. The government does NOT want you to know this secret!", "label": 0},
        {"title": "Millions of illegal ballots found in election, sources say", "text": "Unverified sources claim that millions of fraudulent ballots were discovered in a warehouse. No evidence has been provided and election officials have denied any irregularities. Share this VIRAL post now!", "label": 0},
        {"title": "Scientists paid by elite to hide flat earth truth", "text": "Whistleblowers inside NASA have come forward to reveal that the earth is indeed flat and all globe images are CGI. The curvature of the earth is a conspiracy maintained by the global elite to control the population.", "label": 0},
    ]
    # Expand to ~400 rows by repeating with slight variation
    expanded = []
    for i in range(50):
        for s in samples:
            expanded.append({
                "title": s["title"] + (f" (report {i})" if i > 0 else ""),
                "text": s["text"],
                "label": s["label"]
            })
    df = pd.DataFrame(expanded)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"[✓] Synthetic dataset saved → {OUTPUT_CSV}  ({len(df)} rows)")


def load_isot_csvs() -> bool:
    """Loads True.csv and Fake.csv from DATA_DIR and merges them."""
    true_path = DATA_DIR / "True.csv"
    fake_path = DATA_DIR / "Fake.csv"

    if not true_path.exists() or not fake_path.exists():
        return False

    print("[i] Loading ISOT CSV files...")
    df_true = pd.read_csv(true_path)
    df_fake = pd.read_csv(fake_path)

    df_true["label"] = 1  # REAL
    df_fake["label"] = 0  # FAKE

    df = pd.concat([df_true, df_fake], ignore_index=True)

    # Keep only relevant columns
    cols = [c for c in ["title", "text", "subject", "date"] if c in df.columns]
    df = df[cols + ["label"]]

    # Drop rows with missing text
    df.dropna(subset=["text"], inplace=True)
    df["text"] = df["text"].str.strip()
    df = df[df["text"].str.len() > 20]

    # Shuffle
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"[✓] ISOT dataset saved → {OUTPUT_CSV}")
    print(f"    REAL: {(df['label'] == 1).sum():,}  |  FAKE: {(df['label'] == 0).sum():,}  |  Total: {len(df):,}")
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if OUTPUT_CSV.exists():
        print(f"[i] Dataset already exists at {OUTPUT_CSV}. Delete it to re-download.")
        return

    print("=" * 60)
    print("  ISOT Fake News Dataset — Ingestion Script")
    print("=" * 60)

    # Step 1: Try Kaggle
    if try_kaggle_download():
        if load_isot_csvs():
            return

    # Step 2: Try loading if CSVs are already present (manual download)
    if load_isot_csvs():
        return

    # Step 3: Fall back to synthetic sample
    print("[!] Could not download ISOT dataset automatically.")
    print("    To use the full dataset, either:")
    print("    1. Install kaggle CLI: pip install kaggle")
    print("       Set up ~/.kaggle/kaggle.json with your API key")
    print("       Then re-run this script.")
    print("    2. Download manually from:")
    print("       https://www.kaggle.com/datasets/clmentbisaillon/fake-and-real-news-dataset")
    print("       Place True.csv and Fake.csv in ml/data/")
    print()
    print("[i] Falling back to synthetic sample dataset for development...")
    create_synthetic_sample()


if __name__ == "__main__":
    main()
