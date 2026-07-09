# GlobalPulse Cloud MVP Deployment Guide

This guide explains how to deploy GlobalPulse to the cloud using Railway (Backend), Vercel (Frontend), and Supabase (PostgreSQL).

## 1. Supabase (Database)
You already have your Supabase PostgreSQL database up and running! We've successfully run the migration script `etl/migrate_sqlite_to_pg.py` to move the SQLite data into it. 
Keep your `SUPABASE_DB_URL` handy.

## 2. Railway (Backend & Shadow Daemon)
Railway will host the FastAPI server and run the Shadow Daemon in the background.

1. Go to [Railway.app](https://railway.app/) and create a new project.
2. Select **Deploy from GitHub repo** and select your `globalpulse` repository.
3. Once deployed, Railway might detect two services because of the `Procfile`: `web` and `worker`. If not, you can manually add the services.
4. **Environment Variables**: In your Railway project variables, add the following:
   - `DATABASE_URL` (paste your Supabase DB URL here)
   - `CRICAPI_KEY` (your CricAPI Key)
   - `GLOBALPULSE_MODE` (set to `production`)
5. Railway will automatically build the `Dockerfile` and start the FastAPI server on port 8000 and the shadow daemon worker.
6. Copy the public URL Railway generates (e.g., `globalpulse-backend.up.railway.app`).

## 3. Vercel (Frontend)
Vercel will host the sleek dashboard UI.

1. Go to [Vercel.com](https://vercel.com/) and click **Add New Project**.
2. Select your `globalpulse` repository.
3. In the project setup:
   - **Framework Preset**: Other
   - **Root Directory**: `frontend` (Important!)
4. **Environment Variables**: No environment variables are strictly needed on Vercel because we use Vercel Rewrites in `vercel.json`! 
   Wait... we DO need to configure the rewrite in `vercel.json` if the railway url is dynamic.
   If Vercel does not allow dynamic rewriting from Env Vars in `vercel.json` easily, the best practice is to set `API_BASE_URL` in `script.js` or rewrite manually.
   **Action Required**: Open `frontend/vercel.json` and replace `https://<YOUR_RAILWAY_URL>` with your actual Railway backend URL.
5. Deploy!

## 4. Automation & CI/CD
From now on, any `git push` to the `main` branch will automatically deploy your backend on Railway and your frontend on Vercel.

The Shadow Daemon now runs securely as a Railway Worker service, waking up every hour to pull upcoming matches from CricAPI, lock predictions into Supabase, and verify match results.
