"""Loads the vendored v0.13 scoring snapshot and exposes it grouped by category.

This is a READ-ONLY dashboard: the numbers below are pulled verbatim from
data/v13_results.csv, produced by running v0.13's reference implementation
against a food-spec JSON and a fixtures JSON. Those two inputs are not part
of this repo — see README.md "Regenerating the snapshot".
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "v13_results.csv"


@dataclass(frozen=True)
class FoodScore:
    category: str
    food: str
    latent: float
    portion_g: int
    kcal: int
    free_sugar_g: float
    sodium_g: float
    saturated_fat_g: float
    ul_flags: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "categorie": self.category,
            "food": self.food,
            "latent": self.latent,
            "portie_g": self.portion_g,
            "kcal": self.kcal,
            "vrije_suiker_g": self.free_sugar_g,
            "zout_g": self.sodium_g,
            "verzadigd_vet_g": self.saturated_fat_g,
            "ul_vlaggen": self.ul_flags,
        }


def _parse_ul_flags(raw: str) -> dict:
    """Undoes the "key=value; key2=value2" packing v13_reference.py writes
    into the ul_vlaggen CSV column."""
    flags = {}
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        key, _, value = chunk.partition("=")
        flags[key.strip()] = value.strip()
    return flags


def load_scores(path: Path = DATA_FILE) -> list[FoodScore]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return [
            FoodScore(
                category=row["categorie"],
                food=row["food"],
                latent=float(row["latent"]),
                portion_g=int(float(row["portie_g"])),
                kcal=int(float(row["kcal"])),
                free_sugar_g=float(row["vrije_suiker_g"]),
                sodium_g=float(row["zout_g"]),
                saturated_fat_g=float(row["verzadigd_vet_g"]),
                ul_flags=_parse_ul_flags(row.get("ul_vlaggen", "") or ""),
            )
            for row in reader
        ]


def group_by_category(scores: list[FoodScore]) -> dict[str, list[FoodScore]]:
    """Groups scores by category, each group ranked highest-latent-first.

    v0.13's whole point is that this ranking is only ever compared within a
    category — never flattened into one cross-category leaderboard.
    """
    grouped: dict[str, list[FoodScore]] = {}
    for score in scores:
        grouped.setdefault(score.category, []).append(score)
    for cat_scores in grouped.values():
        cat_scores.sort(key=lambda s: -s.latent)
    return grouped
