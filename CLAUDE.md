# food.bringon.io — CLAUDE.md

Read-only FastAPI dashboard for BringOn's v0.13 food scoring model. No
database, no auth, no user-submitted data. See README.md for the full
picture; this file is the quick-orientation version for future sessions.

## What NOT to do

- Don't wire the dashboard to compute scores live unless `v10_spec.json` and
  `v10_fixtures.json` have actually landed under `data/` — `app/scoring.py`
  exists for provenance and tests, not because `app/main.py` calls it.
- Don't add a database, auth, or a food-entry form without checking with the
  user first — v1 is deliberately read-only and stateless.
- Don't silently change `app/scoring.py`'s math — it's a verbatim port of the
  v0.13 reference implementation. Any change to the formula is a scoring
  decision, not a refactor.
- Don't drop the `canary()` test in `tests/test_scoring.py` or make it
  vacuous — that's the exact v0.12.4 regression (benefit path silently
  disconnected from the score, 9,000/20,000 tests passing vacuously) this
  repo's test discipline exists to prevent.

## Deployment

This repo only builds and pushes the image (`.github/workflows/cd.yml` →
`ghcr.io/bringon/food`). All Swarm deployment lives in `bringon/devops`:
`docker/swarm/stacks/food/food.yml`, `release-food.yml`, `deploy-food.yml`.
Changes to routing, replicas, health checks, or the Traefik host belong
there, not here.

## Health endpoints

`/health/live`, `/health/ready`, `/health` — all identical today (no
external dependency exists to be "not ready" for). Keep `/health/live` as
the one the container healthcheck targets, per the fleet-wide convention in
`bringon/devops`'s CLAUDE.md.
