"""Open Food Facts integration — barcode lookup for products outside our own
29-food v0.13 snapshot.

This is deliberately NOT the v0.13 score. Open Food Facts' nutrient panel
doesn't carry the micronutrient panel, processing index, or reference-intake
weights parts() needs, and we don't have v10_spec.json to run it even if it
did. What a barcode scan shows instead: Open Food Facts' own data (name,
image, nutriments, their Nutri-Score/NOVA group if present) plus generic,
clearly-labelled dietary rules of thumb — never our v0.13 latent score,
never presented as if it were. See scan.html for how this is disclosed to
the user, and verdict.py for the same "flags -> generic advice" idea
applied to our own 29 vendored foods.

This is the one place in the app that makes an outbound network call. It
does not gate /health/* — a scan failing does not mean the dashboard is
unhealthy, see main.py.
"""
from __future__ import annotations

import httpx

OFF_BASE = "https://world.openfoodfacts.org/api/v2/product"
# Open Food Facts asks integrations to identify themselves — see their API
# usage policy — so a generic requests/httpx user agent risks being blocked.
USER_AGENT = "food.bringon.io/1.0 (+https://food.bringon.io; contact: vincent@bringon.io)"
TIMEOUT = 8.0

# Same spirit as verdict.py's per-portion thresholds, applied to Open Food
# Facts' per-100g figures (OFF always normalizes nutriments to per 100g/ml).
# Ours, not a cited external standard.
SUGAR_HIGH_100G = 22.5
SATFAT_HIGH_100G = 5.0
SODIUM_HIGH_100G_MG = 600.0  # roughly 1.5 g salt-equivalent per 100 g
FIBER_LOW_100G = 3.0
PROTEIN_LOW_100G = 5.0


class ProductNotFound(Exception):
    """Barcode not in Open Food Facts."""


class OFFUnavailable(Exception):
    """Open Food Facts could not be reached or returned an error."""


async def lookup_barcode(barcode: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
            resp = await client.get(f"{OFF_BASE}/{barcode}.json")
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise OFFUnavailable(str(exc)) from exc

    data = resp.json()
    if data.get("status") != 1 or "product" not in data:
        raise ProductNotFound(barcode)
    return parse_product(data["product"])


def parse_product(product: dict) -> dict:
    n = product.get("nutriments") or {}
    sodium_100g = n.get("sodium_100g")
    per_100g = {
        "kcal": n.get("energy-kcal_100g"),
        "sugars_g": n.get("sugars_100g"),
        "saturated_fat_g": n.get("saturated-fat_100g"),
        "sodium_mg": None if sodium_100g is None else round(sodium_100g * 1000, 1),
        "salt_g": n.get("salt_100g"),
        "fiber_g": n.get("fiber_100g"),
        "protein_g": n.get("proteins_100g"),
    }
    return {
        "name": product.get("product_name_nl") or product.get("product_name") or "Onbekend product",
        "brand": product.get("brands", ""),
        "image": product.get("image_front_small_url") or product.get("image_url"),
        "quantity": product.get("quantity", ""),
        "nutriscore": (product.get("nutriscore_grade") or "").upper() or None,
        "nova_group": product.get("nova_group"),
        "per_100g": per_100g,
        "advies": advice_for(per_100g),
    }


def advice_for(per_100g: dict) -> list[str]:
    """Generic, clearly-scoped advice — see module docstring. Never claims a
    precise score delta, only "this lever, in this direction"."""
    tips = []
    sugars = per_100g.get("sugars_g")
    satfat = per_100g.get("saturated_fat_g")
    sodium_mg = per_100g.get("sodium_mg")
    fiber = per_100g.get("fiber_g")
    protein = per_100g.get("protein_g")

    if sugars is not None and sugars >= SUGAR_HIGH_100G:
        tips.append(f"Veel suiker ({sugars:g} g/100g) — een variant met minder toegevoegde suiker scoort beter.")
    if satfat is not None and satfat >= SATFAT_HIGH_100G:
        tips.append(f"Veel verzadigd vet ({satfat:g} g/100g) — vervang deels door onverzadigd vet.")
    if sodium_mg is not None and sodium_mg >= SODIUM_HIGH_100G_MG:
        tips.append(f"Veel zout (~{sodium_mg / 1000 * 2.5:.1f} g zout-equivalent/100g) — een natriumarmere variant helpt.")
    if fiber is not None and fiber < FIBER_LOW_100G:
        tips.append(f"Weinig vezels ({fiber:g} g/100g) — combineer met groente, peulvruchten of volkoren graanproducten.")
    if protein is not None and protein < PROTEIN_LOW_100G:
        tips.append(f"Weinig eiwit ({protein:g} g/100g) — combineer met een eiwitbron zoals peulvruchten, ei of yoghurt.")
    if not tips:
        tips.append("Geen van onze gangbare aandachtspunten springt eruit op basis van de Open Food Facts-gegevens.")
    return tips
