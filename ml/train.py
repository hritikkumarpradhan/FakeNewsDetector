"""
train.py — Fine-tune DistilBERT for Fake News Detection.

Designed to run on Google Colab (GPU) or locally with a CUDA GPU.
The script is self-contained: it handles data loading, model init,
training, evaluation, and checkpoint saving.

Usage (locally with GPU):
  python train.py

Usage (Google Colab):
  1. Upload this repo to Colab or mount Google Drive
  2. Run: !python ml/train.py
  3. Best checkpoint saved to ml/models/distilbert-fakenews/

Environment variables (optional overrides):
  EPOCHS          (default: 3)
  BATCH_SIZE      (default: 16)
  LR              (default: 2e-5)
  MAX_LENGTH      (default: 512)
  OUTPUT_DIR      (default: ml/models/distilbert-fakenews)
  DATASET_DIR     (default: ml/data/tokenized_dataset)
"""

import os
import sys
from pathlib import Path

import numpy as np
import evaluate
from datasets import load_from_disk
from transformers import (
    DistilBertTokenizerFast,
    DistilBertForSequenceClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback,
    DataCollatorWithPadding,
)
import torch

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent

EPOCHS      = int(os.environ.get("EPOCHS", 3))
BATCH_SIZE  = int(os.environ.get("BATCH_SIZE", 16))
LR          = float(os.environ.get("LR", 2e-5))
MAX_LENGTH  = int(os.environ.get("MAX_LENGTH", 512))
DATASET_DIR = Path(os.environ.get("DATASET_DIR", BASE_DIR / "data" / "tokenized_dataset"))
OUTPUT_DIR  = Path(os.environ.get("OUTPUT_DIR",  BASE_DIR / "models" / "distilbert-fakenews"))
LOG_DIR     = BASE_DIR / "models" / "logs"

MODEL_CHECKPOINT = "distilbert-base-uncased"
ID2LABEL = {0: "FAKE", 1: "REAL"}
LABEL2ID = {"FAKE": 0, "REAL": 1}

# ── GPU Check ─────────────────────────────────────────────────────────────────
device = "cuda" if torch.cuda.is_available() else "cpu"
print("=" * 60)
print(f"  DistilBERT Fake News Classifier — Training Script")
print("=" * 60)
print(f"  Device  : {device.upper()}")
print(f"  Epochs  : {EPOCHS}")
print(f"  Batch   : {BATCH_SIZE}")
print(f"  LR      : {LR}")
print(f"  Max Len : {MAX_LENGTH}")
print(f"  Output  : {OUTPUT_DIR}")
print("=" * 60)

if device == "cpu":
    print()
    print("⚠️  WARNING: No GPU detected. Training on CPU will be extremely slow.")
    print("   Recommendation: Run on Google Colab (Runtime → Change runtime type → GPU)")
    print("   or Kaggle (Settings → Accelerator → GPU).")
    print()
    ans = input("   Continue on CPU anyway? [y/N]: ").strip().lower()
    if ans != "y":
        print("Exiting. Please run on a GPU-enabled environment.")
        sys.exit(0)

# ── Load Dataset ──────────────────────────────────────────────────────────────
if not DATASET_DIR.exists():
    print(f"[!] Tokenized dataset not found at {DATASET_DIR}")
    print("    Run: python ml/ingest_data.py && python ml/preprocess.py")
    sys.exit(1)

print(f"[i] Loading tokenized dataset from {DATASET_DIR}")
dataset = load_from_disk(str(DATASET_DIR))
print(f"    Train: {len(dataset['train']):,}  Val: {len(dataset['validation']):,}  Test: {len(dataset['test']):,}")

# ── Model ─────────────────────────────────────────────────────────────────────
print(f"[i] Loading model: {MODEL_CHECKPOINT}")
tokenizer = DistilBertTokenizerFast.from_pretrained(MODEL_CHECKPOINT)
model = DistilBertForSequenceClassification.from_pretrained(
    MODEL_CHECKPOINT,
    num_labels=2,
    id2label=ID2LABEL,
    label2id=LABEL2ID,
)
model.to(device)

data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

# ── Metrics ───────────────────────────────────────────────────────────────────
accuracy_metric = evaluate.load("accuracy")
f1_metric       = evaluate.load("f1")

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    acc = accuracy_metric.compute(predictions=predictions, references=labels)
    f1  = f1_metric.compute(predictions=predictions, references=labels, average="weighted")
    return {**acc, **f1}

# ── Training Arguments ────────────────────────────────────────────────────────
training_args = TrainingArguments(
    output_dir=str(OUTPUT_DIR),
    eval_strategy="epoch",
    save_strategy="epoch",
    learning_rate=LR,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE * 2,
    num_train_epochs=EPOCHS,
    weight_decay=0.01,
    load_best_model_at_end=True,
    metric_for_best_model="f1",
    logging_dir=str(LOG_DIR),
    logging_steps=50,
    fp16=(device == "cuda"),        # Mixed precision on GPU only
    report_to="none",               # Disable wandb/tensorboard by default
    push_to_hub=False,
)

# ── Trainer ───────────────────────────────────────────────────────────────────
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"],
    eval_dataset=dataset["validation"],
    tokenizer=tokenizer,
    data_collator=data_collator,
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
)

# ── Train ─────────────────────────────────────────────────────────────────────
print("\n[i] Starting training...")
trainer.train()

# ── Evaluate on Test Set ──────────────────────────────────────────────────────
print("\n[i] Evaluating on test set...")
test_results = trainer.evaluate(dataset["test"])
print("\n  Test Results:")
for k, v in test_results.items():
    print(f"    {k}: {v:.4f}" if isinstance(v, float) else f"    {k}: {v}")

# ── Save Final Model ──────────────────────────────────────────────────────────
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
trainer.save_model(str(OUTPUT_DIR))
tokenizer.save_pretrained(str(OUTPUT_DIR))
print(f"\n[✓] Model saved to {OUTPUT_DIR}")
print("    Load in backend with:")
print(f"    from transformers import pipeline")
print(f"    pipe = pipeline('text-classification', model='{OUTPUT_DIR}')")
