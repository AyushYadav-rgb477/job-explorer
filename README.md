# Job Explorer

Upload your CV and get the jobs that fit it best, out of ~5,700 real listings scraped from
Internshala. For every match you see which of the job's skills you already have and which
you still need to learn. An Insights dashboard shows what the job market wants: top skills,
cities, companies, salaries by experience, and skills that are asked for together.

**Live demo:** _add your Render URL here_

## Features

- **CV matching**: PDF/DOCX CVs are parsed in memory (never stored). Jobs are ranked by a
  hybrid score: 50% TF-IDF cosine similarity (scikit-learn) + 50% coverage of the job's
  required skills.
- **Skill-gap analysis**: for each match, the skills you have and the ones to learn.
- **Job search**: filter listings by title/company, city, skill and minimum salary.
- **Insights dashboard**: Chart.js charts built from the cleaned data.
- **Accounts and history**: sign-up/log-in with Supabase Auth. Signed-in users' matches are
  saved to Postgres, and Row Level Security keeps each user's history private.
- **Data cleaning**: the raw scrape had 3,700+ duplicate rows, perks mixed into skills
  ("Informal dress code"), salary strings like `₹ 2,00,000 - 3,00,000` and multi-city
  locations. `app/cleaning.py` turns it into typed records.

## Tech stack

Python · Flask · pandas · scikit-learn · Supabase (Postgres + Auth + RLS) · Chart.js ·
Gunicorn · Render · pytest

## Project layout

```
app/
  cleaning.py         raw CSV -> clean job records
  job_store.py        loads jobs from Supabase (or the local CSV when Supabase isn't set up)
  matcher.py          TF-IDF + skill-coverage ranking
  cv_parser.py        PDF/DOCX text extraction
  insights.py         dashboard statistics
  auth.py, views.py   routes
  templates/, static/ UI
supabase/schema.sql   tables + Row Level Security policies
scripts/seed_supabase.py  uploads data/jobs.csv to Supabase
tests/                pytest suite
```

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
python wsgi.py                  # http://127.0.0.1:5000
pytest
```

Without a `.env` file the app reads `data/jobs.csv` directly and accounts are turned off.

## Set up Supabase

1. Create a free project at [supabase.com](https://supabase.com).
2. **SQL Editor → New query**: paste `supabase/schema.sql` and run it.
3. Copy `.env.example` to `.env` and fill in `SUPABASE_URL`, `SUPABASE_ANON_KEY` and
   `SUPABASE_SERVICE_ROLE_KEY` from **Project Settings → API Keys** and **Data API**.
4. Load the jobs: `python scripts/seed_supabase.py`.
5. **Authentication → URL Configuration**: set *Site URL* to your Render URL so the
   confirmation emails link back to your site.

## Deploy on Render

1. Click [**Deploy to Render**](https://render.com/deploy?repo=https://github.com/AyushYadav-rgb477/job-explorer)
   (or on [render.com](https://render.com) choose **New → Blueprint** and pick this
   repository). Render reads `render.yaml`.
2. When asked, enter `SUPABASE_URL` and `SUPABASE_ANON_KEY` (never the service role key).
3. Every push to `main` redeploys automatically.

The free plan sleeps after 15 minutes without traffic, so the first visit after that takes
about a minute.
