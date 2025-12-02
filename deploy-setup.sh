#!/bin/bash

# CoinFlow Deployment Setup Script
# This script prepares your application for deployment

set -e  # Exit on error

echo "🚀 CoinFlow Deployment Setup"
echo "================================"
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install Git first."
    exit 1
fi

# Initialize git repository if not already initialized
if [ ! -d .git ]; then
    echo "📦 Initializing Git repository..."
    git init
    echo "✅ Git repository initialized"
else
    echo "✅ Git repository already exists"
fi

# Create .env.example file
echo "📝 Creating .env.example file..."
cat > .env.example << EOF
# Secret key for Flask sessions (generate with: python -c "import secrets; print(secrets.token_hex(32))")
SECRET_KEY=your-secret-key-here

# Flask environment (development or production)
FLASK_ENV=production

# Database URL (optional, defaults to SQLite)
# For PostgreSQL: postgresql://user:password@host:port/database
# DATABASE_URL=postgresql://user:password@localhost:5432/coinflow

# Application settings
FLASK_APP=app
EOF
echo "✅ .env.example created"

# Update .gitignore
echo "📝 Updating .gitignore..."
cat > .gitignore << EOF
# Python
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so

# Flask
instance/
.env

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Database
*.sqlite
*.db

# Build
dist/
build/
*.egg-info/
EOF
echo "✅ .gitignore updated"

# Generate a sample SECRET_KEY
echo ""
echo "🔐 Generating sample SECRET_KEY..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo "Your generated SECRET_KEY: $SECRET_KEY"
echo "⚠️  Save this key! You'll need it for deployment."
echo ""

# Check if requirements.txt exists and has gunicorn
if ! grep -q "gunicorn" requirements.txt; then
    echo "❌ gunicorn not found in requirements.txt"
    exit 1
fi

# Test if the app can be imported
echo "🧪 Testing application import..."
if python3 -c "from app import create_app; app = create_app(); print('✅ App import successful')"; then
    echo "✅ Application can be imported successfully"
else
    echo "❌ Failed to import application"
    exit 1
fi

# Add all files to git
echo ""
echo "📦 Adding files to git..."
git add .

# Show status
echo ""
echo "📊 Git status:"
git status

echo ""
echo "================================"
echo "✅ Setup Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Commit your changes:"
echo "   git commit -m 'Prepare for deployment'"
echo ""
echo "2. Create a GitHub repository at: https://github.com/new"
echo ""
echo "3. Push your code:"
echo "   git remote add origin https://github.com/YOUR_USERNAME/coinflow-fullstack.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "4. Choose a deployment platform:"
echo "   - Render (Recommended): https://render.com"
echo "   - Railway: https://railway.app"
echo "   - Heroku: https://heroku.com"
echo ""
echo "5. See DEPLOYMENT_GUIDE.md for detailed instructions"
echo ""
echo "🔐 Your SECRET_KEY: $SECRET_KEY"
echo "   (Save this for your deployment environment variables)"
echo ""
