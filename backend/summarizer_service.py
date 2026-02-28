"""
summarizer_service.py - Wraps the ML BART summarizer for use in the API.
"""
from __future__ import annotations
import sys
from pathlib import Path

# Allow importing from the sibling ml/ directory
ML_DIR = Path(__file__).parent.parent / "ml"
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from summarizer import summarize  # noqa: E402


def run_summarization(text: str, num_bullets: int = 4) -> dict:
    """
    Run BART summarization on article text.

    Returns:
        {
            "bullets":     list[str],
            "raw_summary": str,
            "model_used":  str,
        }
    """
    result = summarize(text, num_bullets=num_bullets)
    return {
        "bullets":     result["bullets"],
        "raw_summary": result["raw"],
        "model_used":  result["model"],
    }
