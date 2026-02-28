"""
database.py - SQLAlchemy + SQLite setup. Auto-creates DB on first run.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from pathlib import Path

# SQLite file lives next to this module
DB_PATH = Path(__file__).parent / "fakenews.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite + FastAPI
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def create_tables() -> None:
    """Create all tables. Called once at startup."""
    from models import Article  # noqa: F401 – import triggers table registration
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency: yields a DB session, always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
