# CoinFlow Improvement Plan

Goal: turn CoinFlow from a demo Bitcoin tracker into a private, installable tool
people can rely on. Feature ideas are modelled on
[satfolio](https://github.com/guillevc/satfolio) (local-only Bitcoin tracker).

> **Licence rule:** satfolio is AGPL-3.0. We re-implement its *features* from
> public exchange format docs and our own design. Never copy its code or data files.

## Workflow

1. One feature at a time.
2. Every feature ships with tests. The full suite must be green before starting the next one.
3. Fixes come before new features.
4. After finishing a feature, tick it here and add a one-line note on what changed.

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done

---

## Phase 0: Baseline tests (before any change)

- [x] Run the existing suite (18 tests, all passing, 90% backend coverage)
- [x] Cover the untested paths of existing features: registration validation, login with an
      unknown username, logout, newsletter page, newsletter re-subscribe, unsubscribe with no
      subscription, subscription failure handling
      _Done: `tests/test_baseline.py` (+16 tests, 34 total), shared fixtures moved to
      `tests/conftest.py`. Backend coverage 90% → 95%. Suite also passes on Postgres 16._

## Phase 1: Fixes

- [x] **F1. Deleting an entry is not a sale.** `DELETE /api/bitcoin/holdings/<id>` used to
      record a fake `SELL` at the purchase price. A delete is a correction, so it must not write
      to the transaction history.
      _Done: SELL insert removed from `delete_holding`. The original BUY row stays in
      `transaction_history` (that table has no link to the holding); the Phase 3 ledger replaces it._
- [x] **F2. Notes are reachable.** The API accepts notes but the form had no field and the
      table never showed them. Add a notes field to the form and show notes in the table.
      _Done: notes textarea + Notes column. API now trims notes, caps them at 500 characters and
      rejects non-text (a list used to crash with a 500). Checked in a real browser: add with
      note → shown in table → delete, no console errors._
- [x] **F3. Login does not reveal which usernames exist.** Use one message for a wrong
      username or password. Raise the minimum password length from 6 to 8 characters.
      _Done: single "Invalid username or password." message; a login with no password field
      used to crash with a 500. Register form updated to `minlength="8"`. Existing accounts with
      shorter passwords can still log in._

Deferred until the decision on login is made (see Phase 8): CSRF tokens, limits on login
attempts, password reset. They are only worth doing if CoinFlow stays a hosted multi-user app.

## Phase 2: Calculation engine (`app/ledger.py`)

Pure Python, no Flask, all math in `Decimal`.

- [x] Trade sides: **Buy** (fiat → BTC), **Sell** (BTC → fiat), **Reward** (BTC received
      for free). Stored explicitly rather than worked out from the amounts: simpler for manual
      entry, and CoinFlow is BTC-only.
- [x] Fees: fiat fees add to a buy's cost or come off a sale's proceeds; BTC fees reduce the
      BTC held (satfolio instead keeps the full amount and adds the fee as cost, which
      overstates holdings)
- [x] **Break-even price** = (invested − proceeds) ÷ BTC held (goes negative once sales
      have returned more than was invested)
- [x] **Average cost** = cost basis ÷ BTC held; each sale removes cost at the current average
- [x] Total P&L, realized P&L per sale, unrealized P&L, running values per trade
- [x] Unit tests from hand-worked trade sequences + a Hypothesis property test
      _Done: `app/ledger.py`, `tests/test_ledger.py` (30 tests, 100% coverage). Finding:
      satfolio's "unrealized P&L" is `(price − break-even) × held`, which equals **total**
      P&L, so adding its per-sale realized P&L counts gains twice (buy 1 @ $100, sell 0.5 @
      $200 → shows $150 instead of $100). CoinFlow's realized + unrealized always equals total;
      the property test checks this on 200 random histories, and it is the test that catches
      the satfolio formula if it is swapped in._

## Phase 3: Trade ledger (storage + API)

- [x] New `trades` table: side, date, BTC/fiat/fee amounts, fee asset, currency, source
      (`manual`/`kraken`/`coinbase`), `import_id`, `trade_hash` (unique per user), notes.
      Amounts stored as TEXT and read as `Decimal`. In both `schema.sql` and `schema_postgres.sql`.
- [x] Existing `bitcoin_holding` rows move into `trades` as manual buys on app start (one
      transaction; safe to run again)
- [x] API: `GET/POST /api/trades`, `PUT/DELETE /api/trades/<id>` with running break-even,
      average cost and realized P&L per row. Any change that would make the history impossible
      (selling BTC not held at that date) is refused with a clear message.
- [x] `GET /api/portfolio`: held, invested, proceeds, fees, break-even, average cost, value,
      total / realized / unrealized P&L and percentages
      _Done: `app/portfolio.py`, `tests/test_trades_api.py` (+40 tests, 114 total, all passing
      on SQLite and Postgres 16). Amounts go over the API as strings so no precision is lost.
      The old `/api/bitcoin/holdings` and `/transactions` endpoints now read/write `trades`, so
      the current dashboard keeps working (checked in a browser). Migration checked on a copy
      of the local database: 0.0007 BTC @ $42,857.14 became a buy of 0.0007 BTC for exactly $30._

## Restyle: "Brushed MSX" dark theme (STYLE_GUIDE.md)

- [x] Tokens, one system font (no web fonts), brushed-metal windows, MSX stripe bands,
      paper cards, wells, keycap + pill buttons, themed SweetAlert popups
- [x] Markup: visible labels on auth forms, active nav marked with `aria-current`,
      hidden "Stripe"/"Actions" table headers, SVG close/delete icons, no emoji
- [x] JS: stripe chip per transaction row, signed +/− amounts, dialog returns focus to its trigger
      _Done: 11 markup tests added to `tests/test_app.py` (125 total). Checked in a browser at
      1280 / 860 / 390px: 0 font requests (was 9), no horizontal page scroll, no console errors.
      Fixed on the way: "Add Transaction" wrapping in its keycap, and a hidden table-header label
      widening the page on phones. Deviations from the guide: password hint says 8 characters
      (F3), table alignment uses cell classes because of the extra Notes column, loading text on
      the paper card uses `--ink-2` for contrast. Keyboard focus handling is now covered by a browser test (Phase 4c)._

## UI adjustments (user request, 2026-11-14)

- [x] Buttons are flat: no black border and no shadow (keycaps, pills, icon buttons, popups)
- [x] Removed the stripe band under the app header and the one at the bottom of the
      BTC / Total card
      _Done: CSS + two template lines. Inputs keep their border (fields, not buttons). The
      SweetAlert focus ring is now an outline instead of a shadow. Tests: markup checks in
      `tests/test_app.py` and computed-style checks for every button type in
      `tests/test_e2e_style.py`. Recorded as overrides to STYLE_GUIDE.md in CLAUDE.md._

## Phase 4: Manual entry UI

- [x] Form supports Buy / Sell / Reward, fee, notes, and editing an existing trade
      _Done (4c): segmented Buy/Sell/Reward picker, fee in USD or BTC, edit button on every row.
      Amounts go to the API exactly as typed. A refused change keeps the form open. Keyboard:
      focus moves into the form and returns to whichever button opened it (closes the gap left
      by the restyle)._
- [x] Transactions tab shows the real ledger: type, date, BTC, price/BTC, fee, running
      break-even price, realized P&L
      _Done (4b): rows come from `/api/trades`, newest first, with signed BTC amounts. Delete uses
      the new API; a delete that would break the history shows the server's explanation._
- [x] Dashboard shows break-even price, average cost, and realized and unrealized P&L
      _Done (4a): four paper stat tiles under the hero, fed by `/api/portfolio`. P&L tiles stay
      masked until "Total" is shown. A negative break-even shows "Free". Browser tests added
      (`tests/test_e2e_dashboard.py`, Playwright, skipped when no Chromium is available)._
- [x] Cleanup once the UI uses `/api/trades`: remove the old `/api/bitcoin/holdings` and
      `/api/bitcoin/transactions` endpoints, and drop the now-unused `bitcoin_holding` and
      `transaction_history` tables
      _Done (4d): old endpoints removed; schemas no longer create the old tables. On startup any
      leftover holdings move into `trades`, then both old tables are dropped (checked on Postgres
      16 and on a copy of the local database). README updated. 140 tests: 127 unit/API (pass on
      SQLite and Postgres) + 13 browser tests._

## Phase 5: CSV import

- [x] Exchange detection from the header row (scan the first 20 lines: Coinbase puts notes
      above the header)
- [x] Kraken ledger parser: match up the two ledger lines of one trade, staking/earn rewards,
      KFEE fee credits worth zero, skip cancelled entries
      _Done (5.1): `app/importers/kraken.py`. Pairs rows by `refid` (trade and "Buy Crypto"
      spend/receive), current and older layouts (XXBT/ZUSD, XBT.M), rewards from `earn`/`staking`.
      Only BTC/USD becomes a trade; deposits, withdrawals, transfers between own balances, other
      currencies and cancelled trades are skipped with a reason and line number. KFEE rows are
      skipped like any other non-BTC row._
- [x] Coinbase transaction-history parser: Buy, Sell, rewards; skip Convert
      _Done (5.2): `app/importers/coinbase.py`. Both header layouts (with/without `ID`), "$1,234.56"
      amounts, negative sale quantities, rewards (Rewards Income, Coinbase Earn, ...). Send/Receive
      and Convert are skipped with a reason._
- [x] Preview endpoint (nothing saved): counts, date range, totals, fees, duplicate count
- [x] Confirm endpoint with two duplicate checks: reject the same file twice (file hash),
      skip trades already stored (trade hash)
      _Done (5.3): `app/imports.py` + `imports` table. Preview also reports skipped rows and any
      history problem. Import saves the file record and new trades in one transaction and is
      refused for a repeated file (409), nothing new, or an impossible history. Removing an import
      is refused if a later trade depends on it. 5 MB upload limit. `tests/test_imports_api.py`
      (16 tests, SQLite and Postgres 16)._
- [x] Imports page: list imported files, remove one and its trades
      _Done (5.4): `/import` page + nav item. File picker, preview (counts, date range,
      duplicates, problem notice, expandable skipped rows), "Import N trades" disabled whenever the
      import would be refused, imported files with remove. `tests/test_e2e_import.py` (5 browser
      tests); browser fixtures moved to `tests/e2e_support.py`._
- [x] Test fixtures are our own synthetic CSVs that follow the documented formats
      _`tests/fixtures/`, written by hand; `tests/test_importers.py` (27 tests)._

## Phase 6: Price history + chart

- [x] `candles` table with daily BTC closes (we source the history ourselves)
      _Done (6a): `app/prices.py`. History from Bitstamp's public OHLC API back to 2011-08-18
      (1,000 days per request); each install downloads its own copy, nothing is bundled. Only
      finished UTC days are stored. A failed sync keeps what's stored and waits 10 minutes
      before retrying. Checked against the real API: 5,567 days in 3.6 s on first load._
- [x] Fill in missing days automatically; keep the live price from CoinGecko/Coinbase for "now"
      _Changed from the plan: Kraken's OHLC API ignores `since` and only returns the last ~720
      days, so it can't provide history. Bitstamp is the source; Kraken is a fallback used only
      when it covers the whole missing range (otherwise a permanent gap could appear)._
- [x] Chart (lightweight-charts, saved inside the app for offline use): price line,
      break-even line, trade markers, ranges 1M/3M/1Y/3Y/5Y/ALL, buys/sells toggle
      _Done (6b-c): `GET /api/bitcoin/history`; Lightweight Charts 5.2.1 vendored in
      `app/static/vendor/` (unmodified, Apache-2.0, LICENSE + NOTICE included, TradingView
      attribution logo and credit on the page). Break-even is a step line that moves at each
      trade and extends to today; a negative break-even leaves a gap. "Show trades" toggles
      the markers._
- [x] Day price change on the dashboard
      _Done (6d): "Today: +x%" in the hero, the live price against yesterday's close (00:00 UTC).
      Labelled "today" rather than "24h": a rolling 24-hour change would need hourly prices._
      _Tests: `tests/test_prices.py` (11), `tests/test_history_api.py` (6), `tests/test_e2e_chart.py`
      (4 browser tests). 211 total; 189 non-browser tests pass on SQLite and Postgres 16._

## Phase 7: Settings

- [x] Display currency: USD / EUR / GBP / **BRL** (Brazilian real, added 2026-11-14). Trades in
      another currency converted at the exchange rate on the trade date.
      _Done (7.1 + 7.3): `app/fx.py` + `fx_rates` table: ECB reference rates via Frankfurter
      (`https://api.frankfurter.dev/v1/`), one request for every business day since 2010; weekends
      use the previous business day (up to 10 days back), missing rates are refused, not guessed.
      Trades stay stored in their own currency; `/api/trades`, `/api/portfolio` and
      `/api/bitcoin/history` convert each trade at its date's rate and the live price at today's.
      New trades are entered in the display currency; edits keep the trade's own currency (the form
      shows the original amounts, labelled by code when it differs). The BTC balance check ignores
      currency, so saving works without rates; showing converted amounts without rates returns 503
      with an explanation. Checked against the real APIs (2011-08-18: $10.90 x 1.5976 = R$17.41)._
