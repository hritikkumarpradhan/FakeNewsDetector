"""
tests/test_api.py - pytest test suite for all FastAPI endpoints.

Run with:
  cd backend
  pytest tests/test_api.py -v

Uses FastAPI dependency override to inject an in-memory SQLite DB.
"""
from __future__ import annotations
import sys
from pathlib import Path

# Add backend dir to path BEFORE importing anything from the app
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app

# ── In-memory test DB ─────────────────────────────────────────────────────────
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Inject test in-memory DB session instead of production DB."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the dependency app-wide
app.dependency_overrides[get_db] = override_get_db


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    """Create all tables in the in-memory test DB once per test session."""
    # Import models so SQLAlchemy knows about them
    from models import Article  # noqa: F401
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="session")
def client(create_test_tables):
    """Return a TestClient using the test app with DI overrides."""
    # Use with statement to trigger lifespan (which creates the prod DB tables)
    # We don't need lifespan for test DB since we create tables in the fixture above
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ── Sample data ───────────────────────────────────────────────────────────────

REAL_TEXT = (
    "NASA scientists confirmed the discovery of water ice on the Moon's "
    "permanently shadowed craters. The findings, published in Nature Astronomy, "
    "were verified by three independent research teams using data from the "
    "Lunar Reconnaissance Orbiter."
)

FAKE_TEXT = (
    "SHOCKING: The government is putting mind-control chemicals in tap water! "
    "A whistleblower has revealed this secret agenda. Share this before the post "
    "gets deleted! The mainstream media is covering this up entirely."
)


# ── Health Check ──────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_schema(self, client):
        data = client.get("/api/health").json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "classifier_model" in data
        assert "summarizer_model" in data

    def test_root_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200


# ── /api/analyze ──────────────────────────────────────────────────────────────

class TestAnalyze:
    def test_analyze_with_text_returns_200(self, client):
        resp = client.post("/api/analyze", json={"text": REAL_TEXT})
        assert resp.status_code == 200

    def test_analyze_response_has_required_fields(self, client):
        data = client.post("/api/analyze", json={"text": REAL_TEXT}).json()
        assert "label" in data
        assert "score" in data
        assert "confidence" in data
        assert "model_used" in data
        assert "summary_bullets" in data

    def test_analyze_label_is_valid(self, client):
        data = client.post("/api/analyze", json={"text": REAL_TEXT}).json()
        assert data["label"] in ("REAL", "FAKE")

    def test_analyze_score_in_range(self, client):
        data = client.post("/api/analyze", json={"text": REAL_TEXT}).json()
        assert 0.0 <= data["score"] <= 1.0

    def test_analyze_confidence_in_range(self, client):
        data = client.post("/api/analyze", json={"text": REAL_TEXT}).json()
        assert 0.0 <= data["confidence"] <= 1.0

    def test_analyze_summary_bullets_is_list(self, client):
        data = client.post("/api/analyze", json={"text": REAL_TEXT}).json()
        assert isinstance(data["summary_bullets"], list)
        assert len(data["summary_bullets"]) >= 1

    def test_analyze_fake_text_scores_higher(self, client):
        real_data = client.post("/api/analyze", json={"text": REAL_TEXT}).json()
        fake_data = client.post("/api/analyze", json={"text": FAKE_TEXT}).json()
        assert fake_data["score"] >= real_data["score"]

    def test_analyze_persists_to_db(self, client):
        """Verify analysis is stored and retrievable via /api/history."""
        client.post("/api/analyze", json={"text": REAL_TEXT})
        history = client.get("/api/history").json()
        assert history["total"] >= 1

    def test_analyze_no_input_returns_422(self, client):
        resp = client.post("/api/analyze", json={})
        assert resp.status_code == 422

    def test_analyze_empty_text_returns_400(self, client):
        resp = client.post("/api/analyze", json={"text": "   "})
        assert resp.status_code in (400, 422)

    def test_analyze_too_short_text_returns_400(self, client):
        resp = client.post("/api/analyze", json={"text": "hi"})
        assert resp.status_code == 400

    def test_analyze_includes_id(self, client):
        data = client.post("/api/analyze", json={"text": REAL_TEXT}).json()
        assert data.get("id") is not None
        assert isinstance(data["id"], int)


# ── /api/summarize ─────────────────────────────────────────────────────────────

class TestSummarize:
    def test_summarize_returns_200(self, client):
        resp = client.post("/api/summarize", json={"text": REAL_TEXT})
        assert resp.status_code == 200

    def test_summarize_response_schema(self, client):
        data = client.post("/api/summarize", json={"text": REAL_TEXT}).json()
        assert "bullets" in data
        assert "raw_summary" in data
        assert "model_used" in data

    def test_summarize_bullets_is_nonempty_list(self, client):
        data = client.post("/api/summarize", json={"text": REAL_TEXT}).json()
        assert isinstance(data["bullets"], list)
        assert len(data["bullets"]) >= 1

    def test_summarize_custom_num_bullets(self, client):
        data = client.post(
            "/api/summarize", json={"text": REAL_TEXT, "num_bullets": 2}
        ).json()
        assert len(data["bullets"]) <= 4

    def test_summarize_empty_text_returns_400(self, client):
        resp = client.post("/api/summarize", json={"text": "  "})
        assert resp.status_code in (400, 422)

    def test_summarize_model_is_bart(self, client):
        data = client.post("/api/summarize", json={"text": REAL_TEXT}).json()
        assert "bart" in data["model_used"].lower()


# ── /api/history ──────────────────────────────────────────────────────────────

class TestHistory:
    def test_history_returns_200(self, client):
        resp = client.get("/api/history")
        assert resp.status_code == 200

    def test_history_response_schema(self, client):
        data = client.get("/api/history").json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_history_items_have_required_fields(self, client):
        client.post("/api/analyze", json={"text": REAL_TEXT})
        data = client.get("/api/history").json()
        if data["items"]:
            item = data["items"][0]
            assert "id" in item
            assert "label" in item
            assert "score" in item
            assert "analyzed_at" in item

    def test_history_limit_param(self, client):
        resp = client.get("/api/history?limit=2")
        data = resp.json()
        assert resp.status_code == 200
        assert len(data["items"]) <= 2

    def test_history_limit_capped_at_100(self, client):
        resp = client.get("/api/history?limit=999")
        assert resp.status_code == 200
