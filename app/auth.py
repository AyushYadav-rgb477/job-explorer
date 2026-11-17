"""Sign up, log in and log out with Supabase Auth.

Supabase stores the users and their (hashed) passwords. After a successful login the
user's access and refresh tokens are kept in Flask's signed, HTTP-only session cookie.
"""
from __future__ import annotations

from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from .supabase_client import anon_client, is_configured

bp = Blueprint("auth", __name__)

MIN_PASSWORD = 8


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            flash("Please log in to see that page.", "info")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def _error_message(exc: Exception) -> str:
    return getattr(exc, "message", None) or "Something went wrong. Please try again."


def _start_session(auth_session, user) -> None:
    session.clear()
    session.permanent = True
    session["user"] = {"id": user.id, "email": user.email}
    session["access_token"] = auth_session.access_token
    session["refresh_token"] = auth_session.refresh_token


def _safe_next(target: str | None) -> str:
    # Only allow redirects back into this site.
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("views.index")


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST" and is_configured():
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if "@" not in email:
            flash("Please enter a valid email address.", "error")
        elif len(password) < MIN_PASSWORD:
            flash(f"Password must be at least {MIN_PASSWORD} characters.", "error")
        elif password != request.form.get("confirm", ""):
            flash("Passwords don't match.", "error")
        else:
            try:
                res = anon_client().auth.sign_up({"email": email, "password": password})
            except Exception as exc:
                flash(_error_message(exc), "error")
            else:
                if res.session:  # email confirmation is turned off in Supabase
                    _start_session(res.session, res.user)
                    flash("Welcome! Your account is ready.", "success")
                    return redirect(url_for("views.index"))
                flash("Account created. Check your email for a confirmation link, then log in.",
                      "success")
                return redirect(url_for("auth.login"))
    return render_template("signup.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST" and is_configured():
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        try:
            res = anon_client().auth.sign_in_with_password({"email": email, "password": password})
        except Exception as exc:
            flash(_error_message(exc), "error")
        else:
            _start_session(res.session, res.user)
            flash("Logged in.", "success")
            return redirect(_safe_next(request.args.get("next")))
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("views.index"))
