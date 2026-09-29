# CoinFlow - Bitcoin Tracker

A full-stack Flask application for tracking Bitcoin investments with real-time price monitoring, profit/loss calculations, and newsletter subscriptions.

## Features

- 🔐 **User Authentication**: Secure registration and login system with password hashing
- 📊 **Bitcoin Tracking**: Monitor your Bitcoin holdings with real-time price updates
- 💹 **Profit/Loss Calculator**: Automatic calculation of gains and losses
- 📧 **Newsletter Subscription**: Stay updated with Bitcoin market insights
- 💻 **Responsive Design**: Beautiful UI that works on all devices

## Technologies Used

### Backend
- Flask 3.1
- PostgreSQL in production, SQLite for local development
- Werkzeug (Password Hashing)
- CoinGecko API, with Coinbase as a fallback (Bitcoin Prices)

### Frontend
- HTML5
- CSS3 (Custom styling with CSS variables)
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
│   ├── bitcoin.py           # Bitcoin tracking blueprint
│   ├── newsletter.py        # Newsletter blueprint
│   ├── dashboard.py         # Dashboard blueprint
│   ├── db.py                # Database utilities
│   ├── schema.sql           # Database schema (SQLite)
│   ├── schema_postgres.sql  # Database schema (PostgreSQL)
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css    # Main stylesheet
│   │   └── js/
│   │       ├── main.js      # Common JavaScript
│   │       ├── home.js      # Home page scripts
│   │       ├── register.js  # Registration scripts
│   │       └── dashboard.js # Dashboard scripts
│   └── templates/
│       ├── base.html        # Base template
│       ├── home/
│       │   └── index.html   # Home page
│       ├── auth/
│       │   ├── login.html   # Login page
│       │   └── register.html # Registration page
│       └── dashboard/
│           └── index.html   # Dashboard page
├── tests/                   # Pytest suite
├── render.yaml              # Render blueprint (web service + Postgres)
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Usage

### Registration
1. Click "Register" in the navigation
2. Fill in username, email, and password (min 6 characters)
3. Submit the form to create your account

### Login
1. Click "Login" in the navigation
2. Enter your username and password
3. Access your personal dashboard

### Track Bitcoin
1. On the dashboard, add your Bitcoin holdings
2. Enter the amount of BTC and purchase price
3. View real-time profit/loss calculations
4. Delete holdings as needed

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

### Bitcoin API
- `GET /api/bitcoin/price` - Get current Bitcoin price
- `GET /api/bitcoin/holdings` - Get user's holdings (requires auth)
- `POST /api/bitcoin/holdings` - Add new holding (requires auth)
- `DELETE /api/bitcoin/holdings/<id>` - Delete holding (requires auth)
- `GET /api/bitcoin/transactions` - Get transaction history (requires auth)

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

### Bitcoin Holdings Table
- `id` - Primary key
- `user_id` - Foreign key to users
- `amount` - Amount of BTC
- `purchase_price` - Price at purchase
- `purchase_date` - Purchase timestamp
- `notes` - Optional notes

### Newsletter Subscriptions Table
- `id` - Primary key
- `user_id` - Foreign key to users (optional)
- `email` - Subscriber email
- `subscribed_at` - Subscription timestamp
- `is_active` - Subscription status

### Transaction History Table
- `id` - Primary key
- `user_id` - Foreign key to users
- `transaction_type` - BUY or SELL
- `amount` - Transaction amount
- `price` - Price at transaction
- `total_value` - Total transaction value
- `transaction_date` - Transaction timestamp

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
pip install pytest
python -m pytest
# Against Postgres instead of SQLite:
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/coinflow_test python -m pytest
```

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