- [x] BTC or sats display
- [x] Locale-aware number and date formatting
      _Done (7.2 + 7.4): `app/settings.py` + `user_settings` table, `GET/PUT /api/settings`, Settings
      page (header link). Settings are embedded in each page; `main.js` formats money, BTC/sats,
      percentages and dates with them (Automatic = the browser's language)._
- [x] Imports keep EUR / GBP / BRL trades (7.5): Kraken and Coinbase BTC trades in any supported
      currency are imported in that currency; others are skipped with the reason.
- [x] Export the ledger to CSV
      _Done (7.6): `GET /api/trades/export`, oldest first, original amounts and currency; cells that
      would start a spreadsheet formula get a leading apostrophe._
- [x] Delete all data
      _Done (7.7): `POST /api/account/delete-data` with `{"confirm": "DELETE"}`: removes trades,
      imports and settings, keeps the account. "Your data" section on the Settings page._
      _Tests: test_fx (9), test_settings (12), test_currency_api (12), test_data_api (10),
      test_e2e_settings (5) plus updated import tests. 264 total; 236 non-browser tests pass on
      SQLite and Postgres 16._

## Phase 8: Installable desktop app

Decided 2026-11-15: the desktop app keeps login and the same pages as the website; the
website on Render stays. macOS builds are signed and notarized when the Apple Developer ID
certificate is added as GitHub secrets, unsigned otherwise. Windows/Linux builds are unsigned.

- [x] **8.1 Desktop configuration** (`app/desktop.py`): database and a persistent secret key in
      the user's app-data folder; the local server only answers requests addressed to
      127.0.0.1/localhost and ignores proxy headers (protects against DNS rebinding)
      _Done: secret key file is 0600; Flask TRUSTED_HOSTS; ProxyFix and the instance folder are
      skipped in desktop mode (a mutation check confirmed the proxy-header test catches a regression)._
- [x] **8.2 Launcher**: local server on a random free port + a native window (pywebview 6.2.1);
      a headless smoke-test mode for builds and CI
      _Done: `app/launcher.py` + `coinflow_desktop.py`. Downloads allowed (CSV export), external
      links open in the browser, private window storage (log in each launch)._
- [x] **8.3 Build** with PyInstaller 6.22.3: macOS `.app`, Windows `.exe`, Linux binary; verified
      locally on macOS
      _Done: `coinflow.spec`, `packaging/` (icon from the logo, hardened-runtime entitlements),
      `app/version.py` (1.0.0). Local build: 14 s, 30 MB, arm64, minimum macOS 11.0, smoke test
      passes, nothing written inside the bundle, HTTPS certificates bundled._
- [x] **8.4 GitHub Actions**: build and smoke-test on macOS, Windows and Linux; publish a GitHub
      Release with checksums on a version tag; sign + notarize on macOS when secrets exist
      _Done: `.github/workflows/desktop.yml` (macos-15, macos-15-intel, windows-latest,
      ubuntu-24.04) + `RELEASING.md` (secrets walkthrough). Static checks in
      `tests/test_release_workflow.py`. Linux build is experimental (needs GTK/WebKit; built on
      Ubuntu 24.04 so it needs a recent distribution)
      CI verified 2026-11-15 (run 43716081673, PR #1): tests + all four builds and their smoke
      tests pass; the first run caught that Windows has no `shasum` (checksums now use Python).
      The downloaded macOS arm64 .dmg verified against its checksum and passed the smoke test.
      Signing/notarizing still to verify once the Apple secrets are added._
- [x] **8.5 Update check** against GitHub Releases, shown in the app header
      _Done: `app/updates.py`, `GET /api/updates`; desktop only, at most every 6 hours, generic
      User-Agent, silent when offline, only github.com links. 307 tests in total._

---

## Decisions

| Decision | Status |
|---|---|
| Break-even method | **Default chosen:** show both break-even price (satfolio style) and average cost |
| Keep login, or go desktop-only? | **Keep login on desktop too**; website stays on Render (user, 2026-11-15) |
| Code signing | macOS signed + notarized via GitHub secrets when the Apple Developer ID certificate is added; unsigned until then (user, 2026-11-15) |
| Phase order | Fixes first, then features in the order above (user, 2026-11-14) |
| Copying satfolio code | **No.** AGPL-3.0; re-implement features only |
