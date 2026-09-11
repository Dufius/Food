"""Minimal synthetic spec + food fixtures for exercising app/scoring.py.

These are NOT the production v10_spec.json / v10_fixtures.json (not part of
this repo — see README.md). They exist only to give the ported scoring math
in scoring.py real unit-test coverage: shape-compatible with what parts()
expects, small enough to reason about by hand.
"""
from __future__ import annotations

SPEC = {
    "axes": {
        "density": {
            "denominator": {"floor": 50.0},
            "anchored_panel": {
                "scale": 40.0,
                "reference_intake": {
                    "fiber_g": {"value": 30.0},
                    "protein_g": {"value": 50.0},
                    "vit_c_mg": {"value": 80.0},
                },
            },
            "unanchored_terms": {
                "unsaturated_fat_g": {"weight": 1.0, "cap": 20.0},
                "magnesium_mg": {"weight": 0.1, "cap": 20.0},
                "potassium_mg": {"weight": 0.05, "cap": 20.0},
            },
        },
        "harm": {
            "energy_scaled": {
                "denominator": {"floor": 50.0},
                "terms": {
                    "free_sugar_g": {"weight": 1.0},
                    "saturated_fat_g": {"weight": 1.5},
                },
            },
            "mass_scaled": {
                "terms": {
                    "sodium_mg": {"weight": 0.01},
                },
            },
        },
        "processing": {
            "modulator": {"A": 5.0, "B": 10.0},
            "scale": {"K": 1.0},
        },
        "exposure": {
            "weight": {"gamma": 1.0},
        },
    }
}


def make_food(name="test food", kcal=100.0, reference_serving_g=100.0,
              processing_index=1.0, nutrients=None, micronutrients=None):
    n = {"kcal": kcal}
    n.update(nutrients or {})
    return {
        "name": name,
        "reference_serving_g": reference_serving_g,
        "processing_index": processing_index,
        "nutrients": n,
        "micronutrients": micronutrients or {},
    }
