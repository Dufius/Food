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
