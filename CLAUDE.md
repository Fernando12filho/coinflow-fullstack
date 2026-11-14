# CoinFlow

Flask app for tracking Bitcoin holdings. SQLite locally, Postgres on Render.
The roadmap is in `PLAN.md`; read it before starting work and keep its checkboxes current.

## Commands

```bash
venv/bin/pip install -r requirements-dev.txt   # dev + test dependencies
venv/bin/python -m pytest -q                    # run the test suite
venv/bin/python -m pytest -q --cov=app --cov-report=term-missing
flask --app app run                             # run locally at http://localhost:5000
```

Tests stub the price fetch (`bitcoin._fetch_bitcoin_price`) and use a temporary SQLite file.
Set `TEST_DATABASE_URL` to run the same suite against Postgres.

## How we work

- **One feature at a time.** Finish it, test it, get the whole suite green, then move on.
- **Tests come with every change.** Before changing existing behaviour, make sure a test
  covers it. New features ship with their own tests.
- **Fixes before features.** Work through `PLAN.md` in order.
- **Update `PLAN.md`** when a feature is done: tick it and add a short note.
- Keep changes focused on the current item; note other problems in `PLAN.md` rather than
  fixing them on the side.

## Code rules

- Money and BTC amounts use `decimal.Decimal` in new code, stored as TEXT. No floats for
  new calculations.
- Calculation logic lives in plain Python modules with no Flask imports, so it can be unit
  tested directly.
- Schema changes go in **both** `app/schema.sql` and `app/schema_postgres.sql`. Tables are
  created with `CREATE TABLE IF NOT EXISTS`; existing data must survive an app restart.
- SQL uses `?` placeholders (the Postgres wrapper in `app/db.py` converts them).
- Frontend is vanilla JS. Build DOM with `textContent`, never `innerHTML` with user data.
- **UI follows `STYLE_GUIDE.md`** ("Brushed MSX" dark theme). Use its tokens from `:root` in
  `style.css`; no new colours, fonts or font weights outside it. New screens reuse `.window`,
  `.stripe-band`, paper cards, wells, `.pill` and `.btn-primary`. Every control needs a visible
  label or `aria-label` and must show the amber focus ring.
- **Overrides to STYLE_GUIDE.md** (user request, 2026-11-14; these win over the guide):
  - Buttons are flat: no border and no box-shadow on keycaps, pills, icon buttons or popup
    buttons. Show pressed/active state with the background colour instead.
  - No stripe band under the app header, and none at the bottom of the hero (BTC / Total)
    card. Other stripe bands stay.

## satfolio

Features are modelled on satfolio (github.com/guillevc/satfolio), which is **AGPL-3.0**.
Re-implement behaviour from public exchange docs and our own design. Do not copy its code,
fixtures, or bundled price files.
