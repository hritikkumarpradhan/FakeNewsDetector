"""
summarizer.py - Generate bullet-point summaries using BART.

Model: facebook/bart-large-cnn (pre-trained, no fine-tuning needed)
This file is used by both the ML layer and the FastAPI backend.

Usage (standalone):
  python summarizer.py

Returns a list of bullet-point strings.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Optional

from transformers import pipeline

# ── Config ────────────────────────────────────────────────────────────────────
SUMMARIZER_MODEL = "facebook/bart-large-cnn"

MIN_SUMMARY_LENGTH = 60
MAX_SUMMARY_LENGTH = 180  # Per BART call
NUM_BULLETS = 4
MAX_INPUT_CHARS = 3500

_summarizer = None  # Lazy-loaded singleton


def _load_model():
    global _summarizer
    if _summarizer is None:
        print(f"[i] Loading summarizer: {SUMMARIZER_MODEL} (first load may take a moment...)")
        _summarizer = pipeline(
            "summarization",
            model=SUMMARIZER_MODEL,
            device=-1,  # CPU; change to 0 for GPU
        )
        print("[OK] Summarizer ready.")
    return _summarizer


def _split_into_chunks(text: str, chunk_size: int = MAX_INPUT_CHARS) -> list[str]:
    """Split long text into processable chunks."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current = [], ""
    for sent in sentences:
        if len(current) + len(sent) < chunk_size:
            current += " " + sent
        else:
            if current.strip():
                chunks.append(current.strip())
            current = sent
    if current.strip():
        chunks.append(current.strip())
    return chunks or [text[:chunk_size]]


def _raw_summary(text: str) -> str:
    """Generate a raw BART summary from text."""
    summ = _load_model()
    text = text.strip()

    if not text:
        return ""

    if len(text) < 200:
        return text

    chunks = _split_into_chunks(text)
    summaries = []
    for chunk in chunks[:3]:
        result = summ(
            chunk,
            max_length=MAX_SUMMARY_LENGTH,
            min_length=MIN_SUMMARY_LENGTH,
            do_sample=False,
            truncation=True,
        )
        summaries.append(result[0]["summary_text"])

    return " ".join(summaries)


def _to_bullets(summary_text: str, n: int = NUM_BULLETS) -> list[str]:
    """Convert a paragraph summary into bullet points."""
    sentences = re.split(r'(?<=[.!?])\s+', summary_text.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    if not sentences:
        return [summary_text.strip()]

    bullets = sentences[:n]
    bullets = [b if b.endswith(('.', '!', '?')) else b + '.' for b in bullets]
    return bullets


def summarize(text: str, num_bullets: int = NUM_BULLETS) -> dict:
    """
    Summarize article text into bullet points.

    Args:
        text:        The article body text.
        num_bullets: Number of bullet points to return.

    Returns:
        {
            "bullets":  list[str],
            "raw":      str,
            "model":    str,
        }
    """
    if not text or not text.strip():
        return {
            "bullets": ["No content available to summarize."],
            "raw":     "",
            "model":   SUMMARIZER_MODEL,
        }

    raw = _raw_summary(text)
    bullets = _to_bullets(raw, n=num_bullets)

    return {
        "bullets": bullets,
        "raw":     raw,
        "model":   SUMMARIZER_MODEL,
    }


# ── Standalone Test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    sample_article = """
    Scientists at NASA's Jet Propulsion Laboratory have announced a significant breakthrough
    in quantum computing that could revolutionize space exploration. The new quantum processor,
    developed over five years, can perform calculations 1,000 times faster than current
    supercomputers. The technology uses superconducting qubits cooled to near absolute zero.
    Researchers believe this could enable real-time trajectory calculations for deep-space missions,
    dramatically reducing travel time to Mars and beyond. The breakthrough was independently
    verified by teams at MIT and Stanford. The research was published in Nature on February 27,
    2026. NASA plans to integrate the technology into its Artemis lunar program by 2028.
    The quantum processor is the size of a thumbnail, making it ideal for spacecraft deployment.
    Dr. Sarah Chen, lead researcher, called it 'the most exciting development in space computing
    since the digital computer itself.' The system is expected to enter testing phase next year.
    """

    print("=" * 60)
    print("  BART Summarizer -- Smoke Test")
    print("=" * 60)
    print(f"\n  Input ({len(sample_article)} chars):")
    print(f"  {sample_article[:100].strip()}...")

    result = summarize(sample_article)

    print(f"\n  Summary ({SUMMARIZER_MODEL}):")
    for i, bullet in enumerate(result["bullets"], 1):
        print(f"  {i}. {bullet}")

    print(f"\n  Raw: {result['raw'][:200]}...")
    print("\n[OK] Summarizer working correctly.")
