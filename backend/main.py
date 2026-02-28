"""
main.py - FastAPI application entry point.

Endpoints:
  POST /api/analyze    - Analyze a news article (text or URL) for fake news
  POST /api/summarize  - Generate a bullet-point summary from text
  GET  /api/history    - Retrieve the last 20 analyses from SQLite
  GET  /api/health     - Health check / model status

Run with:
  uvicorn main:app --reload --port 8000

API docs at:
  http://localhost:8000/docs   (Swagger UI)
  http://localhost:8000/redoc  (ReDoc)
"""
from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import create_tables, get_db
from models import Article
from schemas import (
    AnalyzeRequest,
    AnalysisResult,
    SummarizeRequest,
    SummarizeResult,
    HistoryItem,
    HistoryResponse,
    HealthResponse,
    ErrorResponse,
)
from scraper import scrape_article
from classifier import run_classification
from summarizer_service import run_summarization

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger("fakenews.api")


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app):
    """Application startup/shutdown lifecycle."""
    logger.info("Creating database tables if needed...")
    create_tables()
    logger.info("Fake News Detector API is ready.")
    yield
    # Cleanup (if any) goes here


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Fake News Detector API",
    description=(
        "An AI-powered REST API that classifies news articles as REAL or FAKE "
        "and generates bullet-point summaries using DistilBERT and BART."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allows the Next.js frontend (localhost:3000) and Chrome Extension to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "chrome-extension://*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ── Helpers ───────────────────────────────────────────────────────────────────

def _save_to_db(
    db: Session,
    text: str,
    url: Optional[str],
    classification: dict,
    summary: dict,
) -> Article:
    """Persist analysis result to SQLite."""
    article = Article(
        source_url=url,
        article_text=text[:5000],       # Cap storage to 5K chars
        label=classification["label"],
        score=classification["score"],
        confidence=classification["confidence"],
        model_used=classification["model"],
        summary_raw=summary.get("raw_summary", ""),
        summary_bullets=json.dumps(summary.get("bullets", [])),
        analyzed_at=datetime.now(timezone.utc),
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post(
    "/api/analyze",
    response_model=AnalysisResult,
    responses={422: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Analyze a news article for fake news",
    tags=["Analysis"],
)
async def analyze(request: AnalyzeRequest, db: Session = Depends(get_db)):
    """
    Analyze a news article for credibility.

    - Provide **text** for raw text analysis.
    - Provide **url** to scrape and analyze a web article.
    - Both `text` and `url` can be provided — `url` takes priority for scraping.

    Returns a credibility score, REAL/FAKE label, and AI-generated bullet summary.
    """
    article_text: Optional[str] = None
    source_url: Optional[str] = request.url

    # ── 1. Get text ──────────────────────────────────────────────────────────
    if request.url:
        logger.info(f"Scraping URL: {request.url}")
        scrape = scrape_article(request.url)
        if not scrape["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=scrape["error"] or "Failed to scrape article from the URL.",
            )
        article_text = scrape["text"]
        logger.info(f"Scraped {len(article_text)} chars via {scrape['method']}")
    elif request.text:
        article_text = request.text.strip()
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either 'text' or 'url' in the request body.",
        )

    if not article_text or len(article_text) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Article text is too short to analyze.",
        )

    # ── 2. Classify ───────────────────────────────────────────────────────────
    logger.info("Running classification...")
    classification = run_classification(article_text)
    logger.info(f"Classification: {classification['label']} (score={classification['score']:.3f})")

    # ── 3. Summarize ──────────────────────────────────────────────────────────
    logger.info("Running summarization...")
    summary = run_summarization(article_text, num_bullets=4)
    logger.info(f"Generated {len(summary['bullets'])} summary bullets")

    # ── 4. Persist ────────────────────────────────────────────────────────────
    saved = _save_to_db(db, article_text, source_url, classification, summary)
    logger.info(f"Saved analysis id={saved.id}")

    return AnalysisResult(
        id=saved.id,
        label=classification["label"],
        score=classification["score"],
        confidence=classification["confidence"],
        model_used=classification["model"],
        summary_bullets=summary["bullets"],
        article_text=article_text[:500] + "..." if len(article_text) > 500 else article_text,
        source_url=source_url,
        analyzed_at=saved.analyzed_at.isoformat(),
    )


@app.post(
    "/api/summarize",
    response_model=SummarizeResult,
    summary="Summarize article text into bullet points",
    tags=["Summarization"],
)
async def summarize(request: SummarizeRequest):
    """
    Generate a factual bullet-point summary of article text using BART.

    Does **not** classify for fake news — use `/api/analyze` for that.
    """
    if not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text field cannot be empty.",
        )
    logger.info(f"Summarizing {len(request.text)} chars, num_bullets={request.num_bullets}")
    summary = run_summarization(request.text, num_bullets=request.num_bullets)

    return SummarizeResult(
        bullets=summary["bullets"],
        raw_summary=summary["raw_summary"],
        model_used=summary["model_used"],
    )


@app.get(
    "/api/history",
    response_model=HistoryResponse,
    summary="Get last 20 analyses",
    tags=["History"],
)
async def history(limit: int = 20, db: Session = Depends(get_db)):
    """
    Retrieve the most recent analyses stored in the database.

    Query params:
      - **limit**: number of items to return (max 100, default 20)
    """
    limit = min(limit, 100)
    rows = (
        db.query(Article)
        .order_by(Article.analyzed_at.desc())
        .limit(limit)
        .all()
    )

    items = []
    for row in rows:
        # Get first bullet for preview
        try:
            bullets = json.loads(row.summary_bullets or "[]")
            preview = bullets[0] if bullets else (row.summary_raw or "")[:120]
        except Exception:
            preview = ""

        items.append(HistoryItem(
            id=row.id,
            source_url=row.source_url,
            label=row.label,
            score=row.score,
            summary_preview=preview[:150],
            analyzed_at=row.analyzed_at.isoformat() if row.analyzed_at else "",
        ))

    return HistoryResponse(items=items, total=len(items))


@app.get(
    "/api/health",
    response_model=HealthResponse,
    summary="API health check",
    tags=["Health"],
)
async def health():
    """Returns API status and which models are loaded."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        classifier_model="distilbert-base-uncased (mock: typeform/distilbert-base-uncased-mnli)",
        summarizer_model="facebook/bart-large-cnn",
    )


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Fake News Detector API", "docs": "/docs"}
