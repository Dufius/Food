# food.bringon.io

Read-only dashboard for BringOn's v0.13 food scoring model: category-scoped
rankings and per-portion dose facts. FastAPI + server-rendered HTML, no
database, no user input.

## What this is (v1)

- Every score is only meaningful **within its own category** — v0.13's whole
  point is refusing a universal, cross-category ordering. See `/methodologie`
  on the running app, or the docstring in `app/scoring.py`.
- The dashboard renders a fixed snapshot, `data/v13_results.csv`. It does not
  accept new food entries and does not recompute scores per-request.
- `app/scoring.py` is the ported v0.13 scoring engine (`latent()`,
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
`/health/ready`, `/health` — all identical today since this service has no
external dependency to be "not ready" for.

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
├── main.py        FastAPI routes + health endpoints
├── data.py        Loads/groups data/v13_results.csv
├── scoring.py      Ported v0.13 scoring engine (latent, dose_facts, canary)
├── templates/      Jinja2 HTML (index, category, methodology)
└── static/         style.css
data/
└── v13_results.csv  Current scoring snapshot
tests/               pytest suite (scoring math, data loading, API/HTML)
```
