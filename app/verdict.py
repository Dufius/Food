"""Consumer-facing verdicts layered on top of the v0.13 latent score.

Two independent signals, deliberately kept separate — this module must never
quietly merge them into one fake universal health score:

1. TIER — a food's position within its OWN category (top/mid/low third of
   latent scores in that category). This is exactly v0.13's actual output:
   a claim relative to other products in the same category, never across
   categories. "Laagste van groente_fruit" does not mean unhealthy — an
   apple at the bottom of a category full of nori and lettuce is still an
   apple; the wording below says "laagste", never "ongezond", for that
   reason.

2. FLAGS — absolute, category-independent facts read straight off
   dose_facts(): a food either does or doesn't deliver a lot of free sugar,
   sodium, saturated fat, or exceed 50% of a nutrient's upper limit in one
   portion. These numbers mean the same thing whether the food is a drink
   or a dessert, which is exactly why — unlike TIER — they can be absolute.
   The sugar/sodium/fat/kcal thresholds are our own everyday rule of thumb,
   not a cited external standard; the UL-based flags are the one piece here
   that does carry a fixed reference (see scoring.py's UL dict).

Each triggered flag also carries a generic, actionable ADVICE line ("wat
zou de score verbeteren") — this is deliberately generic dietary guidance
tied to the flag that fired, never a claim like "add 3g fiber and the score
becomes +12.4": we don't have the per-nutrient axis breakdown (Q/harm/proc)
for these 29 vendored foods, only the final latent number and dose facts.
See off.py for the same idea applied to Open Food Facts barcode lookups,
which *do* carry a fuller nutrient panel per 100g.

If you are tempted to add a single 0-100 "health score" here: don't,
without first checking with the user — that is exactly the universal
ordering v0.13 explicitly refuses to produce.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .data import FoodScore

# Per-portion rules of thumb — ours, not an official standard. Deliberately
# separate from UL (scoring.py), which does carry a real reference intake.
SUGAR_HIGH_G = 15.0
SODIUM_HIGH_G = 1.0    # dose_facts' "zout_g" is already the salt-equivalent (Na x 2.5)
SATFAT_HIGH_G = 5.0
KCAL_HIGH = 500

TIER_TOP, TIER_MID, TIER_LOW = "top", "mid", "low"

TIER_LABEL = {
    TIER_TOP: "Topkeuze",
    TIER_MID: "Gemiddeld",
    TIER_LOW: "Laagste",
}
TIER_CLASS = {
    TIER_TOP: "tier-top",
    TIER_MID: "tier-mid",
    TIER_LOW: "tier-low",
}

ADVICE = {
    "sugar": "Kies een variant met minder toegevoegde/vrije suiker, of eet een kleinere portie.",
    "sodium": "Een natriumarmere variant of kleinere portie verlaagt de zoutbelasting van deze portie.",
    "satfat": "Vervang een deel van het verzadigd vet door onverzadigd vet (bijv. olijfolie, noten, vette vis).",
    "kcal": "Een kleinere portie houdt de energie-impact van dit ene moment lager.",
    "ul": "Combineer dit niet met andere bronnen van hetzelfde nutriënt op dezelfde dag — deze portie alleen zit al boven de helft van de veilige bovengrens.",
}


def slugify(name: str) -> str:
    s = name.lower().replace("%", "pct")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def tier_for_rank(rank: int, n: int) -> str:
    """rank is 1-based, 1 = highest latent score in its category."""
    if n <= 1:
        return TIER_MID
    pct = (rank - 1) / (n - 1)
    if pct <= 1 / 3:
        return TIER_TOP
    if pct >= 2 / 3:
        return TIER_LOW
    return TIER_MID


def absolute_flags(score: FoodScore) -> list[dict]:
    """Category-independent warnings. Our heuristics first, then the
    UL-referenced ones (which carry a real reference intake, see scoring.py)."""
    flags = []
    if score.free_sugar_g >= SUGAR_HIGH_G:
        flags.append({"kind": "sugar", "label": f"Veel vrije suiker: {score.free_sugar_g:g} g per portie"})
    if score.sodium_g >= SODIUM_HIGH_G:
        flags.append({"kind": "sodium", "label": f"Veel zout: {score.sodium_g:g} g per portie"})
    if score.saturated_fat_g >= SATFAT_HIGH_G:
        flags.append({"kind": "satfat", "label": f"Veel verzadigd vet: {score.saturated_fat_g:g} g per portie"})
    if score.kcal >= KCAL_HIGH:
        flags.append({"kind": "kcal", "label": f"Veel energie: {score.kcal} kcal per portie"})
    for nutrient, detail in score.ul_flags.items():
        naam = nutrient.split("_")[0]
        flags.append({"kind": "ul", "label": f"{naam}: {detail}", "nutrient": nutrient})
    return flags


def advice_for_flags(flags: list[dict]) -> list[str]:
    """Dedups by kind, keeps a stable order (sugar, sodium, satfat, kcal, ul)."""
    order = ["sugar", "sodium", "satfat", "kcal", "ul"]
    seen = {f["kind"] for f in flags}
    return [ADVICE[kind] for kind in order if kind in seen]


@dataclass(frozen=True)
class Verdict:
    slug: str
    category: str
    rank: int
    of: int
    tier: str
    tier_label: str
    flags: list = field(default_factory=list)
    advice: list = field(default_factory=list)
    rationale: str = ""


def _cat_label(category: str) -> str:
    return category.replace("_", " ")


def build_verdict(score: FoodScore, rank: int, n: int, best: FoodScore, worst: FoodScore) -> Verdict:
    tier = tier_for_rank(rank, n)
    flags = absolute_flags(score)
    advice = advice_for_flags(flags)
    cat = _cat_label(score.category)

    bits = []
    if n == 1:
        bits.append(
            f"Enige product tot nu toe in de categorie {cat} — nog geen vergelijking mogelijk."
        )
    elif score.food == best.food:
        margin = score.latent - worst.latent
        bits.append(
            f"Hoogste latente score binnen {cat}: {margin:+.2f} punten voorsprong op {worst.food}."
        )
    elif score.food == worst.food:
        margin = best.latent - score.latent
        bits.append(
            f"Laagste latente score binnen {cat}: {margin:+.2f} punten achterstand op {best.food}."
        )
    else:
        bits.append(f"Positie {rank} van {n} binnen {cat}.")

    if flags:
        bits.append("Let op: " + "; ".join(f["label"] for f in flags) + ".")
    else:
        bits.append(
            "Geen van de gangbare aandachtspunten (suiker, zout, verzadigd vet, bovengrenzen) "
            "speelt hier op portieniveau."
        )

    return Verdict(
        slug=slugify(score.food),
        category=score.category,
        rank=rank,
        of=n,
        tier=tier,
        tier_label=TIER_LABEL[tier],
        flags=flags,
        advice=advice,
        rationale=" ".join(bits),
    )
