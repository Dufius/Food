from app.data import FoodScore
from app.verdict import (
    absolute_flags,
    advice_for_flags,
    build_verdict,
    slugify,
    tier_for_rank,
)


def make_score(**kw):
    defaults = dict(
        category="dranken", food="Test", latent=0.0, portion_g=100, kcal=10,
        free_sugar_g=0.0, sodium_g=0.0, saturated_fat_g=0.0, ul_flags={},
    )
    defaults.update(kw)
    return FoodScore(**defaults)


def test_slugify_handles_punctuation_and_percent():
    assert slugify("Appel heel, lokaal") == "appel-heel-lokaal"
    assert slugify("85% pure chocolade") == "85pct-pure-chocolade"


def test_tier_for_rank_thirds():
    assert tier_for_rank(1, 6) == "top"
    assert tier_for_rank(2, 6) == "top"
    assert tier_for_rank(3, 6) == "mid"
    assert tier_for_rank(4, 6) == "mid"
    assert tier_for_rank(5, 6) == "low"
    assert tier_for_rank(6, 6) == "low"


def test_tier_for_rank_single_item_category_is_neutral():
    assert tier_for_rank(1, 1) == "mid"


def test_absolute_flags_thresholds():
    lean = make_score(free_sugar_g=2.0, sodium_g=0.2, saturated_fat_g=1.0, kcal=100)
    assert absolute_flags(lean) == []

    sugary = make_score(free_sugar_g=35.0)
    flags = absolute_flags(sugary)
    assert any(f["kind"] == "sugar" for f in flags)


def test_absolute_flags_includes_ul():
    liver_like = make_score(ul_flags={"vit_a_ug": "132% van bovengrens"})
    flags = absolute_flags(liver_like)
    ul_flags = [f for f in flags if f["kind"] == "ul"]
    assert len(ul_flags) == 1
    assert "132%" in ul_flags[0]["label"]


def test_advice_for_flags_dedups_and_orders():
    flags = [
        {"kind": "kcal", "label": "x"},
        {"kind": "sugar", "label": "y"},
        {"kind": "sugar", "label": "y2"},
    ]
    advice = advice_for_flags(flags)
    assert len(advice) == 2  # sugar once, kcal once
    assert advice[0] != advice[1]


def test_build_verdict_best_and_worst_reference_each_other():
    best = make_score(food="Beste", latent=10.0)
    mid = make_score(food="Midden", latent=0.0)
    worst = make_score(food="Slechtste", latent=-10.0)

    v_best = build_verdict(best, 1, 3, best, worst)
    v_worst = build_verdict(worst, 3, 3, best, worst)
    v_mid = build_verdict(mid, 2, 3, best, worst)

    assert v_best.tier == "top"
    assert "Hoogste" in v_best.rationale
    assert v_worst.tier == "low"
    assert "Laagste" in v_worst.rationale
    assert v_mid.tier == "mid"
    assert "Positie 2 van 3" in v_mid.rationale


def test_build_verdict_single_item_category_says_so():
    only = make_score(food="Enige")
    v = build_verdict(only, 1, 1, only, only)
    assert "Enige product" in v.rationale
    assert v.tier == "mid"


def test_build_verdict_no_flags_says_so():
    clean = make_score(free_sugar_g=0.0, sodium_g=0.0, saturated_fat_g=0.0, kcal=50)
    v = build_verdict(clean, 1, 2, clean, clean)
    assert "Geen van de gangbare aandachtspunten" in v.rationale
    assert v.advice == []
