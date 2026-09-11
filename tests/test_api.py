import httpx
import respx
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_live():
    r = client.get("/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_index_renders():
    r = client.get("/")
    assert r.status_code == 200
    assert "food.bringon.io" in r.text
    assert "dranken" in r.text


def test_api_categories_lists_all():
    r = client.get("/api/categories")
    assert r.status_code == 200
    cats = r.json()
    assert "dranken" in cats
    assert cats == sorted(cats)


def test_api_foods_returns_all_rows():
    r = client.get("/api/foods")
    assert r.status_code == 200
    assert len(r.json()) == 29


def test_category_page_renders_known_category():
    r = client.get("/categorie/dranken")
    assert r.status_code == 200
    assert "Water" in r.text
    assert "Cola" in r.text


def test_unknown_category_is_404():
    assert client.get("/categorie/nonexistent").status_code == 404
    assert client.get("/api/categories/nonexistent").status_code == 404


def test_methodology_page_renders():
    r = client.get("/methodologie")
    assert r.status_code == 200
    assert "latente schaal" in r.text.lower() or "latent" in r.text.lower()


def test_category_page_shows_tier_badges():
    r = client.get("/categorie/dranken")
    assert r.status_code == 200
    assert "Topkeuze" in r.text
    assert "Laagste" in r.text


def test_product_page_renders_rationale_and_stats():
    r = client.get("/product/cola")
    assert r.status_code == 200
    assert "Cola" in r.text
    assert "onderbouwing" in r.text.lower()
    assert "-54.36" in r.text or "−54.36" in r.text


def test_product_page_shows_advice_when_flags_present():
    # Cola trips the free-sugar heuristic (35 g >= 15 g threshold).
    r = client.get("/product/cola")
    assert "Wat zou de score verbeteren" in r.text


def test_unknown_product_is_404():
    r = client.get("/product/does-not-exist")
    assert r.status_code == 404


def test_api_product_returns_verdict():
    r = client.get("/api/product/cola")
    assert r.status_code == 200
    data = r.json()
    assert data["food"] == "Cola"
    assert data["verdict"]["tier"] == "low"


def test_api_product_unknown_is_404():
    assert client.get("/api/product/does-not-exist").status_code == 404


def test_scan_page_renders():
    r = client.get("/scannen")
    assert r.status_code == 200
    assert "Open Food Facts" in r.text


def test_api_scan_rejects_malformed_barcode():
    assert client.get("/api/scan/not-a-barcode").status_code == 400
    assert client.get("/api/scan/123").status_code == 400


NUTELLA_PRODUCT = {
    "product_name": "Nutella",
    "brands": "Ferrero",
    "nutriscore_grade": "e",
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


def test_api_scan_success_is_never_the_v013_score():
    with respx.mock:
        respx.get("https://world.openfoodfacts.org/api/v2/product/3017620422003.json").mock(
            return_value=httpx.Response(200, json={"status": 1, "product": NUTELLA_PRODUCT})
        )
        r = client.get("/api/scan/3017620422003")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Nutella"
    assert "latent" not in data  # this is OFF data, never our v0.13 score


def test_api_scan_not_found():
    with respx.mock:
        respx.get("https://world.openfoodfacts.org/api/v2/product/0000000000000.json").mock(
            return_value=httpx.Response(200, json={"status": 0})
        )
        r = client.get("/api/scan/0000000000000")
    assert r.status_code == 404


def test_api_scan_off_unavailable_is_502():
    with respx.mock:
        respx.get("https://world.openfoodfacts.org/api/v2/product/1234567890123.json").mock(
            side_effect=httpx.ConnectError("boom")
        )
        r = client.get("/api/scan/1234567890123")
    assert r.status_code == 502
