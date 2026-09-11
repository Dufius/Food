"""Builds the enriched, consumer-facing view over the v0.13 snapshot.

Wraps each FoodScore with its Verdict (tier + flags + advice + rationale,
see verdict.py) and indexes everything by slug for the product detail page.
Kept separate from main.py so the enrichment logic has its own tests
independent of the HTTP layer.
"""
from __future__ import annotations

from dataclasses import dataclass

from .data import FoodScore, group_by_category, load_scores
from .verdict import Verdict, build_verdict


@dataclass(frozen=True)
class Entry:
    score: FoodScore
    verdict: Verdict


@dataclass(frozen=True)
class Dashboard:
    by_category: dict  # category -> list[Entry], ranked
    by_slug: dict       # slug -> Entry


def build_dashboard(scores: list[FoodScore] | None = None) -> Dashboard:
    scores = scores if scores is not None else load_scores()
    grouped = group_by_category(scores)

    by_category: dict[str, list[Entry]] = {}
    by_slug: dict[str, Entry] = {}

    for category, rows in grouped.items():
        n = len(rows)
        best, worst = rows[0], rows[-1]
        entries = []
        for rank, row in enumerate(rows, start=1):
            verdict = build_verdict(row, rank, n, best, worst)
            entry = Entry(score=row, verdict=verdict)
            entries.append(entry)
            by_slug[verdict.slug] = entry
        by_category[category] = entries

    return Dashboard(by_category=by_category, by_slug=by_slug)
