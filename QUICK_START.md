# CoinFlow - Quick Start Guide

## 🎉 Your Application is Ready!

Your Flask application is now running at: **http://127.0.0.1:5000**

## 📋 Quick Start Steps

### 1. Access the Application
Open your web browser and navigate to:
```
http://localhost:5000
```

### 2. Create an Account
- Click "Register" in the navigation bar
- Fill in:
  - Username (unique)
  - Email address
  - Password (minimum 6 characters)
- Click "Register" to create your account

### 3. Login
- Click "Login" in the navigation bar
- Enter your username and password
- Click "Login" to access your dashboard

### 4. Track Bitcoin
Once logged in, you can:
- View the current Bitcoin price (updates automatically)
- Add your Bitcoin holdings:
  - Enter the amount of BTC you own
  - Enter the purchase price
  - Add optional notes
  - Click "Add Holding"
- View your portfolio summary:
  - Total Bitcoin owned
  - Total amount invested
  - Current portfolio value
  - Profit/Loss (with percentage)
- Manage holdings:
  - View all your purchases in a table
  - See individual profit/loss for each holding
  - Delete holdings when needed

### 5. Subscribe to Newsletter
- Scroll to the newsletter section on the home page or dashboard
- Enter your email address
- Click "Subscribe"
- Manage subscription from your dashboard

## 🛠️ Development Commands

### Start the Application
```bash
cd coinflow-fullstack
./venv/bin/flask --app app run
```

Or use the startup script:
```bash
./run.sh
```

### Stop the Application
Press `CTRL+C` in the terminal

### Reset Database
```bash
cd coinflow-fullstack
./venv/bin/flask --app app init-db
```

### Run with Debug Mode
```bash
cd coinflow-fullstack
./venv/bin/flask --app app run --debug
```

## 🌐 Application Structure

### Home Page (/)
- Features overview
- Current Bitcoin price display
- Newsletter subscription form
- Login and Register links

### Login (/auth/login)
- User authentication
- Username and password fields
- Link to registration

### Register (/auth/register)
- New user registration
- Username, email, and password fields
- Password confirmation
- Link to login

### Dashboard (/dashboard)
- Current Bitcoin price
- Portfolio summary with profit/loss
- Add holdings form
- Holdings management table
- Newsletter subscription status

## 📊 Features Overview

### Real-Time Bitcoin Tracking
- Fetches current Bitcoin price from CoinGecko API
- Updates every 60 seconds automatically
- Displays price in USD

### Portfolio Management
- Add multiple Bitcoin purchases
- Track different purchase prices
- Calculate individual and total profit/loss
- View transaction history

### Profit/Loss Calculator
- Automatic calculation based on current price
- Shows both dollar amount and percentage
- Color-coded (green for profit, red for loss)
- Individual holding analysis

### Newsletter System
- Email subscription management
- Subscribe/unsubscribe functionality
- User-linked subscriptions for logged-in users
- Anonymous subscriptions supported

### Security Features
- Secure password hashing (Werkzeug)
- Session-based authentication
- Protected routes (login required)
- SQL injection prevention
- XSS protection

## 🎨 UI Features

### Responsive Design
- Works on desktop, tablet, and mobile
- Adaptive layouts
- Touch-friendly buttons

### Modern Interface
- Clean, professional design
- Color-coded profit/loss indicators
- Intuitive navigation
- Real-time updates
- Alert notifications

### User Experience
- Flash messages for feedback
- Loading indicators
- Form validation
- Confirmation dialogs
- Auto-hiding alerts

## 🔧 Customization

### Change Secret Key
Edit your environment or `app/__init__.py`:
```python
SECRET_KEY='your-new-secret-key'
```

### Modify Colors
Edit `app/static/css/style.css`:
```css
:root {
    --primary-color: #f7931a;  /* Bitcoin orange */
    --success-color: #48bb78;   /* Green for profits */
    --error-color: #f56565;     /* Red for losses */
}
```

### Update Price Refresh Rate
Edit `app/static/js/dashboard.js` and `app/static/js/home.js`:
```javascript
// Change from 60000 (60 seconds) to your preferred interval
setInterval(fetchBitcoinPrice, 30000); // 30 seconds
```

## 📱 API Endpoints

### Public Endpoints
- `GET /` - Home page
- `GET /auth/login` - Login page
- `GET /auth/register` - Registration page
- `POST /api/bitcoin/price` - Get Bitcoin price
- `POST /api/newsletter/subscribe` - Subscribe to newsletter

### Protected Endpoints (Require Login)
- `GET /dashboard` - User dashboard
- `GET /api/bitcoin/holdings` - Get user holdings
- `POST /api/bitcoin/holdings` - Add new holding
- `DELETE /api/bitcoin/holdings/<id>` - Delete holding
- `GET /api/bitcoin/transactions` - Get transaction history
- `GET /api/newsletter/status` - Get subscription status
- `POST /api/newsletter/unsubscribe` - Unsubscribe

## 🐛 Troubleshooting

### Application won't start
- Make sure virtual environment is activated
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify database is initialized: `flask --app app init-db`

### Can't access database
- Check that `instance/` directory exists
- Re-initialize database: `flask --app app init-db`

### Bitcoin price not loading
- Check internet connection
- CoinGecko API might be rate-limited (free tier limits)
- Check browser console for errors

### Login issues
- Verify username and password are correct
- Check that cookies are enabled
- Clear browser cache and try again

## 📞 Support

For issues or questions:
1. Check the main README.md
2. Review the code documentation
3. Check browser console for JavaScript errors
4. Check Flask terminal output for Python errors

## 🎯 Next Steps

Now that your application is running, you can:
1. Create your first user account
2. Add some Bitcoin holdings
3. Watch real-time profit/loss calculations
4. Subscribe to the newsletter
5. Customize the styling to match your preferences
6. Add more features as needed

Enjoy tracking your Bitcoin investments! 🚀
