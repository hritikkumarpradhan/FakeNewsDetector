"""
scraper.py - Extract article text from a URL.

Uses requests + BeautifulSoup (html.parser) for compatibility.
Optionally uses newspaper3k if available for higher-quality extraction.
"""
from __future__ import annotations
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 15  # seconds
MIN_TEXT_LENGTH = 100


def _scrape_with_newspaper(url: str) -> str | None:
    """Use newspaper3k for high-quality extraction (lazily imported)."""
    try:
        from newspaper import Article as NewspaperArticle
        article = NewspaperArticle(url)
        article.download()
        article.parse()
        text = article.text.strip()
        return text if len(text) >= MIN_TEXT_LENGTH else None
    except Exception:
        return None


def _scrape_with_bs4(url: str) -> str | None:
    """Fallback: BeautifulSoup paragraph extraction using html.parser."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        # Use 'html.parser' (stdlib) to avoid lxml SWIG C-extension issues
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove nav/footer/script/style noise
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()

        # Try article tag first, then main, then body
        container = soup.find("article") or soup.find("main") or soup.body
        if not container:
            return None

        paragraphs = container.find_all("p")
        text = " ".join(p.get_text(separator=" ").strip() for p in paragraphs)
        text = re.sub(r"\s+", " ", text).strip()
        return text if len(text) >= MIN_TEXT_LENGTH else None

    except Exception:
        return None


def scrape_article(url: str) -> dict:
    """
    Scrape article text from a URL.

    Returns:
        {
            "text":    str | None,
            "success": bool,
            "method":  "newspaper" | "bs4" | "none",
            "error":   str | None,
        }
    """
    # Try newspaper3k first (lazy import - won't break pytest collection)
    text = _scrape_with_newspaper(url)
    if text:
        return {"text": text, "success": True, "method": "newspaper", "error": None}

    # Fallback to BeautifulSoup
    text = _scrape_with_bs4(url)
    if text:
        return {"text": text, "success": True, "method": "bs4", "error": None}

    return {
        "text": None,
        "success": False,
        "method": "none",
        "error": "Could not extract article text from the provided URL.",
    }
