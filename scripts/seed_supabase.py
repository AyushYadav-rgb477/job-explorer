"""Load data/jobs.csv into the Supabase `jobs` table.

Run once after creating the tables with supabase/schema.sql:

    python scripts/seed_supabase.py

Needs SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env. The service role key bypasses
Row Level Security, so it is only used here on your machine — never put it on Render.
Re-running is safe: rows are upserted on their URL.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.cleaning import load_csv  # noqa: E402

BATCH = 500


def main() -> None:
    load_dotenv(ROOT / ".env")
    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env first.")

    jobs = load_csv(str(ROOT / "data" / "jobs.csv"))
    client = create_client(url, key)
    for start in range(0, len(jobs), BATCH):
        client.table("jobs").upsert(jobs[start:start + BATCH], on_conflict="url").execute()
        print(f"Uploaded {min(start + BATCH, len(jobs))}/{len(jobs)} jobs")
    print("Done.")


if __name__ == "__main__":
    main()
