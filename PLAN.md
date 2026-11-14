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
      the paper card uses `--ink-2` for contrast. Not yet run: an automated keyboard-only pass._

## Phase 4: Manual entry UI

- [ ] Form supports Buy / Sell / Reward, fee, notes, and editing an existing trade
- [ ] Transactions tab shows the real ledger: type, date, BTC, price/BTC, fee, running
      break-even price, realized P&L
- [ ] Dashboard shows break-even price, average cost, and realized and unrealized P&L
- [ ] Cleanup once the UI uses `/api/trades`: remove the old `/api/bitcoin/holdings` and
      `/api/bitcoin/transactions` endpoints, and drop the now-unused `bitcoin_holding` and
      `transaction_history` tables

## Phase 5: CSV import

- [ ] Exchange detection from the header row (scan the first 20 lines: Coinbase puts notes
      above the header)
- [ ] Kraken ledger parser: match up the two ledger lines of one trade, staking/earn rewards,
      KFEE fee credits worth zero, skip cancelled entries
- [ ] Coinbase transaction-history parser: Buy, Sell, rewards; skip Convert
- [ ] Preview endpoint (nothing saved): counts, date range, totals, fees, duplicate count
- [ ] Confirm endpoint with two duplicate checks: reject the same file twice (file hash),
      skip trades already stored (trade hash)
- [ ] Imports page: list imported files, remove one and its trades
- [ ] Test fixtures are our own synthetic CSVs that follow the documented formats

## Phase 6: Price history + chart

- [ ] `candles` table with daily BTC closes (we source the history ourselves)
- [ ] Fill in missing days from Kraken's public OHLC API; keep the live price from
      CoinGecko/Coinbase for "now"
- [ ] Chart (lightweight-charts, saved inside the app for offline use): price line,
      break-even line, trade markers, ranges 1M/3M/1Y/3Y/5Y/ALL, buys/sells toggle
- [ ] 24h price change on the dashboard

## Phase 7: Settings

- [ ] Display currency: USD / EUR / GBP (trades in another currency converted using
      BTC prices on the trade date)
- [ ] BTC or sats display
- [ ] Locale-aware number and date formatting
- [ ] Export the ledger to CSV
- [ ] Delete all data

## Phase 8: Installable desktop app

- [ ] pywebview window + PyInstaller builds for macOS, Windows, Linux (GitHub Actions)
- [ ] Database in the user's app-data folder
- [ ] Local mode: decide whether to drop login and the newsletter (see open decisions)
- [ ] Update check against GitHub Releases

---

## Decisions

| Decision | Status |
|---|---|
| Break-even method | **Default chosen:** show both break-even price (satfolio style) and average cost |
| Keep login, or go desktop-only? | **Open.** Login stays for now; decide at Phase 8 |
| Phase order | Fixes first, then features in the order above (user, 2026-11-14) |
| Copying satfolio code | **No.** AGPL-3.0; re-implement features only |
