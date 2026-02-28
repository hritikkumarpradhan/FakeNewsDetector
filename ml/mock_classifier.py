"""
mock_classifier.py - Lightweight fake news classifier for LOCAL TESTING.

Uses zero-shot classification with a pre-trained MNLI model.
NO training required. Works immediately after installing dependencies.

This is what the FastAPI backend uses during development so you can
test all API endpoints without waiting for the full DistilBERT fine-tune.

Usage (standalone test):
  python mock_classifier.py

Returns: {"label": "FAKE"|"REAL", "score": float (0.0-1.0), "confidence": float}
"""

from __future__ import annotations
import time
from pathlib import Path
from typing import Optional

from transformers import pipeline

# ── Config ────────────────────────────────────────────────────────────────────
# This model runs zero-shot classification (no fine-tuning needed)
MOCK_MODEL = "typeform/distilbert-base-uncased-mnli"

# Labels we ask the model to choose between
CANDIDATE_LABELS = [
    "this is real, verified, credible news",
    "this is fake, misleading, or fabricated news",
]

# Path where the trained model would be saved (used if available)
BASE_DIR = Path(__file__).parent
TRAINED_MODEL_DIR = BASE_DIR / "models" / "distilbert-fakenews"

_classifier = None  # Lazy-loaded singleton


def _load_model(use_trained: bool = False):
    """Load model once and cache it."""
    global _classifier
    if _classifier is not None:
        return _classifier

    if use_trained and TRAINED_MODEL_DIR.exists():
        print(f"[i] Loading fine-tuned model from {TRAINED_MODEL_DIR}")
        from transformers import pipeline as hf_pipeline
        _classifier = hf_pipeline(
            "text-classification",
            model=str(TRAINED_MODEL_DIR),
            device=-1,  # CPU
        )
        _classifier._mode = "trained"
    else:
        if use_trained:
            print("[!] Fine-tuned model not found, falling back to mock classifier.")
        print(f"[i] Loading mock zero-shot classifier: {MOCK_MODEL}")
        _classifier = pipeline(
            "zero-shot-classification",
            model=MOCK_MODEL,
            device=-1,  # CPU
        )
        _classifier._mode = "mock"

    return _classifier


def classify(text: str, use_trained: bool = False) -> dict:
    """
    Classify article text as REAL or FAKE.

    Args:
        text: Article text or title to classify.
        use_trained: If True, attempts to load the fine-tuned DistilBERT model.

    Returns:
        {
            "label":      "REAL" or "FAKE",
            "score":      float between 0.0 and 1.0 (probability of being FAKE),
            "confidence": float between 0.0 and 1.0 (model confidence in its prediction),
            "model":      "trained" or "mock"
        }
    """
    clf = _load_model(use_trained=use_trained)
    text = text.strip()
    if not text:
        return {"label": "UNKNOWN", "score": 0.5, "confidence": 0.0, "model": "none"}

    # Truncate very long texts
    text = text[:2000]

    if hasattr(clf, "_mode") and clf._mode == "trained":
        # Fine-tuned model: direct classification
        result = clf(text, truncation=True, max_length=512)[0]
        raw_label = result["label"].upper()  # "REAL" or "FAKE"
        confidence = float(result["score"])
        score = 1.0 - confidence if raw_label == "REAL" else confidence
        label = raw_label
    else:
        # Zero-shot mock classifier
        result = clf(text, CANDIDATE_LABELS)
        top_label = result["labels"][0]
        top_score = result["scores"][0]

        if "fake" in top_label.lower():
            label = "FAKE"
            score = float(top_score)
        else:
            label = "REAL"
            score = 1.0 - float(top_score)

        confidence = float(top_score)

    return {
        "label":      label,
        "score":      round(score, 4),
        "confidence": round(confidence, 4),
        "model":      "trained" if (hasattr(clf, "_mode") and clf._mode == "trained") else "mock",
    }


# ── Standalone Test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import io
    # Only redirect stdout when running standalone (not when imported as module)
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    test_articles = [
        {
            "name": "Real News Sample",
            "text": "NASA scientists confirmed the discovery of water ice on the Moon's permanently shadowed craters. The findings, published in Nature Astronomy, were verified by three independent research teams using data from the Lunar Reconnaissance Orbiter."
        },
        {
            "name": "Fake News Sample",
            "text": "SHOCKING: The government is putting mind-control chemicals in tap water! A whistleblower has revealed this secret agenda. Share this before the post gets deleted! The mainstream media is covering this up."
        },
        {
            "name": "Ambiguous Sample",
            "text": "The new policy has generated significant controversy among experts. Some analysts believe it will help the economy while others warn of potential risks. The debate continues in government circles."
        }
    ]

    print("=" * 60)
    print("  Mock Classifier -- Smoke Test")
    print("=" * 60)
    for article in test_articles:
        print(f"\n  [{article['name']}]")
        print(f"  Text: {article['text'][:80]}...")
        t0 = time.time()
        result = classify(article["text"])
        elapsed = time.time() - t0
        print(f"  >> Label: {result['label']}  |  Fake Score: {result['score']:.2%}  |  Confidence: {result['confidence']:.2%}  ({elapsed:.2f}s)")
    print("\n[OK] Mock classifier working correctly.")
