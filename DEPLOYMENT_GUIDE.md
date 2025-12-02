# CoinFlow Deployment Guide

This guide covers multiple deployment options for your Flask application.

## Table of Contents
1. [Quick Deploy Options](#quick-deploy-options)
2. [Production Preparation](#production-preparation)
3. [Deploy to Render (Recommended)](#deploy-to-render)
4. [Deploy to Railway](#deploy-to-railway)
5. [Deploy to Heroku](#deploy-to-heroku)
6. [Deploy to Vercel](#deploy-to-vercel)
7. [Deploy with Docker](#deploy-with-docker)
8. [Deploy to VPS (DigitalOcean/AWS)](#deploy-to-vps)

---

## Quick Deploy Options

### 🎯 Recommended for Beginners: Render (Free Tier Available)
- ✅ Free tier available
- ✅ Easy setup
- ✅ Automatic HTTPS
- ✅ PostgreSQL included
- ✅ No credit card required

### Other Options:
- **Railway**: Modern, easy to use, free tier
- **Heroku**: Popular, requires credit card
- **Vercel**: Great for frontend, needs adapters for Flask
- **DigitalOcean/AWS**: Full control, requires more setup

---

## Production Preparation

### 1. Create Production Configuration

Create `config.py` in the `app/` directory:
```python
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
class DevelopmentConfig(Config):
    DEBUG = True
    
class ProductionConfig(Config):
    DEBUG = False
    # Use PostgreSQL in production
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
```

### 2. Update requirements.txt for Production

Add these packages:
```txt
Flask==3.0.0
Flask-Cors==4.0.0
Werkzeug==3.0.1
requests==2.31.0
click==8.1.7
gunicorn==21.2.0
psycopg2-binary==2.9.9
```

### 3. Create Procfile (for most platforms)
```
web: gunicorn "app:create_app()"
```

### 4. Create runtime.txt
```
python-3.11.7
```

### 5. Update app/__init__.py for Production

The app already has good structure, but ensure SECRET_KEY uses environment variable:
```python
SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
```

---

## Deploy to Render

### Step 1: Prepare Your Repository
```bash
cd /Users/fernandoguimaraes/Desktop/Fernando/coinflow/coinflow-fullstack
git init
git add .
git commit -m "Initial commit for deployment"
```

### Step 2: Push to GitHub
```bash
# Create a new repository on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/coinflow-fullstack.git
git branch -M main
git push -u origin main
```

### Step 3: Deploy on Render

1. Go to [render.com](https://render.com) and sign up/login
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `coinflow-app`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn "app:create_app()"`
   - **Plan**: Free

5. Add Environment Variables:
   - `SECRET_KEY`: Generate a strong key (use: `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `FLASK_ENV`: `production`

6. Click "Create Web Service"

### Step 4: Add PostgreSQL (Optional but Recommended)

1. In Render Dashboard, click "New +" → "PostgreSQL"
2. Name it `coinflow-db`
3. Select Free tier
4. Click "Create Database"
5. In your Web Service, add the database URL as environment variable:
   - Key: `DATABASE_URL`
   - Value: Copy from your PostgreSQL instance

Your app will be live at: `https://coinflow-app.onrender.com`

---

## Deploy to Railway

### Step 1: Prepare Files
```bash
cd /Users/fernandoguimaraes/Desktop/Fernando/coinflow/coinflow-fullstack
```

### Step 2: Install Railway CLI (Optional)
```bash
brew install railway
railway login
```

### Step 3: Deploy via Web UI (Easier)

1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Railway auto-detects Python and Flask
6. Add environment variables in Settings:
   - `SECRET_KEY`: Your secret key
   - `FLASK_ENV`: production

7. Railway provides PostgreSQL - add it:
   - Click "New" → "Database" → "PostgreSQL"
   - Railway auto-connects it

Your app will be live at: `https://YOUR_APP.railway.app`

---

## Deploy to Heroku

### Prerequisites
```bash
brew tap heroku/brew && brew install heroku
heroku login
```

### Step 1: Create Heroku App
```bash
cd /Users/fernandoguimaraes/Desktop/Fernando/coinflow/coinflow-fullstack
heroku create coinflow-app
```

### Step 2: Add PostgreSQL
```bash
heroku addons:create heroku-postgresql:mini
```

### Step 3: Set Environment Variables
```bash
heroku config:set SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
heroku config:set FLASK_ENV=production
```

### Step 4: Deploy
```bash
git push heroku main
```

### Step 5: Initialize Database
```bash
heroku run flask --app app init-db
```

Your app will be at: `https://coinflow-app.herokuapp.com`

---

## Deploy to Vercel

Vercel is primarily for frontend/serverless, but can work with Flask using adapters.

### Step 1: Install Vercel CLI
```bash
npm i -g vercel
```

### Step 2: Create vercel.json
```json
{
  "version": 2,
  "builds": [
    {
      "src": "app/__init__.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app/__init__.py"
    }
  ]
}
```

### Step 3: Create api/index.py (Vercel entry point)
```python
from app import create_app

app = create_app()
```

### Step 4: Deploy
```bash
vercel
```

**Note**: Vercel has limitations with SQLite. Consider using a hosted database.

---

## Deploy with Docker

### Step 1: Create Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application
COPY . .

# Create instance directory
RUN mkdir -p instance

# Expose port
EXPOSE 5000

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:create_app()"]
```

### Step 2: Create docker-compose.yml
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - SECRET_KEY=your-secret-key-here
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/coinflow
    depends_on:
      - db
    volumes:
      - ./instance:/app/instance

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=coinflow
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Step 3: Build and Run
```bash
docker-compose up --build
```

### Step 4: Deploy to Docker Hub
```bash
docker build -t yourusername/coinflow:latest .
docker push yourusername/coinflow:latest
```

Then deploy to any cloud provider that supports Docker (AWS ECS, Google Cloud Run, etc.)

---

## Deploy to VPS (DigitalOcean/AWS)

### Step 1: Set Up Server

SSH into your server:
```bash
ssh root@your-server-ip
```

### Step 2: Install Dependencies
```bash
# Update system
apt update && apt upgrade -y

# Install Python and dependencies
apt install -y python3 python3-pip python3-venv nginx supervisor postgresql postgresql-contrib

# Create app user
adduser coinflow
su - coinflow
```

### Step 3: Clone and Setup Application
```bash
cd /home/coinflow
git clone https://github.com/YOUR_USERNAME/coinflow-fullstack.git
cd coinflow-fullstack

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt gunicorn
```

### Step 4: Configure PostgreSQL
```bash
sudo -u postgres psql
CREATE DATABASE coinflow;
CREATE USER coinflow WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE coinflow TO coinflow;
\q
```

### Step 5: Configure Gunicorn with Supervisor

Create `/etc/supervisor/conf.d/coinflow.conf`:
```ini
[program:coinflow]
directory=/home/coinflow/coinflow-fullstack
command=/home/coinflow/coinflow-fullstack/venv/bin/gunicorn --workers 3 --bind unix:coinflow.sock -m 007 "app:create_app()"
user=coinflow
autostart=true
autorestart=true
stderr_logfile=/var/log/coinflow.err.log
stdout_logfile=/var/log/coinflow.out.log
environment=SECRET_KEY="your-secret-key",DATABASE_URL="postgresql://coinflow:your_password@localhost/coinflow"
```

Start supervisor:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start coinflow
```

### Step 6: Configure Nginx

Create `/etc/nginx/sites-available/coinflow`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/coinflow/coinflow-fullstack/coinflow.sock;
    }

    location /static {
        alias /home/coinflow/coinflow-fullstack/app/static;
    }
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/coinflow /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

### Step 7: Setup SSL with Let's Encrypt
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## Environment Variables Checklist

For any deployment, set these environment variables:

```bash
SECRET_KEY=<generate-strong-random-key>
FLASK_ENV=production
DATABASE_URL=<your-database-url>  # Optional, uses SQLite if not set
```

Generate SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Post-Deployment Checklist

- [ ] Application is accessible via HTTPS
- [ ] Database is properly initialized
- [ ] Environment variables are set
- [ ] Secret key is strong and unique
- [ ] Error logging is configured
- [ ] Backups are scheduled (for database)
- [ ] Domain name is configured (if applicable)
- [ ] Test all features:
  - [ ] Registration
  - [ ] Login
  - [ ] Add Bitcoin holdings
  - [ ] Newsletter subscription
  - [ ] Profit/loss calculations

---

## Monitoring and Maintenance

### Check Application Logs

**Render/Railway**: View in dashboard
**Heroku**: `heroku logs --tail`
**Docker**: `docker-compose logs -f`
**VPS**: `sudo tail -f /var/log/coinflow.out.log`

### Database Backups

**Render**: Automatic with paid plans
**Railway**: Automatic
**Heroku**: `heroku pg:backups:capture`
**VPS**: Set up cron job with pg_dump

### Update Application

```bash
git pull origin main
# Restart application (method depends on platform)
```

---

## Troubleshooting

### Application won't start
- Check logs for errors
- Verify all environment variables are set
- Ensure database connection is working

### Database connection errors
- Verify DATABASE_URL is correct
- Check if database service is running
- Ensure firewall allows connection

### Static files not loading
- Check Nginx configuration
- Verify file permissions
- Ensure CORS is properly configured

---

## Cost Comparison

| Platform | Free Tier | Paid Plans | Best For |
|----------|-----------|------------|----------|
| **Render** | ✅ Yes | $7+/month | Beginners, small apps |
| **Railway** | ✅ Limited | $5+/month | Modern workflow |
| **Heroku** | ⚠️ Limited | $5+/month | Established apps |
| **Vercel** | ✅ Yes | $20+/month | Frontend-heavy apps |
| **DigitalOcean** | ❌ No | $6+/month | Full control |
| **AWS** | ✅ Limited | Varies | Enterprise |

---

## Recommended: Start with Render

For most users, I recommend starting with **Render**:
1. Free tier available
2. Easy setup
3. Automatic deployments
4. Built-in PostgreSQL
5. Automatic HTTPS
6. No credit card required for free tier

Once you're comfortable, you can migrate to other platforms as needed.

---

## Need Help?

- Check platform-specific documentation
- Review application logs
- Test locally first with `gunicorn "app:create_app()"`
- Ensure all dependencies are in requirements.txt

Good luck with your deployment! 🚀
