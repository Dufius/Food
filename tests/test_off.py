import httpx
import pytest
import respx

from app.off import (
    OFFUnavailable,
    ProductNotFound,
    advice_for,
    lookup_barcode,
    parse_product,
)

NUTELLA_PRODUCT = {
    "product_name": "Nutella",
    "brands": "Ferrero",
    "quantity": "400g",
    "image_front_small_url": "https://example.invalid/nutella.jpg",
    "nutriscore_grade": "e",
    "nova_group": 4,
    "nutriments": {
        "energy-kcal_100g": 539,
        "sugars_100g": 56.3,
        "saturated-fat_100g": 10.6,
        "sodium_100g": 0.107,
        "salt_100g": 0.27,
        "fiber_100g": 3.4,
        "proteins_100g": 6.3,
    },
}


def test_parse_product_maps_off_fields():
    facts = parse_product(NUTELLA_PRODUCT)
    assert facts["name"] == "Nutella"
    assert facts["nutriscore"] == "E"
    assert facts["per_100g"]["kcal"] == 539
    assert facts["per_100g"]["sodium_mg"] == pytest.approx(107.0)


def test_advice_for_flags_high_sugar_and_satfat():
    tips = advice_for({"sugars_g": 56.3, "saturated_fat_g": 10.6, "sodium_mg": 107.0, "fiber_g": 3.4, "protein_g": 6.3})
    joined = " ".join(tips).lower()
    assert "suiker" in joined
    assert "verzadigd vet" in joined
    # fiber (3.4) is above the low-fiber threshold (3.0) and protein (6.3) above
    # the low-protein threshold (5.0) — neither should be flagged here.
    assert "vezels" not in joined
    assert "eiwit" not in joined


def test_advice_for_clean_product_says_nothing_stands_out():
    tips = advice_for({"sugars_g": 1.0, "saturated_fat_g": 0.5, "sodium_mg": 50.0, "fiber_g": 8.0, "protein_g": 10.0})
    assert len(tips) == 1
    assert "geen" in tips[0].lower()


def test_advice_for_missing_fields_does_not_crash():
    assert advice_for({}) == ["Geen van onze gangbare aandachtspunten springt eruit op basis van de Open Food Facts-gegevens."]


@pytest.mark.anyio
async def test_lookup_barcode_success():
    with respx.mock:
        respx.get("https://world.openfoodfacts.org/api/v2/product/3017620422003.json").mock(
            return_value=httpx.Response(200, json={"status": 1, "product": NUTELLA_PRODUCT})
        )
        facts = await lookup_barcode("3017620422003")
    assert facts["name"] == "Nutella"


@pytest.mark.anyio
async def test_lookup_barcode_not_found():
    with respx.mock:
        respx.get("https://world.openfoodfacts.org/api/v2/product/0000000000000.json").mock(
            return_value=httpx.Response(200, json={"status": 0})
        )
        with pytest.raises(ProductNotFound):
            await lookup_barcode("0000000000000")


@pytest.mark.anyio
async def test_lookup_barcode_network_error_raises_off_unavailable():
    with respx.mock:
        respx.get("https://world.openfoodfacts.org/api/v2/product/1234567890123.json").mock(
            side_effect=httpx.ConnectError("boom")
        )
        with pytest.raises(OFFUnavailable):
            await lookup_barcode("1234567890123")


@pytest.fixture
def anyio_backend():
    return "asyncio"
