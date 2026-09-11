# food.bringon.io

Consumer-facing dashboard for BringOn's v0.13 food scoring model: a
gezondheidsscore **with substantiation** for each of our own 29 foods, plus
a barcode scanner (Open Food Facts) for everything else. FastAPI +
server-rendered HTML, no database, no user accounts.

## What this is (v1)

Two distinct sources of "is this good for me", deliberately never blurred
into one fake universal number:

1. **Our own v0.13 data** (`data/v13_results.csv`), enriched per food with:
   - a **tier** — Topkeuze / Gemiddeld / Laagste — the food's position
     within its own category, translated to words. This is v0.13's actual
     output: relative to other foods in the same category, never across
     categories. "Laagste" is not "ongezond": an apple at the bottom of a
     category full of nori and lettuce is still an apple. See
     `app/verdict.py`.
   - absolute **flags** — free sugar, sodium, saturated fat, energy per
     portion above an everyday rule-of-thumb threshold, plus the UL flags
     that already existed in `v13_reference.py` (those do carry a real
     reference intake). These mean the same thing regardless of category,
     which is exactly why they can be absolute where tier can't.
   - generic **advice** tied to whichever flags fired ("kies een variant
     met minder toegevoegde suiker…") — never a claim like "add 3g fiber
     and the score becomes +12.4": we don't have the per-nutrient axis
     breakdown for these 29 vendored foods, only the final latent number
     and dose facts.
   - a plain-language **rationale** combining tier + flags into one
     paragraph, shown on each product's page.

   Read-only: this app does not recompute v0.13 scores, see "Why the
   dashboard doesn't compute scores live" below.

2. **Open Food Facts barcode lookups** (`app/off.py`) for anything outside
   our own 29 foods. This is a real outbound network call — the one place
   in this app that has one — to `world.openfoodfacts.org`'s public API.
   It returns OFF's own nutrition data (and their Nutri-Score/NOVA group if
   present) plus the same kind of generic advice as above, computed from
   OFF's per-100g nutrients. **Never presented as our v0.13 score** — OFF
   doesn't carry the micronutrient panel, processing index, or
   reference-intake weights `parts()` needs, and we don't have
   `v10_spec.json` to run it even if it did. `/scannen` discloses this
   explicitly in the UI.

`app/scoring.py` is the ported v0.13 scoring engine (`latent()`,
`dose_facts()`, `parts()`, the benefit-path `canary()`) — vendored verbatim
from the reference implementation, kept here for provenance and so the
math has real unit-test coverage (`tests/test_scoring.py`), not because the
dashboard calls it live today.

## Why the dashboard doesn't compute scores live

`parts()` needs two inputs neither of which is part of this repo:

- a **food-spec JSON** (`v10_spec.json`) — density/harm/processing axis
  definitions, reference intakes, weights, caps;
- a **fixtures JSON** (`v10_fixtures.json`) — the actual food composition
  data (nutrients, micronutrients, processing index, reference serving) plus
  the golden-pairs constraints.

Both live with the data-science side of the scoring work, not in this app
repo. `data/v13_results.csv` is the output of running the reference
implementation against them once, vendored here as the current snapshot.

### Regenerating the snapshot

Once `v10_spec.json` and `v10_fixtures.json` are available:

1. Drop them under `data/`.
2. Run the reference script's `main()` (or a thin wrapper importing
   `app.scoring`) to regenerate `data/v13_results.csv`.
3. Commit the new snapshot — the dashboard picks it up on next deploy.

A live-compute API (`POST` nutrients in, get a score back) is a natural v2
once those inputs are available; `app/scoring.py` already has the pure
functions for it, they're just not wired to a route yet.

## Barcode scanning

`/scannen` uses the browser's `BarcodeDetector` API (Chrome/Edge/Android
Chrome) to read EAN/UPC codes from the camera, with a manual numeric-entry
fallback for browsers without it (notably Safari/Firefox at time of
writing) or when camera permission is denied. Either path calls
`GET /api/scan/{barcode}`, which proxies to Open Food Facts
(`app/off.py`) and returns their data plus generic advice — see
`app/off.py`'s module docstring for the full reasoning on why that's never
our v0.13 score.

This was **not** end-to-end verified against the live Open Food Facts API
in the sandbox this was built in — that sandbox's network egress policy
blocks `world.openfoodfacts.org` outright. What is verified: the full
request/response handling (success, not-found, and network-error paths)
against `respx`-mocked responses shaped exactly like OFF's documented API
schema (`tests/test_off.py`, `tests/test_api.py`). Worth a real end-to-end
check once this runs somewhere with normal internet egress.

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
pytest -v
```

## Docker

```bash
docker build -t food .
docker run -p 8000:8000 food
```

Health checks: `/health/live` (used by the Swarm container healthcheck),
`/health/ready`, `/health` — all identical today. The v0.13 dashboard has
no dependency to be "not ready" for; the barcode scanner calls out to Open
Food Facts, but that's a per-request feature, not something the service
depends on to be considered healthy — OFF being down doesn't gate these
endpoints.

## Deployment

Built and pushed here (`.github/workflows/cd.yml`) to
`ghcr.io/bringon/food`, then released and deployed by
[`bringon/devops`](https://github.com/bringon/devops) —
`release-food.yml` pins the tag, `deploy-food.yml` rolls it out to the
Swarm cluster, fronted by Traefik at `https://food.bringon.io`. See that
repo's `docker/swarm/stacks/food/` and `CLAUDE.md`.

## Layout

```
app/
├── main.py         FastAPI routes + health endpoints
├── data.py         Loads/groups data/v13_results.csv (FoodScore)
├── verdict.py       Tier + absolute flags + advice + rationale (v0.13 data)
├── dashboard.py      Wires FoodScore + Verdict together, indexes by slug
├── off.py           Open Food Facts barcode lookup + generic advice
├── scoring.py        Ported v0.13 scoring engine (latent, dose_facts, canary)
├── templates/        Jinja2 HTML (index, category, product, scan, methodology)
└── static/           style.css, favicon.svg
data/
└── v13_results.csv   Current scoring snapshot
tests/                 pytest suite (scoring math, verdicts, OFF, API/HTML)
```
