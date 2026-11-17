"""Job Explorer: match a CV against Internshala job listings and explore the job market."""
from __future__ import annotations

import logging
import os
import secrets
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, abort, request, session

MAX_UPLOAD_MB = 5


def create_app(config: dict | None = None) -> Flask:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY") or secrets.token_hex(32),
        MAX_CONTENT_LENGTH=MAX_UPLOAD_MB * 1024 * 1024,
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("RENDER") is not None,  # Render serves over HTTPS
    )
    if config:
        app.config.update(config)

    _setup_csrf(app)
    app.jinja_env.filters["lakh"] = format_lakh

    from .auth import bp as auth_bp
    from .views import bp as views_bp

    app.register_blueprint(views_bp)
    app.register_blueprint(auth_bp)

    @app.context_processor
    def inject_globals():
        from .supabase_client import is_configured
        return {"current_user": session.get("user"), "accounts_enabled": is_configured(),
                "max_upload_mb": MAX_UPLOAD_MB}

    return app


def format_lakh(rupees) -> str:
    """200000 -> '₹2 L', 245000 -> '₹2.45 L' (Indian lakh = 100,000)."""
    import pandas as pd
    if rupees is None or pd.isna(rupees):
        return ""
    value = f"{int(rupees) / 100_000:.2f}".rstrip("0").rstrip(".")
    return f"₹{value} L"


def _setup_csrf(app: Flask) -> None:
    """Minimal CSRF protection: every POST must carry the token stored in the session."""

    def csrf_token() -> str:
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return session["csrf_token"]

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def check_csrf():
        if request.method != "POST" or app.config.get("TESTING_SKIP_CSRF"):
            return
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        expected = session.get("csrf_token")
        if not sent or not expected or not secrets.compare_digest(sent, expected):
            abort(400, "Your session expired. Please reload the page and try again.")
