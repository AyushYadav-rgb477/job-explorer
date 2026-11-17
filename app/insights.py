"""Job-market statistics for the Insights dashboard, all computed from the jobs DataFrame."""
from __future__ import annotations

from collections import Counter
from itertools import combinations

import pandas as pd


def _top(counter: Counter, n: int) -> dict:
    items = counter.most_common(n)
    return {"labels": [k for k, _ in items], "values": [v for _, v in items]}


def compute(jobs: pd.DataFrame) -> dict:
    skill_lists = [list(dict.fromkeys(s)) for s in jobs["skills"]]
    skill_counts = Counter(s for skills in skill_lists for s in skills)
    pair_counts = Counter(
        pair for skills in skill_lists for pair in combinations(sorted(skills), 2)
    )

    paid = jobs.dropna(subset=["salary_min", "salary_max"]).copy()
    paid["salary_mid"] = (paid["salary_min"] + paid["salary_max"]) / 2

    by_exp = (paid.dropna(subset=["experience_years"])
              .groupby("experience_years")["salary_mid"]
              .agg(["median", "count"]))
    by_exp = by_exp[by_exp["count"] >= 5]  # too few listings to say anything

    bands = [0, 200_000, 300_000, 400_000, 500_000, 700_000, 1_000_000, float("inf")]
    band_labels = ["< 2 L", "2–3 L", "3–4 L", "4–5 L", "5–7 L", "7–10 L", "10 L+"]
    band_counts = pd.cut(paid["salary_mid"], bands, labels=band_labels, right=False).value_counts()

    top_paying = (paid.groupby("title")["salary_mid"].agg(["median", "count"])
                  .query("count >= 5").sort_values("median", ascending=False).head(10))

    return {
        "totals": {
            "jobs": int(len(jobs)),
            "companies": int(jobs["company"].nunique()),
            "cities": len({c for cities in jobs["cities"] for c in cities}),
            "skills": len(skill_counts),
            "with_salary_pct": round(100 * len(paid) / max(len(jobs), 1)),
            "median_salary": int(paid["salary_mid"].median()) if len(paid) else None,
            "hybrid_pct": round(100 * jobs["is_hybrid"].mean()) if len(jobs) else 0,
        },
        "top_skills": _top(skill_counts, 15),
        "top_companies": _top(Counter(jobs["company"]), 10),
        "top_cities": _top(Counter(c for cities in jobs["cities"] for c in cities), 12),
        "top_titles": _top(Counter(jobs["title"]), 10),
        "skill_pairs": [
            {"a": a, "b": b, "count": n} for (a, b), n in pair_counts.most_common(12)
        ],
        "salary_by_experience": {
            "labels": [f"{int(y)} yr" for y in by_exp.index],
            "values": [int(v) for v in by_exp["median"]],
        },
        "salary_bands": {
            "labels": band_labels,
            "values": [int(band_counts.get(label, 0)) for label in band_labels],
        },
        "top_paying_titles": {
            "labels": list(top_paying.index),
            "values": [int(v) for v in top_paying["median"]],
        },
    }
