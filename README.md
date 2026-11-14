# CoinFlow - Bitcoin Tracker

A full-stack Flask application for tracking Bitcoin: record buys, sells and rewards, and see your break-even price, average cost and profit/loss at the live price.

## Features

- 🔐 **User Authentication**: Secure registration and login system with password hashing
- 📒 **Trade Ledger**: Record buys, sells and rewards (e.g. staking) with fees in USD or BTC, notes, and editing
- 💹 **Break-even & P/L**: Break-even price, average cost, and realized / unrealized profit and loss, all with exact decimal math
- 📥 **CSV Import**: Bring in your history from Kraken (Ledgers export) or Coinbase (Transaction history). See a preview first; files and trades already imported are skipped, and every row that isn't imported is listed with the reason
- 🛡️ **Consistent History**: Changes that would make your history impossible (e.g. selling BTC you didn't hold yet) are refused with a clear message
- 📧 **Newsletter Subscription**: Stay updated with Bitcoin market insights
- 💻 **Responsive Design**: "Brushed MSX" dark theme (see `STYLE_GUIDE.md`) that works from phone to desktop

## Technologies Used

### Backend
- Flask 3.1
- PostgreSQL in production, SQLite for local development
- Werkzeug (Password Hashing)
- CoinGecko API, with Coinbase as a fallback (Bitcoin Prices)

### Frontend
- HTML5
- CSS3 (design tokens from `STYLE_GUIDE.md`, no web fonts)
- Vanilla JavaScript (ES6+)
- Responsive Design

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
│   ├── bitcoin.py           # Live BTC price (CoinGecko, Coinbase fallback)
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
│   │       ├── import.js    # Import page: preview, import, imported files
│   │       └── newsletter.js
│   └── templates/
│       ├── base.html
│       ├── partials/        # App header and footer
│       ├── auth/            # Login and register (shared layout)
│       └── dashboard/       # Portfolio, import and newsletter pages
├── tests/                   # Pytest suite (unit, API and browser tests)
├── PLAN.md                  # Roadmap and progress
├── CLAUDE.md                # How we work on this repo
├── STYLE_GUIDE.md           # UI style guide
├── render.yaml              # Render blueprint (web service + Postgres)
├── requirements.txt         # Python dependencies
├── requirements-dev.txt     # Test dependencies
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

Only BTC bought, sold or earned in USD is imported for now. Deposits, withdrawals and transfers are skipped: moving your own BTC doesn't change what you paid for it.

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

### Trades and portfolio (require auth)
- `GET /api/trades` - All trades, newest first, with running break-even, average cost and realized P/L
- `POST /api/trades` - Add a trade: `{side: buy|sell|reward, date: YYYY-MM-DD, btc, fiat, fee?, fee_asset?: USD|BTC, notes?}`
- `PUT /api/trades/<id>` - Replace a trade
- `DELETE /api/trades/<id>` - Delete a trade
- `GET /api/portfolio` - Position summary: held, invested, proceeds, fees, break-even, average cost, value, total / realized / unrealized P/L

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

- Bitcoin price data provided by CoinGecko API
- Built with Flask and modern web technologies
