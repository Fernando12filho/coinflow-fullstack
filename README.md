# CoinFlow - Bitcoin Tracker

A full-stack Flask application for tracking Bitcoin: record buys, sells and rewards, and see your break-even price, average cost and profit/loss at the live price.

## Features

- 🔐 **User Authentication**: Secure registration and login system with password hashing
- 📒 **Trade Ledger**: Record buys, sells and rewards (e.g. staking) with fees in USD or BTC, notes, and editing
- 💹 **Break-even & P/L**: Break-even price, average cost, and realized / unrealized profit and loss, all with exact decimal math
- 📈 **Price & Break-even Chart**: Daily BTC price since 2011 with your break-even line and every buy, sale and reward marked; 1M to ALL ranges
- ⚙️ **Settings**: Show amounts in USD, EUR, GBP or BRL (each trade converted at the exchange rate on its date), BTC or sats, and your number format. Export everything to CSV, or delete all your data
- 📥 **CSV Import**: Bring in your history from Kraken (Ledgers export) or Coinbase (Transaction history). See a preview first; files and trades already imported are skipped, and every row that isn't imported is listed with the reason
- 🛡️ **Consistent History**: Changes that would make your history impossible (e.g. selling BTC you didn't hold yet) are refused with a clear message
- 📧 **Newsletter Subscription**: Stay updated with Bitcoin market insights
- 💻 **Responsive Design**: "Brushed MSX" dark theme (see `STYLE_GUIDE.md`) that works from phone to desktop

## Technologies Used

### Backend
- Flask 3.1
- PostgreSQL in production, SQLite for local development
- Werkzeug (Password Hashing)
- CoinGecko API, with Coinbase as a fallback (live Bitcoin price)
- Bitstamp public OHLC API, with Kraken as a fallback (daily price history)
- European Central Bank reference rates via Frankfurter (daily USD → EUR / GBP / BRL)

### Frontend
- HTML5
- CSS3 (design tokens from `STYLE_GUIDE.md`, no web fonts)
- Vanilla JavaScript (ES6+)
- [TradingView Lightweight Charts™](https://www.tradingview.com/) 5.2.1, bundled in `app/static/vendor/` (Apache-2.0)
- Responsive Design

## Desktop app

CoinFlow also runs as an installable app that keeps everything on your computer (same pages
and login as the website). Download it from the
[Releases](https://github.com/Fernando12filho/coinflow-fullstack/releases) page:

| Computer | File |
|---|---|
| Mac with Apple Silicon (M1 or newer), macOS 11+ | `CoinFlow-<version>-macOS-arm64.dmg` |
| Mac with Intel, macOS 11+ | `CoinFlow-<version>-macOS-x64.dmg` |
| Windows 10 / 11, 64-bit | `CoinFlow-<version>-Windows-x64.zip` |
| Linux, 64-bit (experimental; needs GTK and WebKitGTK, and a recent distribution) | `CoinFlow-<version>-Linux-x64.tar.gz` |

Each file has a `.sha256` checksum next to it. Your data is stored in
`~/Library/Application Support/CoinFlow` (macOS), `%APPDATA%\CoinFlow` (Windows) or
`~/.local/share/coinflow` (Linux). The app shows "Update available" when a newer release exists.
Building and signing releases: see [RELEASING.md](RELEASING.md).

## Installation

1. **Clone the repository**
   ```bash
   cd coinflow-fullstack
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables (optional)**
   ```bash
   export SECRET_KEY=your-secret-key-here
   # Use Postgres instead of the local SQLite file:
   # export DATABASE_URL=postgresql://user:password@localhost:5432/coinflow
   ```

   Database tables are created automatically on startup.

## Running the Application

1. **Start the Flask development server**
   ```bash
   flask --app app run
   ```

2. **Open your browser**
   Navigate to `http://localhost:5000`

## Project Structure

```
coinflow-fullstack/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── auth.py              # Authentication blueprint
│   ├── bitcoin.py           # Live BTC price (CoinGecko, Coinbase fallback) and /api/bitcoin/history
│   ├── prices.py            # Daily price history: fetch (Bitstamp, Kraken fallback) and store
│   ├── fx.py                # Daily exchange rates (ECB via Frankfurter) and currency conversion
│   ├── settings.py          # Per-user settings: currency, BTC/sats, number format
│   ├── account.py           # Delete all of a user's data
│   ├── ledger.py            # Calculation engine: break-even, average cost, P/L (pure Python)
│   ├── portfolio.py         # Trade storage and the /api/trades + /api/portfolio routes
│   ├── imports.py           # /api/imports: preview, import and remove exchange CSV files
│   ├── importers/           # Kraken and Coinbase CSV parsers (pure Python)
│   ├── newsletter.py        # Newsletter blueprint
│   ├── dashboard.py         # Dashboard blueprint
│   ├── db.py                # Database utilities
│   ├── schema.sql           # Database schema (SQLite)
│   ├── schema_postgres.sql  # Database schema (PostgreSQL)
│   ├── static/
│   │   ├── css/style.css    # "Brushed MSX" theme (STYLE_GUIDE.md)
│   │   ├── img/             # Logo and icons
│   │   └── js/
│   │       ├── main.js      # Shared helpers and popups (SweetAlert2)
│   │       ├── dashboard.js # Portfolio: summary, stats, ledger, add/edit form
│   │       ├── chart.js     # Price & break-even chart
│   │       ├── import.js    # Import page: preview, import, imported files
│   │       ├── settings.js  # Settings page: save settings, delete data
│   │       └── newsletter.js
│   └── templates/
│       ├── base.html
│       ├── partials/        # App header and footer
│       ├── auth/            # Login and register (shared layout)
│       └── dashboard/       # Portfolio, import, settings and newsletter pages
├── tests/                   # Pytest suite (unit, API and browser tests)
├── coinflow_desktop.py      # Desktop app entry point (see app/launcher.py)
├── coinflow.spec            # PyInstaller build for the desktop app
├── packaging/               # Desktop icon and macOS entitlements
├── RELEASING.md             # Building, signing and publishing desktop releases
├── PLAN.md                  # Roadmap and progress
├── CLAUDE.md                # How we work on this repo
├── STYLE_GUIDE.md           # UI style guide
├── render.yaml              # Render blueprint (web service + Postgres)
├── requirements.txt         # Python dependencies
├── requirements-dev.txt     # Test dependencies
├── requirements-desktop.txt # Desktop app build dependencies
└── README.md                # This file
```

## Usage

### Registration
1. Click "Register" in the navigation
2. Fill in username, email, and password (min 8 characters)
3. Submit the form to create your account

### Login
1. Click "Login" in the navigation
2. Enter your username and password
3. Access your personal dashboard

### Track Bitcoin
1. On the dashboard, click **Add Transaction**
2. Pick **Buy**, **Sell** or **Reward**, then enter the date, BTC amount, dollars paid or received, and any fee
3. See your break-even price, average cost and profit/loss update at the live price
4. Open the **Transactions** tab to see every trade with its running break-even; edit or delete any of them

### Import from an exchange
1. Open **Import** in the navigation
2. Choose a Kraken Ledgers CSV or a Coinbase Transaction history CSV and click **Preview**
3. Check the preview: trades found, what's new, the date range, and any skipped rows with the reason
4. Click **Import**. Each imported file is listed below and can be removed with its trades

Only BTC bought, sold or earned in USD, EUR, GBP or BRL is imported, each trade in its own currency. Deposits, withdrawals and transfers are skipped: moving your own BTC doesn't change what you paid for it.

### Settings
1. Open **Settings** in the header
2. Choose the display currency (USD, EUR, GBP or BRL), BTC or sats, and the number format
3. Under **Your data**, download every trade as CSV, or type DELETE to remove all your trades, imports and settings (your account stays)

Trades are always stored in the currency they were entered in. Showing them in another currency uses the European Central Bank rate on each trade's date, so profit in reais can differ from profit in dollars.

### Newsletter
1. Enter your email on the home page or dashboard
2. Subscribe to receive Bitcoin market updates
3. Logged-in users can unsubscribe from the dashboard

## API Endpoints

### Authentication
- `GET /auth/register` - Registration page
- `POST /auth/register` - Register new user
- `GET /auth/login` - Login page
- `POST /auth/login` - Authenticate user
- `GET /auth/logout` - Logout user

### Bitcoin price
- `GET /api/bitcoin/price` - Current Bitcoin price
- `GET /api/bitcoin/history` - Daily closes since 2011 and today's change (requires auth). Missing finished days are fetched on request; the first request downloads the full history (a few seconds)

### Trades and portfolio (require auth)
- `GET /api/trades` - All trades, newest first, with running break-even, average cost and realized P/L
- `POST /api/trades` - Add a trade: `{side: buy|sell|reward, date: YYYY-MM-DD, btc, fiat, fee?, fee_asset?, currency?, notes?}` (currency defaults to the display currency; `fee_asset` is the trade currency or BTC)
- `PUT /api/trades/<id>` - Replace a trade
- `DELETE /api/trades/<id>` - Delete a trade
- `GET /api/portfolio` - Position summary: held, invested, proceeds, fees, break-even, average cost, value, total / realized / unrealized P/L

### Settings and data (require auth)
- `GET /api/settings` - Current settings and the allowed options
- `PUT /api/settings` - Change `currency` (USD, EUR, GBP, BRL), `btc_unit` (BTC, sats) and/or `locale`
- `GET /api/trades/export` - Every trade as CSV, in its original currency
- `POST /api/account/delete-data` - `{"confirm": "DELETE"}` removes all trades, imports and settings

Trades, portfolio and price history are returned in the display currency; each trade also includes `trade_currency`, `trade_fiat` and `trade_fee` as entered. When a conversion needs an exchange rate that isn't available, these return `503` with an explanation.

### Imports (require auth)
- `POST /api/imports/preview` - Upload a CSV (`file` field) and get a preview; nothing is saved
- `POST /api/imports` - Import the file's new trades (`409` if this exact file was imported before)
- `GET /api/imports` - Imported files
- `DELETE /api/imports/<id>` - Remove an import and its trades

Uploads are limited to 5 MB.

Amounts are sent and returned as decimal strings (e.g. `"0.005"`) so no precision is lost. A change that would make the history impossible is refused with `400` and an explanation.

### Newsletter API
- `POST /api/newsletter/subscribe` - Subscribe to newsletter
- `POST /api/newsletter/unsubscribe` - Unsubscribe the logged-in user (requires auth)
- `GET /api/newsletter/status` - Get subscription status (requires auth)

API routes that require auth return `401` JSON when not logged in.

## Database Schema

### Users Table
- `id` - Primary key
- `username` - Unique username
- `email` - Unique email
- `password` - Hashed password
- `created_at` - Registration timestamp

### Trades Table
- `id` - Primary key
- `user_id` - Foreign key to users
- `side` - `buy`, `sell` or `reward`
- `trade_date` - Date of the trade
- `btc_amount`, `fiat_amount`, `fee_amount` - Exact decimal amounts, stored as text
- `fee_asset` - `BTC` or the trade currency
- `currency` - Trade currency (USD)
- `source`, `import_id`, `trade_hash` - Where the trade came from (manual now; CSV import later)
- `notes` - Optional notes

### Imports Table
- `id` - Primary key
- `user_id` - Foreign key to users
- `provider` - `kraken` or `coinbase`
- `filename`, `file_hash` - The uploaded file and its SHA-256 (the same file can't be imported twice)
- `trade_count`, `date_from`, `date_to` - What the import added
- `imported_at` - When it was imported

### User Settings Table
- `user_id` - Primary key, foreign key to users
- `currency`, `btc_unit`, `locale` - Display settings (defaults: USD, BTC, automatic)

### FX Rates Table
- `currency`, `day` - Primary key (`BRL`/`EUR`/`GBP`, `YYYY-MM-DD`)
- `rate` - Units of that currency per 1 USD (ECB reference rate), exact decimal as text

### Candles Table
- `currency`, `day` - Primary key (`USD`, `YYYY-MM-DD` in UTC)
- `close` - Daily closing price, exact decimal stored as text

Shared by all users. Only finished days are stored.

Databases from older versions are migrated on startup: rows from the old `bitcoin_holding` table become buys in `trades`, and the old `bitcoin_holding` and `transaction_history` tables are dropped.

### Newsletter Subscriptions Table
- `id` - Primary key
- `user_id` - Foreign key to users (optional)
- `email` - Subscriber email
- `subscribed_at` - Subscription timestamp
- `is_active` - Subscription status

## Security Features

- Password hashing using Werkzeug
- Session-based authentication with `HttpOnly`, `SameSite=Lax` cookies (`Secure` in production)
- SQL injection prevention (parameterized queries)
- XSS protection (template auto-escaping, escaped user notes in the dashboard)
- The app refuses to start in production without a `SECRET_KEY`

## Development

### Running in Debug Mode
```bash
export FLASK_ENV=development
flask --app app run --debug
```

### Running Tests
```bash
pip install -r requirements-dev.txt
python -m pytest
# Against Postgres instead of SQLite:
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/coinflow_test python -m pytest
```

The browser tests (`tests/test_e2e_dashboard.py`) drive the dashboard in headless Chromium with
Playwright. They need a Chromium build (`playwright install chromium`, or point
`PLAYWRIGHT_CHROMIUM` at one) and are skipped when none is available. Run only them with
`python -m pytest -m e2e`, or skip them with `-m "not e2e"`.

### Resetting the Database
```bash
flask --app app init-db   # deletes all data
```

## Production Deployment

See [RENDER_DEPLOY.md](RENDER_DEPLOY.md). In short: create a Render Blueprint from this repo and it sets up the web service, a Postgres database and a `SECRET_KEY` for you.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Support

For issues and questions, please open an issue on the repository.

## Acknowledgments

- Live Bitcoin price from CoinGecko and Coinbase; daily history from Bitstamp and Kraken
- Exchange rates: European Central Bank reference rates, served by [Frankfurter](https://frankfurter.dev/)
- Charts by TradingView Lightweight Charts™, © TradingView, Inc. ([tradingview.com](https://www.tradingview.com/))
- Built with Flask and modern web technologies
