"""
models.py - SQLAlchemy ORM models for SQLite database.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from database import Base


class Article(Base):
    """Stores each analyzed article and its result."""
    __tablename__ = "articles"

    id          = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source_url  = Column(String(2048), nullable=True, index=True)
    article_text = Column(Text, nullable=False)
    label       = Column(String(10), nullable=False)   # "REAL" or "FAKE"
    score       = Column(Float, nullable=False)         # 0.0–1.0 fake probability
    confidence  = Column(Float, nullable=False)
    model_used  = Column(String(100), nullable=False)
    summary_raw = Column(Text, nullable=True)
    summary_bullets = Column(Text, nullable=True)      # JSON-serialized list[str]
    analyzed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Article id={self.id} label={self.label} score={self.score:.2f}>"
