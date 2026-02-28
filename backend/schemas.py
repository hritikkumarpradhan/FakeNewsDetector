"""
schemas.py - Pydantic request/response models for the API.
"""
from __future__ import annotations
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ── Request Models ────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    text: Optional[str] = Field(None, description="Raw article text to analyze")
    url: Optional[str] = Field(None, description="URL of article to scrape and analyze")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"text": "NASA confirms water ice on Moon. The findings were verified by three independent teams."},
                {"url": "https://www.bbc.com/news/science-environment-12345678"},
            ]
        }
    }


class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=20, description="Article text to summarize")
    num_bullets: int = Field(4, ge=1, le=8, description="Number of bullet points")


# ── Response Models ───────────────────────────────────────────────────────────

class AnalysisResult(BaseModel):
    id: Optional[int] = None
    label: str = Field(..., description="'REAL' or 'FAKE'")
    score: float = Field(..., ge=0.0, le=1.0, description="Probability the article is FAKE (0=real, 1=fake)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence in its prediction")
    model_used: str = Field(..., description="Which model produced this result")
    summary_bullets: list[str] = Field(default_factory=list, description="AI-generated bullet point summary")
    article_text: Optional[str] = Field(None, description="Extracted article text (truncated)")
    source_url: Optional[str] = Field(None, description="Source URL if provided")
    analyzed_at: Optional[str] = None


class SummarizeResult(BaseModel):
    bullets: list[str] = Field(..., description="Bullet-point summary sentences")
    raw_summary: str = Field(..., description="Raw paragraph summary")
    model_used: str


class HistoryItem(BaseModel):
    id: int
    source_url: Optional[str]
    label: str
    score: float
    summary_preview: str
    analyzed_at: str


class HistoryResponse(BaseModel):
    items: list[HistoryItem]
    total: int


class HealthResponse(BaseModel):
    status: str
    version: str
    classifier_model: str
    summarizer_model: str


class ErrorResponse(BaseModel):
    detail: str
