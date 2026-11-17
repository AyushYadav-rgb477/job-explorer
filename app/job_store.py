"""Where the app gets its jobs from.

In production the jobs live in the Supabase `jobs` table. When Supabase isn't configured
(local development, tests) the store falls back to cleaning data/jobs.csv directly, so the
app always has the same records either way. Jobs are loaded once and kept in memory: the
whole table is a few thousand rows, and matching needs all of them at once anyway.
"""
from __future__ import annotations

import logging
from pathlib import Path
from threading import Lock

import pandas as pd

from .cleaning import load_csv
from .supabase_client import anon_client, is_configured

log = logging.getLogger(__name__)

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "jobs.csv"
PAGE = 1000  # Supabase returns at most 1000 rows per request

_jobs: pd.DataFrame | None = None
_lock = Lock()


def _fetch_from_supabase() -> list[dict]:
    client = anon_client()
    rows, start = [], 0
    while True:
        batch = (client.table("jobs").select("*").order("id")
                 .range(start, start + PAGE - 1).execute().data)
        rows.extend(batch)
        if len(batch) < PAGE:
            return rows
        start += PAGE


def jobs() -> pd.DataFrame:
    """All jobs as a DataFrame with one row per job (columns as in the `jobs` table)."""
    global _jobs
    with _lock:
        if _jobs is None:
            if is_configured():
                records, source = _fetch_from_supabase(), "Supabase"
            else:
                records, source = load_csv(str(CSV_PATH)), "local CSV"
            df = pd.DataFrame.from_records(records)
            if "id" not in df:
                df.insert(0, "id", range(1, len(df) + 1))
            for col in ("experience_years", "salary_min", "salary_max"):
                df[col] = df[col].astype("Int64")
            _jobs = df.reset_index(drop=True)
            log.info("Loaded %d jobs from %s", len(_jobs), source)
        return _jobs


def reset() -> None:
    """Forget loaded jobs (used by tests)."""
    global _jobs
    with _lock:
        _jobs = None
