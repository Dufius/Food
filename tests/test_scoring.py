"""Tests for the ported v0.13 scoring math in app/scoring.py.

The canary test here is the same discipline v13_reference.py carries: if a
10x bump in a beneficial nutrient stops moving the latent score, the benefit
path is disconnected — the exact v0.12.4 defect (9,000 of 20,000 metamorphic
tests passed vacuously). It must fail loudly, not silently pass.
"""
from app.scoring import canary, dose_facts, latent

from .fixtures import SPEC, make_food


def test_canary_benefit_path_is_wired():
    foods = [
        make_food("water-achtig", kcal=1.0),
        make_food("gemiddeld", kcal=150.0, nutrients={
            "fiber_g": 3.0, "protein_g": 5.0, "unsaturated_fat_g": 2.0,
            "free_sugar_g": 1.0, "saturated_fat_g": 1.0, "sodium_mg": 50.0,
        }, micronutrients={"vit_c_mg": 10.0, "magnesium_mg": 20.0, "potassium_mg": 100.0}),
    ]
    fails, results = canary(foods, SPEC)
    assert fails == [], f"canary broken for: {fails} (dood pad — batenkant niet aangesloten)"
    for nut, (moved, total) in results.items():
        assert moved == total, f"{nut} only moved {moved}/{total} products"


def test_latent_strictly_increases_with_beneficial_nutrient():
    base = make_food(kcal=150.0, nutrients={"fiber_g": 2.0})
    more_fiber = make_food(kcal=150.0, nutrients={"fiber_g": 20.0})
    assert latent(more_fiber, SPEC) > latent(base, SPEC)


def test_latent_strictly_decreases_with_harm():
    base = make_food(kcal=150.0, nutrients={"free_sugar_g": 1.0})
    more_sugar = make_food(kcal=150.0, nutrients={"free_sugar_g": 40.0})
    assert latent(more_sugar, SPEC) < latent(base, SPEC)


def test_latent_strictly_decreases_with_processing():
    lightly_processed = make_food(kcal=150.0, processing_index=1.0)
    heavily_processed = make_food(kcal=150.0, processing_index=10.0)
    assert latent(heavily_processed, SPEC) < latent(lightly_processed, SPEC)


def test_dose_facts_reports_per_portion_amounts():
    food = make_food(
        kcal=400.0,
        reference_serving_g=200.0,
        nutrients={"free_sugar_g": 10.0, "sodium_mg": 800.0, "saturated_fat_g": 5.0},
    )
    facts = dose_facts(food)
    assert facts["portie_g"] == 200.0
    assert facts["kcal"] == 800  # 400 kcal/100g * 2 portions
    assert facts["vrije_suiker_g"] == 20.0
    assert facts["zout_g"] == round(800.0 * 2 * 2.5 / 1000, 2)
    assert facts["verzadigd_vet_g"] == 10.0


def test_dose_facts_flags_only_above_50pct_of_upper_limit():
    low = make_food(kcal=100.0, reference_serving_g=100.0,
                     micronutrients={"vit_a_ug": 1000.0})  # 33% of UL 3000
    high = make_food(kcal=100.0, reference_serving_g=100.0,
                      micronutrients={"vit_a_ug": 2000.0})  # 67% of UL 3000
    assert dose_facts(low)["ul_vlaggen"] == {}
    assert "vit_a_ug" in dose_facts(high)["ul_vlaggen"]
