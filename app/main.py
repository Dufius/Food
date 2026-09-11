"""food.bringon.io — read-only dashboard for the v0.13 food scoring model.

Serves the category-scoped rankings and per-portion dose facts produced by
v0.13's scoring engine (see scoring.py and README.md for the methodology).
v1 is intentionally read-only: it renders a fixed snapshot
(data/v13_results.csv), it does not accept new food entries or recompute
scores on request.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.data import group_by_category, load_scores
from app.scoring import LATENT, UL, UL_NOTE

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="food.bringon.io",
    description="v0.13 food scoring — category-scoped rankings and dose facts",
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Loaded once at startup: this is a fixed snapshot, not a live query path.
_scores = load_scores()
_by_category = group_by_category(_scores)


# --- health --------------------------------------------------------------
# Three endpoints, matching the fleet-wide convention (see DevOps CLAUDE.md):
# /health/live is what the container healthcheck hits. This service has no
# external dependency (no DB, no cache, no broker — everything it serves is
# a CSV loaded at startup), so /health, /health/live and /health/ready are
# identical today. Kept as three routes anyway so this app doesn't need a
# breaking change the day it grows a dependency worth checking.

@app.get("/health/live")
def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready():
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}


# --- JSON API --------------------------------------------------------------

@app.get("/api/categories")
def api_categories():
    return sorted(_by_category.keys())


@app.get("/api/foods")
def api_foods():
    return [s.as_dict() for s in _scores]


@app.get("/api/categories/{category}")
def api_category(category: str):
    rows = _by_category.get(category)
    if rows is None:
        return JSONResponse({"error": "unknown category"}, status_code=404)
    return [s.as_dict() for s in rows]


# --- HTML dashboard ---------------------------------------------------------

@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "by_category": dict(sorted(_by_category.items())),
            "latent": LATENT,
        },
    )


@app.get("/categorie/{category}")
def category_page(request: Request, category: str):
    rows = _by_category.get(category)
    if rows is None:
        return templates.TemplateResponse(
            request,
            "not_found.html",
            {"category": category},
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "category.html",
        {"category": category, "rows": rows},
    )


@app.get("/methodologie")
def methodology(request: Request):
    return templates.TemplateResponse(
        request,
        "methodology.html",
        {"latent": LATENT, "ul": UL, "ul_note": UL_NOTE},
    )
