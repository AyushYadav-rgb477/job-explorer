"""Turns the raw Internshala scrape (data/jobs.csv) into clean job records.

The raw CSV has duplicate rows, a repeated header row, salaries like "₹ 2,00,000 - 3,00,000",
experience like "1 year(s)", perks mixed into the skills column, and multi-city locations
like "Delhi, Noida (Hybrid)". Every job record this module returns has the same shape as a
row of the Supabase `jobs` table.
"""
from __future__ import annotations

import re
from datetime import datetime

import pandas as pd

# Items Internshala lists under skills that are really perks of the job.
PERKS = {
    "informal dress code", "5 days a week", "certificate", "letter of recommendation",
    "free snacks & beverages", "job offer", "flexible work hours", "health insurance",
    "life insurance", "cab/transportation facility", "work from home", "pre-placement offer",
}

CITY_ALIASES = {"bangalore": "Bengaluru", "gurugram": "Gurgaon", "hydrabad": "Hyderabad",
                "bombay": "Mumbai", "new delhi": "Delhi", "vishakhapatnam": "Visakhapatnam"}

MISSING = {"", "not found", "not mentioned", "nan"}


def parse_salary(raw: object) -> tuple[int | None, int | None]:
    """'₹ 2,00,000 - 3,00,000' -> (200000, 300000); 'Not Mentioned' -> (None, None)."""
    numbers = [int(n) for n in re.findall(r"\d+", str(raw).replace(",", ""))]
    numbers = [n for n in numbers if n >= 1000]  # ignore stray digits such as "/month 3"
    if not numbers:
        return None, None
    return min(numbers), max(numbers)


def parse_experience(raw: object) -> int | None:
    """'1 year(s)' -> 1; 'Not Found' -> None."""
    match = re.search(r"\d+", str(raw))
    return int(match.group()) if match else None


def split_skills(raw: object) -> tuple[list[str], list[str]]:
    """Split the comma-separated skills column into (skills, perks)."""
    if str(raw).strip().lower() in MISSING:
        return [], []
    skills, perks = [], []
    for item in str(raw).split(","):
        item = item.strip()
        if not item:
            continue
        (perks if item.lower() in PERKS else skills).append(item)
    return list(dict.fromkeys(skills)), list(dict.fromkeys(perks))


def parse_cities(raw: object) -> tuple[list[str], bool]:
    """'Delhi, Bangalore (Hybrid)' -> (['Delhi', 'Bengaluru'], True)."""
    text = str(raw).strip()
    if text.lower() in MISSING:
        return [], False
    is_hybrid = "(hybrid)" in text.lower()
    text = re.sub(r"\(hybrid\)", "", text, flags=re.IGNORECASE)
    cities = []
    for part in text.split(","):
        name = re.sub(r"\(.*?\)", "", part).strip()
        if name.islower():  # "kolkata" -> "Kolkata"
            name = name.title()
        if name:
            cities.append(CITY_ALIASES.get(name.lower(), name))
    return list(dict.fromkeys(cities)), is_hybrid


def parse_timestamp(raw: object) -> str | None:
    try:
        return datetime.strptime(str(raw).strip(), "%d-%m-%Y %H:%M").isoformat()
    except ValueError:
        return None


def clean_jobs(raw: pd.DataFrame) -> list[dict]:
    """Return one clean record per unique job URL."""
    df = raw.rename(columns={"Profile Name": "title", "Company Name": "company",
                             "Skills Required": "skills", "Experience": "experience",
                             "Salary": "salary", "City": "city", "URL": "url",
                             "Timestamp": "timestamp"})
    df = df[df["title"] != "Profile Name"]                   # repeated header rows
    df = df.drop_duplicates(subset="url", keep="first")
    records = []
    for row in df.itertuples(index=False):
        salary_min, salary_max = parse_salary(row.salary)
        skills, perks = split_skills(row.skills)
        cities, is_hybrid = parse_cities(row.city)
        records.append({
            "title": str(row.title).strip(),
            "company": str(row.company).strip(),
            "experience_years": parse_experience(row.experience),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "skills": skills,
            "perks": perks,
            "cities": cities,
            "is_hybrid": is_hybrid,
            "url": str(row.url).strip(),
            "scraped_at": parse_timestamp(row.timestamp),
        })
    return records


def load_csv(path: str) -> list[dict]:
    return clean_jobs(pd.read_csv(path, encoding="utf-8"))
