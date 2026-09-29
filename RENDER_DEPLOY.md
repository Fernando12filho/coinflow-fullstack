# Deploying CoinFlow on Render

The repo includes a `render.yaml` blueprint that creates everything in one go:

- a **web service** running `gunicorn "app:create_app()"`
- a **PostgreSQL database**, wired in through `DATABASE_URL`
- a randomly generated `SECRET_KEY` and `FLASK_ENV=production`

Tables are created automatically when the app starts, so there is no database setup step.

## Steps

1. Push this repo to GitHub (`main` branch).
2. Sign in at https://dashboard.render.com with GitHub.
3. Click **New +** → **Blueprint** and pick the `coinflow-fullstack` repository.
4. Render reads `render.yaml` and shows the `coinflow` web service and the `coinflow-db` database. Click **Apply**.
5. Wait for the first deploy to finish (a few minutes), then open the `https://coinflow-xxxx.onrender.com` URL shown on the service page.

After that, every push to `main` redeploys automatically.

## Check it works

- `https://<your-app>.onrender.com/healthz` returns `{"status": "ok"}`
- Register, log in, add a holding, and check that the price and profit/loss show up
- Redeploy (or push a commit) and confirm your account and holdings are still there

## Why Postgres and not SQLite

Render's filesystem is wiped on every deploy and restart, so a SQLite file would lose all users and holdings. The app uses SQLite only when `DATABASE_URL` is not set (local development).

## Free tier limits

- The web service sleeps after 15 minutes without traffic; the first request after that takes ~30-60 seconds.
- Render's free PostgreSQL database expires 30 days after creation. Before then, either upgrade it to a paid plan or point `DATABASE_URL` at another free Postgres provider (for example Neon or Supabase) in the service's **Environment** tab.

## Troubleshooting

- **Build fails**: check the build logs. Python version comes from `.python-version`.
- **App crashes on start with `SECRET_KEY must be set`**: add a `SECRET_KEY` environment variable (generate one with `python3 -c "import secrets; print(secrets.token_hex(32))"`).
- **Price shows "Unable to load price"**: the app tries CoinGecko, then Coinbase. Check the logs for `Error fetching Bitcoin price` warnings.
- **Reset all data**: in the service's **Shell** tab run `flask --app app init-db`. This deletes every user and holding.
