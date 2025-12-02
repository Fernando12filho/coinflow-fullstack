# Render Deployment Quick Start

## Prerequisites
- GitHub account
- Render account (free): https://render.com

## Steps to Deploy on Render

### 1. Push to GitHub

```bash
# In your terminal, navigate to the project
cd /Users/fernandoguimaraes/Desktop/Fernando/coinflow/coinflow-fullstack

# Initialize git (if not done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - CoinFlow app"

# Create a new repository on GitHub: https://github.com/new
# Name it: coinflow-fullstack

# Add remote and push
git remote add origin https://github.com/YOUR_USERNAME/coinflow-fullstack.git
git branch -M main
git push -u origin main
```

### 2. Deploy on Render

1. Go to https://render.com and sign in with GitHub
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository: `coinflow-fullstack`
4. Configure the service:
   - **Name**: `coinflow-app` (or any name you prefer)
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Root Directory**: (leave blank)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn "app:create_app()"`
   - **Instance Type**: `Free`

5. Click **"Advanced"** to add environment variables:
   - Click **"Add Environment Variable"**
   - Key: `SECRET_KEY`
   - Value: Generate one with:
     ```bash
     python3 -c "import secrets; print(secrets.token_hex(32))"
     ```
   - Add another:
   - Key: `FLASK_ENV`
   - Value: `production`

6. Click **"Create Web Service"**

### 3. Wait for Deployment

Render will:
- Install dependencies
- Build your app
- Deploy it
- Give you a URL like: `https://coinflow-app.onrender.com`

**Note**: First deploy might take 5-10 minutes. Free tier apps sleep after 15 minutes of inactivity.

### 4. Initialize Database (if needed)

If your app needs database initialization, go to your service in Render:
1. Click **"Shell"** tab
2. Run: `flask --app app init-db`

### 5. Test Your App

Visit your app URL and test:
- ✅ Home page loads
- ✅ Can register new user
- ✅ Can login
- ✅ Dashboard works
- ✅ Bitcoin price updates
- ✅ Can add holdings

## Optional: Add PostgreSQL Database

### For Better Performance (Recommended for Production)

1. In Render Dashboard, click **"New +"** → **"PostgreSQL"**
2. Configure:
   - **Name**: `coinflow-db`
   - **Database**: `coinflow`
   - **User**: `coinflow`
   - **Region**: Same as your web service
   - **Plan**: `Free`
3. Click **"Create Database"**

4. In your Web Service, add environment variable:
   - Go to **"Environment"** tab
   - Click **"Add Environment Variable"**
   - Key: `DATABASE_URL`
   - Value: Copy from your PostgreSQL instance (Internal Database URL)

5. Your app will automatically use PostgreSQL instead of SQLite

## Troubleshooting

### Build Failed
- Check logs in Render dashboard
- Ensure `requirements.txt` has all dependencies
- Make sure `Procfile` exists and is correct

### App Crashes
- Check logs: Click your service → **"Logs"** tab
- Verify environment variables are set
- Ensure `SECRET_KEY` is set

### Database Issues
- If using SQLite: It persists on Render
- If using PostgreSQL: Check connection string
- Initialize database: Use Shell tab to run `flask --app app init-db`

### App is Slow
- Free tier apps sleep after 15 minutes
- First request after sleep takes ~30 seconds
- Upgrade to paid tier ($7/month) for always-on

## Updating Your App

When you make changes:

```bash
git add .
git commit -m "Your update message"
git push origin main
```

Render automatically redeploys when you push to main branch!

## Custom Domain (Optional)

1. In Render service, go to **"Settings"**
2. Scroll to **"Custom Domain"**
3. Click **"Add Custom Domain"**
4. Follow instructions to configure DNS

## Monitoring

- **Logs**: Real-time in Render dashboard
- **Metrics**: View in dashboard (CPU, Memory, Requests)
- **Alerts**: Set up email notifications for failures

## Cost

- **Free Tier**:
  - 750 hours/month free
  - Apps sleep after 15 min inactivity
  - PostgreSQL: 90 days free, then $7/month
  
- **Paid Tier**: $7/month
  - Always on
  - Better performance
  - No sleep

## Success! 🎉

Your CoinFlow app is now live and accessible to the world!

Share your URL: `https://your-app.onrender.com`

For other deployment options, see `DEPLOYMENT_GUIDE.md`
