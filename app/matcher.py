"""Rank jobs against a CV.

Each job gets two scores, combined 50/50:
- text similarity: TF-IDF cosine similarity between the CV and the job's title + skills
  (skills are repeated so they weigh more than the title);
- skill coverage: the share of the job's listed skills that appear in the CV.

Skill coverage also tells the user which of a job's skills they have and which they lack.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from threading import Lock

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

TEXT_WEIGHT = 0.5
SKILL_WEIGHT = 0.5


def _skill_pattern(skill: str) -> re.Pattern:
    # Skills like "C++", "MS-Excel" or "Node.js" aren't plain words, so \b won't do.
    return re.compile(rf"(?<![\w+#.]){re.escape(skill.lower())}(?![\w+#])")


@dataclass
class _Index:
    vectorizer: TfidfVectorizer
    matrix: object
    skill_patterns: dict[str, re.Pattern]


_index: _Index | None = None
_indexed_df_id: int | None = None
_lock = Lock()


def _build_index(jobs: pd.DataFrame) -> _Index:
    docs = [f"{row.title} " + " ".join(row.skills) * 3 for row in jobs.itertuples()]
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
    matrix = vectorizer.fit_transform(docs)
    all_skills = {s for skills in jobs["skills"] for s in skills if len(s) > 1}
    return _Index(vectorizer, matrix, {s: _skill_pattern(s) for s in all_skills})


def _get_index(jobs: pd.DataFrame) -> _Index:
    global _index, _indexed_df_id
    with _lock:
        if _index is None or _indexed_df_id != id(jobs):
            _index, _indexed_df_id = _build_index(jobs), id(jobs)
        return _index


def skills_in_text(text: str, jobs: pd.DataFrame) -> list[str]:
    """Every known job skill that is mentioned in the text."""
    lowered = text.lower()
    found = [s for s, pattern in _get_index(jobs).skill_patterns.items() if pattern.search(lowered)]
    return sorted(found, key=str.lower)


def match(cv_text: str, jobs: pd.DataFrame, limit: int = 10) -> tuple[list[str], list[dict]]:
    """Return (skills found in the CV, best `limit` jobs with scores)."""
    index = _get_index(jobs)
    cv_skills = skills_in_text(cv_text, jobs)
    cv_skill_set = {s.lower() for s in cv_skills}

    text_scores = linear_kernel(index.vectorizer.transform([cv_text]), index.matrix).ravel()

    scored = []
    for i, row in enumerate(jobs.itertuples()):
        job_skills = [s for s in row.skills if len(s) > 1]
        have = [s for s in job_skills if s.lower() in cv_skill_set]
        coverage = len(have) / len(job_skills) if job_skills else 0.0
        score = TEXT_WEIGHT * text_scores[i] + SKILL_WEIGHT * coverage
        if score > 0:
            scored.append((score, i, have, [s for s in job_skills if s.lower() not in cv_skill_set]))
    scored.sort(key=lambda t: t[0], reverse=True)

    results, seen = [], set()
    for score, i, have, missing in scored:
        job = jobs.iloc[i]
        key = (job["title"].lower(), job["company"].lower())
        if key in seen:  # same role re-posted for several cities
            continue
        seen.add(key)
        results.append({
            "id": int(job["id"]),
            "title": job["title"],
            "company": job["company"],
            "cities": list(job["cities"]),
            "is_hybrid": bool(job["is_hybrid"]),
            "salary_min": None if pd.isna(job["salary_min"]) else int(job["salary_min"]),
            "salary_max": None if pd.isna(job["salary_max"]) else int(job["salary_max"]),
            "url": job["url"],
            "score": round(float(score) * 100, 1),
            "matched_skills": have,
            "missing_skills": missing,
        })
        if len(results) == limit:
            break
    return cv_skills, results
