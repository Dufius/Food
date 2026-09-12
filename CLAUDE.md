# food.bringon.io — CLAUDE.md

FastAPI dashboard for BringOn's v0.13 food scoring model, a barcode scanner
(Open Food Facts) for anything outside our own 29 foods, and a client-side
QUANTITY calculator (`/behoefte`, inspired by the FQQ v0.20 research
prototype). No database, no auth, no user accounts — the QUANTITY layer's
personal-data inputs never leave the browser, on purpose. See README.md for
the full picture; this file is the quick-orientation version for future
sessions.

## What NOT to do

- Don't wire the dashboard to compute v0.13 scores live unless
  `v10_spec.json` and `v10_fixtures.json` have actually landed under
  `data/` — `app/scoring.py` exists for provenance and tests, not because
  `app/main.py` calls it.
- Don't add a database, auth, or a food-entry form without checking with the
  user first — the 29-food side is deliberately read-only and stateless.
- Don't silently change `app/scoring.py`'s math — it's a verbatim port of the
  v0.13 reference implementation. Any change to the formula is a scoring
  decision, not a refactor.
- Don't drop the `canary()` test in `tests/test_scoring.py` or make it
  vacuous — that's the exact v0.12.4 regression (benefit path silently
  disconnected from the score, 9,000/20,000 tests passing vacuously) this
  repo's test discipline exists to prevent.
- **Never present Open Food Facts data, or the tier/flag/advice layer in
  `verdict.py`, as if it were the v0.13 latent score.** `off.py` and
  `verdict.py` both exist to give people a useful, honest signal
  (Topkeuze/Gemiddeld/Laagste is *relative to the category*; sugar/salt/
  fat/kcal flags are absolute; OFF data is *their* data) without
  fabricating precision the underlying model doesn't have. Don't collapse
  any of this into a single 0-100 "health score" without checking with the
  user first — that's exactly the universal ordering v0.13 explicitly
  refuses to produce.
- Don't remove the `[hidden] { display: none !important; }` rule in
  `style.css` — a same-specificity class rule loaded after it (e.g. `.btn`)
  can otherwise leave a `hidden` element visible; hit this for real with
  the scan page's "Stop camera" button.
- **Never move QUANTITY's personal-data inputs (weight, height, FFM,
  measured REE, activity, "eaten today") to the server.** `quantity.js` is
  the whole reason this app can do body-based personalization without a
  database or accounts — if a future change sends any of this to an API
  route, that's a new personal-health-data-storage system and needs the
  same "check with the user first" treatment as a database would.
- **Do not add a geography-based energy prior, or any FORM (can-this-
  person-eat-this) safety filter (allergens etc.), without checking with
  the user first.** Both were explicitly scoped out of the FQQ v0.20
  integration — geography for stereotyping risk even with a "prior, not a
  claim" framing, FORM because a false negative on an allergen is a real
  safety failure that needs a far more rigorous dataset than this project
  has. See README.md "The QUANTITY layer" for the full reasoning.
- Every QUANTITY-adjacent number is a population-average estimate
  (Katch-McArdle, Mifflin-St Jeor, EU reference intake), never measured
  metabolism. Keep the "onderzoeksprototype, geen medisch of diëtistisch
  advies" framing wherever this shows up in the UI — don't let a redesign
  quietly drop it.

## Deployment

This repo only builds and pushes the image (`.github/workflows/cd.yml` →
`ghcr.io/bringon/food`). All Swarm deployment lives in `bringon/devops`:
`docker/swarm/stacks/food/food.yml`, `release-food.yml`, `deploy-food.yml`.
Changes to routing, replicas, health checks, or the Traefik host belong
there, not here.

## Health endpoints

`/health/live`, `/health/ready`, `/health` — all identical today. Keep
`/health/live` as the one the container healthcheck targets, per the
fleet-wide convention in `bringon/devops`'s CLAUDE.md. The barcode scanner
(`app/off.py`) makes an outbound call to Open Food Facts, but that's a
per-request feature, not a startup dependency — Open Food Facts being down
must never fail these health endpoints or the container healthcheck.

## Open Food Facts integration

`app/off.py` is the only place in this app that makes an outbound network
call. It was built and unit-tested against `respx`-mocked responses shaped
like OFF's documented API schema, but **never verified end-to-end against
the live API** — the sandbox it was built in blocks egress to
`world.openfoodfacts.org` outright. Do a real scan against production (or
any environment with normal internet egress) before trusting this fully;
if OFF's actual response shape differs from the mocked fixtures in
`tests/test_off.py`, `parse_product()` is the place to fix it.
