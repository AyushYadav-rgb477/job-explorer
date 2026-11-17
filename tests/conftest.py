import pytest

from app import create_app, job_store


@pytest.fixture(autouse=True)
def no_supabase(monkeypatch):
    """Tests run against the local CSV, never a real Supabase project."""
    monkeypatch.setattr("app.load_dotenv", lambda: None)  # ignore a developer's .env
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    yield
    job_store.reset()


@pytest.fixture
def client():
    app = create_app({"TESTING": True, "TESTING_SKIP_CSRF": True, "SECRET_KEY": "test"})
    return app.test_client()
