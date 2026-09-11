"""food.bringon.io — a consumer-facing dashboard for BringOn's v0.13 food
scoring model, plus a barcode scanner for anything outside our own 29-food
snapshot.

Two distinct sources of "is this good for me", never blurred together:

1. Our own v0.13 data (data/v13_results.csv, enriched with a per-category
   tier + absolute nutrient flags + advice in verdict.py/dashboard.py).
   Read-only: this app does not recompute scores, see README.md.
2. Open Food Facts barcode lookups (off.py) for anything else — their own
   data plus generic advice, explicitly never presented as a v0.13 score.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.dashboard import build_dashboard
from app.off import OFFUnavailable, ProductNotFound, lookup_barcode
from app.scoring import LATENT, UL, UL_NOTE

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="food.bringon.io",
    description="v0.13 food scoring — category-scoped rankings, dose facts, and a barcode scanner",
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Loaded once at startup: this is a fixed snapshot, not a live query path.
_dashboard = build_dashboard()


# --- health --------------------------------------------------------------
# Three endpoints, matching the fleet-wide convention (see DevOps CLAUDE.md):
# /health/live is what the container healthcheck hits. The v0.13 dashboard
# has no dependency (CSV loaded at startup); the barcode scanner calls out
# to Open Food Facts, but that is a per-request feature, not something the
# service depends on to be considered healthy — Open Food Facts being down
# does not gate these endpoints.

@app.get("/health/live")
def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready():
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}


# --- JSON API — our own v0.13 data -----------------------------------------

@app.get("/api/categories")
def api_categories():
    return sorted(_dashboard.by_category.keys())


@app.get("/api/foods")
def api_foods():
    return [entry.score.as_dict() for entries in _dashboard.by_category.values() for entry in entries]


@app.get("/api/categories/{category}")
def api_category(category: str):
    entries = _dashboard.by_category.get(category)
    if entries is None:
        return JSONResponse({"error": "unknown category"}, status_code=404)
    return [entry.score.as_dict() for entry in entries]


@app.get("/api/product/{slug}")
def api_product(slug: str):
    entry = _dashboard.by_slug.get(slug)
    if entry is None:
        return JSONResponse({"error": "unknown product"}, status_code=404)
    return {**entry.score.as_dict(), "verdict": vars(entry.verdict)}


# --- JSON API — Open Food Facts barcode lookup ------------------------------

@app.get("/api/scan/{barcode}")
async def api_scan(barcode: str):
    if not barcode.isdigit() or not (8 <= len(barcode) <= 14):
        return JSONResponse({"error": "Ongeldige streepjescode."}, status_code=400)
    try:
        product = await lookup_barcode(barcode)
    except ProductNotFound:
        return JSONResponse({"error": "Product niet gevonden in Open Food Facts."}, status_code=404)
    except OFFUnavailable:
        return JSONResponse({"error": "Open Food Facts is nu niet bereikbaar. Probeer het later opnieuw."}, status_code=502)
    return product


# --- HTML dashboard ---------------------------------------------------------

@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "by_category": dict(sorted(_dashboard.by_category.items())),
            "latent": LATENT,
        },
    )


@app.get("/categorie/{category}")
def category_page(request: Request, category: str):
    entries = _dashboard.by_category.get(category)
    if entries is None:
        return templates.TemplateResponse(
            request,
            "not_found.html",
            {"category": category},
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "category.html",
        {"category": category, "entries": entries},
    )


@app.get("/product/{slug}")
def product_page(request: Request, slug: str):
    entry = _dashboard.by_slug.get(slug)
    if entry is None:
        return templates.TemplateResponse(
            request,
            "not_found.html",
            {"category": None, "slug": slug},
            status_code=404,
        )
    category_entries = _dashboard.by_category[entry.score.category]
    return templates.TemplateResponse(
        request,
        "product.html",
        {
            "entry": entry,
            "best": category_entries[0],
            "worst": category_entries[-1],
        },
    )


@app.get("/scannen")
def scan_page(request: Request):
    return templates.TemplateResponse(request, "scan.html", {})


@app.get("/methodologie")
def methodology(request: Request):
    return templates.TemplateResponse(
        request,
        "methodology.html",
        {"latent": LATENT, "ul": UL, "ul_note": UL_NOTE},
    )
