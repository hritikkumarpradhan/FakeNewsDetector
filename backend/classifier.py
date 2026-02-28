"""
classifier.py - Wraps the ML mock/trained classifier for use in the API.

Sys.path is extended so we can import from ml/ without packaging.
"""
from __future__ import annotations
import sys
from pathlib import Path

# Allow importing from the sibling ml/ directory
ML_DIR = Path(__file__).parent.parent / "ml"
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from mock_classifier import classify  # noqa: E402


def run_classification(text: str) -> dict:
    """
    Run fake news classification on text.

    Returns:
        {
            "label":      "REAL" | "FAKE",
            "score":      float,   # 0.0-1.0, probability of being FAKE
            "confidence": float,
            "model":      str,
        }
    """
    use_trained = (ML_DIR / "models" / "distilbert-fakenews").exists()
    return classify(text, use_trained=use_trained)
