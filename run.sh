#!/bin/bash

# Startup script for CoinFlow application

echo "🚀 Starting CoinFlow Bitcoin Tracker..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if database exists
if [ ! -f "instance/coinflow.sqlite" ]; then
    echo "🗄️  Initializing database..."
    flask --app app init-db
fi

# Set environment variables
export FLASK_APP=app
export FLASK_ENV=development

# Start the application
echo "✅ Starting Flask application..."
echo "🌐 Application will be available at http://localhost:5000"
echo ""
flask --app app run --host=0.0.0.0
