"""v0.13 scoring engine — category-scoped, unbounded latent scale, dose facts first.

Vendored from the v0.13 reference implementation (v13_reference.py). This module
is the single source of truth for *how* a score is computed; it does not itself
decide what gets rendered — see data.py for the dashboard's read path, which
currently serves the pre-computed data/v13_results.csv snapshot rather than
calling `latent()` live, because the two inputs `parts()` needs — a food-spec
JSON (density/harm/processing axis definitions) and a fixtures JSON (the actual
food composition data) — are not part of this repo. They belong to the
data-science side of the scoring work; see README.md "Regenerating the
snapshot" for what would need to land here to make this call live again.

Three changes of principle carried over from v13_reference.py, verbatim:

1. NO UNIVERSAL ORDERING. A score is only defined against other foods in the
   same category. Cross-category comparison is refused by the code, not merely
   discouraged in a comment. "Is nori better than crisps" is a question nobody
   asks at a shelf; the whole denominator argument, the ceiling at 100 and the
   floor collapse at 0 were artefacts of insisting on an answer to it.

2. UNBOUNDED LATENT SCALE. v0.12.4 assembled multiplicatively
   (quality_base x (1 - penalty)) with quality_base = 0 at zero density, so
   everything without density collapsed to exactly 0. The latent form below is
   strictly monotone in every input and saturates nowhere, so ordering
   survives at both ends. The hard-coded water exception is no longer needed:
   water lands at latent 0 by construction.

3. DOSE FACTS ARE THE OUTPUT. What one realistic portion delivers, in grams,
   plus any upper-limit flag. The rank is secondary and is reported as a
   position within its category, never as a bare number.
"""
from __future__ import annotations

import copy
import math

CATEGORY = {
    "Water": "dranken", "Zwarte koffie": "dranken", "Light cola": "dranken",
    "Cola": "dranken", "Sinaasappelsap": "dranken", "Bouillon bereid": "dranken",
    "Kropsla": "groente_fruit", "Komkommer": "groente_fruit", "Nori zeewier": "groente_fruit",
    "Appel heel, lokaal": "groente_fruit", "Appelmoes ongezoet": "groente_fruit",
    "Linzen gekookt": "peulvruchten_noten", "Walnoten": "peulvruchten_noten",
    "Bruine rijst laag-arseen": "granen", "Bruine rijst hoog-arseen": "granen",
    "Witte rijst laag-arseen": "granen",
    "Extra vierge olijfolie": "vetten", "Boter": "vetten",
    "Gekookt lokaal ei": "vis_vlees_ei", "Sardines in blik": "vis_vlees_ei",
    "Runderlever gebakken": "vis_vlees_ei",
    "Magere yoghurt naturel": "zuivel",
    "Honing": "zoetmakers", "Witte tafelsuiker": "zoetmakers",
    "85% pure chocolade": "zoetwaren",
    "Chips": "hartige_snacks", "Proteinereep": "hartige_snacks",
    "Happy Meal-achtig": "samengestelde_maaltijden",
    "Spirulinapoeder": "supplementen",
}

LATENT = {"w_quality": 10.0, "w_harm": 8.0, "w_processing": 8.0,
          "expr": "w_q*ln(1+Q) - w_h*ln(1+P_harm) - w_p*ln(1+P_proc)",
          "kind": "CHOSEN — no reference intake exists for the trade-off between "
                  "the three axes. Labelled, not disguised.",
          "properties": "strictly monotone in each argument, no floor, no ceiling, "
                        "water = 0 by construction"}

UL = {"vit_a_ug": 3000, "vit_d_ug": 100, "calcium_mg": 2500, "iron_mg": 40,
      "folate_ug": 1000, "magnesium_mg": 250, "vit_c_mg": 2000}
UL_NOTE = {"folate_ug": "alleen synthetisch foliumzuur", "magnesium_mg": "alleen supplementair"}


def amounts(f):
    d = dict(f["nutrients"])
    d.update(f.get("micronutrients", {}))
    return d


def parts(f, spec):
    """Returns (quality, harm_exposed, processing_exposed) — all >= 0."""
    a = amounts(f)
    d = spec["axes"]["density"]
    k = 100.0 / max(a["kcal"], d["denominator"]["floor"])
    ri = d["anchored_panel"]["reference_intake"]
    anch = 100.0 * sum(min(a.get(n, 0.0) * k / c["value"], 1.0) for n, c in ri.items()) \
        / len(ri) * d["anchored_panel"]["scale"]
    unanch = sum(min(a.get(n, 0.0) * k * c["weight"], c["cap"])
                 for n, c in d["unanchored_terms"].items())
    Q = anch + unanch
    h = spec["axes"]["harm"]
    ke = 100.0 / max(a["kcal"], h["energy_scaled"]["denominator"]["floor"])
    harm = sum(a.get(t, 0.0) * ke * c["weight"] for t, c in h["energy_scaled"]["terms"].items()) \
        + sum(a.get(t, 0.0) * c["weight"] for t, c in h["mass_scaled"]["terms"].items())
    p = spec["axes"]["processing"]
    mod = 1 + p["modulator"]["A"] / (Q + p["modulator"]["B"])
    expw = (f["reference_serving_g"] / 100.0) ** spec["axes"]["exposure"]["weight"]["gamma"]
    return Q, harm * expw, f["processing_index"] * mod * p["scale"]["K"] * expw


def latent(f, spec):
    Q, P, R = parts(f, spec)
    return (LATENT["w_quality"] * math.log1p(Q)
            - LATENT["w_harm"] * math.log1p(P)
            - LATENT["w_processing"] * math.log1p(R))


def dose_facts(f):
    """What one reference serving actually delivers. This is the headline."""
    a = amounts(f)
    s = f["reference_serving_g"] / 100.0
    out = {"portie_g": f["reference_serving_g"],
           "kcal": round(a["kcal"] * s),
           "vrije_suiker_g": round(a.get("free_sugar_g", 0) * s, 1),
           "zout_g": round(a.get("sodium_mg", 0) * s * 2.5 / 1000, 2),
           "verzadigd_vet_g": round(a.get("saturated_fat_g", 0) * s, 1)}
    flags = {}
    for n, lim in UL.items():
        pct = 100.0 * a.get(n, 0.0) * s / lim
        if pct >= 50:
            flags[n] = f"{pct:.0f}% van bovengrens" + (f" ({UL_NOTE[n]})" if n in UL_NOTE else "")
    out["ul_vlaggen"] = flags
    return out


def canary(foods, spec):
    """MUST move. If a 10x increase in a beneficial nutrient leaves the latent
    score unchanged, the benefit path is not wired to the score and every
    'benefit' test in the suite is a vacuous pass — the exact v0.12.4 defect
    this canary exists to catch."""
    fails = []
    results = {}
    for nut, where in [("fiber_g", "nutrients"), ("protein_g", "nutrients"),
                       ("unsaturated_fat_g", "nutrients"), ("vit_c_mg", "micronutrients"),
                       ("magnesium_mg", "micronutrients"), ("potassium_mg", "micronutrients")]:
        moved = 0
        for f in foods:
            g = copy.deepcopy(f)
            g.setdefault("micronutrients", {})
            base = g[where].get(nut, 0.0)
            g[where][nut] = max(base * 10, 5.0)
            if latent(g, spec) - latent(f, spec) > 1e-9:
                moved += 1
        results[nut] = (moved, len(foods))
        if moved == 0:
            fails.append(nut)
    return fails, results
