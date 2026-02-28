"""
preprocess.py — Tokenize the dataset and create train/val/test splits.

Usage:
  python preprocess.py

Reads:  ml/data/dataset.csv
Writes: ml/data/tokenized_dataset/  (HuggingFace DatasetDict on disk)

Splits: 80% train / 10% validation / 10% test
"""

import os
from pathlib import Path
import pandas as pd
from datasets import Dataset, DatasetDict, ClassLabel
from transformers import DistilBertTokenizerFast

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
INPUT_CSV = DATA_DIR / "dataset.csv"
OUTPUT_DIR = DATA_DIR / "tokenized_dataset"

MODEL_CHECKPOINT = "distilbert-base-uncased"
MAX_LENGTH = 512
SEED = 42

# ── Load tokenizer ─────────────────────────────────────────────────────────────
print(f"[i] Loading tokenizer: {MODEL_CHECKPOINT}")
tokenizer = DistilBertTokenizerFast.from_pretrained(MODEL_CHECKPOINT)


def build_input_text(row: dict) -> str:
    """Concatenate title + text for richer context."""
    title = str(row.get("title", "") or "").strip()
    text = str(row.get("text", "") or "").strip()
    if title:
        return title + " [SEP] " + text[:1000]  # Truncate body to stay within limits
    return text[:1024]


def tokenize_batch(batch):
    return tokenizer(
        batch["input_text"],
        truncation=True,
        max_length=MAX_LENGTH,
        padding="max_length",
    )


def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"Dataset not found at {INPUT_CSV}. Run ingest_data.py first."
        )

    print(f"[i] Reading {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)

    # Build combined input text
    df["input_text"] = df.apply(build_input_text, axis=1)

    # Keep only what we need
    df = df[["input_text", "label"]].dropna()
    df["label"] = df["label"].astype(int)

    print(f"[i] Total examples: {len(df):,}  |  REAL: {(df['label']==1).sum():,}  |  FAKE: {(df['label']==0).sum():,}")

    # ── Create HuggingFace Dataset ──────────────────────────────────────────────
    dataset = Dataset.from_pandas(df, preserve_index=False)

    # Cast label to ClassLabel for cleaner handling
    features = dataset.features.copy()
    features["label"] = ClassLabel(names=["FAKE", "REAL"])
    dataset = dataset.cast(features)

    # ── Split ──────────────────────────────────────────────────────────────────
    train_test = dataset.train_test_split(test_size=0.2, seed=SEED)
    val_test   = train_test["test"].train_test_split(test_size=0.5, seed=SEED)

    dataset_dict = DatasetDict({
        "train":      train_test["train"],
        "validation": val_test["train"],
        "test":       val_test["test"],
    })

    print(f"[i] Train: {len(dataset_dict['train']):,}  |  Val: {len(dataset_dict['validation']):,}  |  Test: {len(dataset_dict['test']):,}")

    # ── Tokenize ──────────────────────────────────────────────────────────────
    print("[i] Tokenizing (this may take a minute)...")
    tokenized = dataset_dict.map(
        tokenize_batch,
        batched=True,
        batch_size=64,
        remove_columns=["input_text"],
    )

    tokenized.set_format("torch", columns=["input_ids", "attention_mask", "label"])

    # ── Save ──────────────────────────────────────────────────────────────────
    print(f"[i] Saving tokenized dataset to {OUTPUT_DIR}")
    tokenized.save_to_disk(str(OUTPUT_DIR))
    print(f"[✓] Done! Load with: datasets.load_from_disk('{OUTPUT_DIR}')")


if __name__ == "__main__":
    main()
