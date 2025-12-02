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
- Flask 3.0.0
- SQLite Database
- Werkzeug (Password Hashing)
- CoinGecko API (Bitcoin Prices)

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

4. **Initialize the database**
   ```bash
   flask --app app init-db
   ```

5. **Set environment variables (optional)**
   ```bash
   export FLASK_APP=app
   export FLASK_ENV=development
   export SECRET_KEY=your-secret-key-here
   ```

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
│   ├── schema.sql           # Database schema
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
├── requirements.txt         # Python dependencies
└── README.md               # This file
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
3. Unsubscribe anytime from the dashboard

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
- `POST /api/newsletter/unsubscribe` - Unsubscribe from newsletter
- `GET /api/newsletter/status` - Get subscription status (requires auth)

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
- Session-based authentication
- CSRF protection (Flask built-in)
- SQL injection prevention (parameterized queries)
- XSS protection (template auto-escaping)

## Development

### Running in Debug Mode
```bash
export FLASK_ENV=development
flask --app app run --debug
```

### Resetting the Database
```bash
flask --app app init-db
```

## Production Deployment

1. Set a strong `SECRET_KEY` environment variable
2. Use a production WSGI server (e.g., Gunicorn)
3. Configure proper database (PostgreSQL recommended)
4. Enable HTTPS
5. Set up rate limiting
6. Configure logging

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Support

For issues and questions, please open an issue on the repository.

## Acknowledgments

- Bitcoin price data provided by CoinGecko API
- Built with Flask and modern web technologies
