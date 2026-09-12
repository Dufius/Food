"""Tests the pure client-side math in app/static/quantity.js by running it
through Node (present on the CI image by default, no extra dependency).

These numbers are cross-checked against the FQQ v0.20 research bundle's own
validated test fixtures (v020_body_size_meal_test.csv,
v020_uncertainty_cascade.csv) — notably, the bundle's write-up calls the
FFM-based formula "Cunningham", but its actual numbers (1190.8 kcal at
FFM=38kg, 2054.8 kcal at FFM=78kg) only match Katch-McArdle
(370 + 21.6*FFM), not Cunningham (500 + 22*FFM). We use the formula that
actually reproduces the bundle's own numbers, correctly attributed.
"""
import json
import subprocess
from pathlib import Path

import pytest

QUANTITY_JS = Path(__file__).resolve().parent.parent / "app" / "static" / "quantity.js"

pytestmark = pytest.mark.skipif(
    subprocess.run(["node", "--version"], capture_output=True).returncode != 0,
    reason="node is not available in this environment",
)


def run_node(js_snippet: str) -> dict:
    script = QUANTITY_JS.read_text() + "\n" + js_snippet
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, f"node failed: {result.stderr}"
    return json.loads(result.stdout.strip())


def test_ffm_formula_matches_bundle_small_body():
    # v020_body_size_meal_test.csv: FFM=38kg -> ree_kcal=1190.8
    data = run_node("console.log(JSON.stringify(fqqComputeREE({ffmKg: '38'})))")
    assert abs(data["value"] - 1190.8) < 1e-6
    assert "Katch-McArdle" in data["source"]


def test_ffm_formula_matches_bundle_large_body():
    # v020_body_size_meal_test.csv: FFM=78kg -> ree_kcal=2054.8
    data = run_node("console.log(JSON.stringify(fqqComputeREE({ffmKg: '78'})))")
    assert abs(data["value"] - 2054.8) < 1e-6


def test_measured_ree_overrides_everything_else():
    data = run_node("""console.log(JSON.stringify(fqqComputeREE({
        measuredReeKcal: '1500', ffmKg: '38', weightKg: '52', heightCm: '155', ageYears: '30', sex: 'v'
    })))""")
    assert data["value"] == 1500
    assert data["source"] == "Gemeten rustmetabolisme"
    assert data["confidence"] == "hoog"


def test_ffm_overrides_age_sex_height_weight():
    data = run_node("""console.log(JSON.stringify(fqqComputeREE({
        ffmKg: '38', weightKg: '52', heightCm: '155', ageYears: '30', sex: 'v'
    })))""")
    assert "Katch-McArdle" in data["source"]


def test_mifflin_st_jeor_used_when_no_ree_or_ffm():
    data = run_node("""console.log(JSON.stringify(fqqComputeREE({
        weightKg: '70', heightCm: '175', ageYears: '30', sex: 'm'
    })))""")
    expected = 10 * 70 + 6.25 * 175 - 5 * 30 + 5
    assert abs(data["value"] - expected) < 1e-9
    assert "Mifflin" in data["source"]


def test_mifflin_st_jeor_women_offset():
    data = run_node("""console.log(JSON.stringify(fqqComputeREE({
        weightKg: '70', heightCm: '175', ageYears: '30', sex: 'v'
    })))""")
    expected = 10 * 70 + 6.25 * 175 - 5 * 30 - 161
    assert abs(data["value"] - expected) < 1e-9


def test_no_personal_data_falls_back_to_reference_intake():
    data = run_node("console.log(JSON.stringify(fqqComputeDailyTarget({})))")
    assert data["tdee"] == 2000
    assert data["ree"] is None
    assert "referentie-inname" in data["source"].lower()


def test_exertion_increases_daily_target_by_exactly_the_extra_kcal():
    data = run_node("""
        const base = fqqComputeDailyTarget({ffmKg: '38', activityLevel: 'sedentary'});
        const withExercise = fqqComputeDailyTarget({ffmKg: '38', activityLevel: 'sedentary', extraExerciseKcal: '600'});
        console.log(JSON.stringify({base: base.tdee, withExercise: withExercise.tdee}));
    """)
    assert data["withExercise"] - data["base"] == pytest.approx(600)


def test_remaining_and_surplus_are_mutually_exclusive():
    data = run_node("""
        const low = fqqRemainingNeed({ffmKg: '38', activityLevel: 'sedentary', consumedTodayKcal: '100'});
        const high = fqqRemainingNeed({ffmKg: '38', activityLevel: 'sedentary', consumedTodayKcal: '5000'});
        console.log(JSON.stringify({low, high}));
    """)
    assert data["low"]["remaining"] > 0
    assert data["low"]["surplus"] == 0
    assert data["high"]["surplus"] > 0
    assert data["high"]["remaining"] == 0


def test_same_meal_is_a_bigger_fraction_for_the_smaller_body():
    # Mirrors the bundle's own headline test: same 550 kcal meal, same
    # activity level, different body size -> different fraction of daily need.
    data = run_node("""
        const small = fqqComputeDailyTarget({ffmKg: '38', activityLevel: 'light'});
        const large = fqqComputeDailyTarget({ffmKg: '78', activityLevel: 'light'});
        console.log(JSON.stringify({
          smallFraction: 550 / small.tdee,
          largeFraction: 550 / large.tdee,
        }));
    """)
    assert data["smallFraction"] > data["largeFraction"]
