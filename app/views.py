"""Pages and JSON endpoints: CV matching, job search, insights and match history."""
from __future__ import annotations

import logging
import math
from threading import Lock

import pandas as pd
from flask import (Blueprint, flash, jsonify, redirect, render_template, request,
                   session, url_for)

from . import insights, job_store, matcher
from .auth import login_required
from .cv_parser import CVError, extract_text
from .supabase_client import user_client

log = logging.getLogger(__name__)
bp = Blueprint("views", __name__)

PER_PAGE = 20
_insights_cache: dict | None = None
_insights_lock = Lock()


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/api/match", methods=["POST"])
def api_match():
    upload = request.files.get("cv")
    if not upload or not upload.filename:
        return jsonify(error="Please choose a CV file."), 400
    try:
        cv_text = extract_text(upload.filename, upload.read())
    except CVError as exc:
        return jsonify(error=str(exc)), 400

    jobs = job_store.jobs()
    cv_skills, matches = matcher.match(cv_text, jobs)

    saved = False
    if session.get("user") and matches:
        try:
            user_client(session).table("match_history").insert({
                "cv_name": upload.filename[:200],
                "cv_skills": cv_skills,
                "matches": matches,
            }).execute()
            saved = True
        except Exception:
            log.exception("Could not save match history")
    return jsonify(cv_skills=cv_skills, matches=matches, saved=saved)


@bp.route("/jobs")
def jobs_page():
    df = job_store.jobs()
    q = request.args.get("q", "").strip()
    city = request.args.get("city", "").strip()
    skill = request.args.get("skill", "").strip()
    min_salary = request.args.get("min_salary", type=int)
    page = max(request.args.get("page", 1, type=int), 1)

    filtered = df
    if q:
        text = filtered["title"] + " " + filtered["company"]
        filtered = filtered[text.str.contains(q, case=False, regex=False)]
    if city:
        filtered = filtered[filtered["cities"].apply(lambda cs: city in cs)]
    if skill:
        s = skill.lower()
        filtered = filtered[filtered["skills"].apply(lambda ks: any(k.lower() == s for k in ks))]
    if min_salary:
        filtered = filtered[filtered["salary_max"].fillna(0) >= min_salary]

    total = len(filtered)
    pages = max(math.ceil(total / PER_PAGE), 1)
    page = min(page, pages)
    rows = filtered.iloc[(page - 1) * PER_PAGE: page * PER_PAGE].to_dict("records")
    for row in rows:  # pandas' NA isn't usable in templates
        for col in ("experience_years", "salary_min", "salary_max"):
            row[col] = None if pd.isna(row[col]) else int(row[col])

    stats = _insights()
    return render_template(
        "jobs.html", jobs=rows, total=total, page=page, pages=pages,
        filters={"q": q, "city": city, "skill": skill, "min_salary": min_salary or ""},
        cities=stats["top_cities"]["labels"], skills=stats["top_skills"]["labels"],
    )


def _insights() -> dict:
    global _insights_cache
    with _insights_lock:
        if _insights_cache is None:
            _insights_cache = insights.compute(job_store.jobs())
        return _insights_cache


@bp.route("/insights")
def insights_page():
    return render_template("insights.html", totals=_insights()["totals"])


@bp.route("/api/insights")
def api_insights():
    return jsonify(_insights())


@bp.route("/history")
@login_required
def history():
    try:
        rows = (user_client(session).table("match_history")
                .select("id, cv_name, cv_skills, matches, created_at")
                .order("created_at", desc=True).limit(50).execute().data)
    except Exception:
        log.exception("Could not load match history")
        flash("Couldn't load your history right now. Please log in again.", "error")
        rows = []
    return render_template("history.html", entries=rows)


@bp.route("/history/<uuid:entry_id>/delete", methods=["POST"])
@login_required
def delete_history(entry_id):
    try:
        user_client(session).table("match_history").delete().eq("id", str(entry_id)).execute()
        flash("Deleted.", "info")
    except Exception:
        log.exception("Could not delete history entry")
        flash("Couldn't delete that entry.", "error")
    return redirect(url_for("views.history"))


@bp.route("/healthz")
def healthz():
    return {"status": "ok", "jobs": len(job_store.jobs())}


@bp.app_errorhandler(413)
def too_large(_):
    return jsonify(error="That file is too big. The limit is 5 MB."), 413


@bp.app_errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, message="Page not found."), 404


@bp.app_errorhandler(400)
def bad_request(err):
    if request.path.startswith("/api/"):
        return jsonify(error=err.description), 400
    return render_template("error.html", code=400, message=err.description), 400


@bp.app_errorhandler(500)
def server_error(_):
    return render_template("error.html", code=500, message="Something went wrong."), 500
