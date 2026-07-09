# GlobalPulse: Complete Cloud MVP Deployment Guide

This guide will walk you through deploying GlobalPulse to a **100% Free, Cloud-Native Architecture** using Vercel, Google Cloud Run, Supabase, and GitHub Actions.

Follow these steps precisely in order.

---

## Step 1: Set up Supabase (Database & Model Storage)

We use Supabase to host our PostgreSQL database and store our trained machine learning models.

1. **Create a Supabase Project**
   - Go to [Supabase](https://supabase.com/) and create a new project.
   - Wait for the database to provision.

2. **Get Your Database Credentials (DATABASE_URL)**
   - In your Supabase dashboard, click the **Connect** button at the top (or go to Project Settings -> Database).
   - Click the **Direct** or **ORM** tab.
   - Under **Connection Method**, select **Transaction pooler** (this is best for Cloud Run because it's serverless).
   - Leave **Type** as **URI**.
   - Scroll down and copy the connection string provided. It will look like `postgresql://postgres.xxx...`.
   - Replace `[YOUR-PASSWORD]` in that string with your actual Supabase database password.
   - *This entire string is your `DATABASE_URL`.*

3. **Get Your API Credentials**
   - Go to **Project Settings** -> **API**.
   - Copy the **Project URL**. *This is your `SUPABASE_URL`*.
   - Copy the **service_role secret**. *This is your `SUPABASE_KEY`*. (Do not use the public anon key for the backend).

4. **Create the Model Storage Bucket**
   - In the left sidebar, click **Storage**.
   - Click **New Bucket**.
   - Name it exactly: `models`
   - Make it a **Private** bucket (do not check the public option).

---

## Step 2: Create a Cron Secret Token

Your automated cron jobs (running on GitHub Actions) will securely ping your backend to trigger predictions and verifications. We need a secret token (like a password) to protect these routes so random people on the internet can't trigger them.

1. **You make this up yourself.** There is no website to generate this.
2. Just open a notepad and type a random, long string of letters and numbers. 
   - Example: `GlobalPulseSecretToken2026_xyz123`
3. Save this string in your notepad for now. 
4. *This string is your `CRON_SECRET_TOKEN`.* You will paste this exact same string into both GitHub Actions and Google Cloud Run later.

---

## Step 3: Configure GitHub Actions Secrets

GitHub needs access to your secrets so it can deploy your code and run the cron jobs.

1. Go to your GitHub Repository (`infounify94/globalpulse`).
2. Go to **Settings** -> **Secrets and variables** -> **Actions**.
3. Click **New repository secret**.
4. Add the following secrets one by one:
   - `DATABASE_URL` (Your Supabase connection string)
   - `SUPABASE_URL` (Your Supabase Project URL)
   - `SUPABASE_KEY` (Your Supabase Service Role Key)
   - `CRON_SECRET_TOKEN` (The secret you generated in Step 2)
   - `CRICAPI_KEY` (Your CricAPI key)

*(Note: We will add `API_BASE_URL` in Step 5 after deploying Cloud Run).*

---

## Step 4: Deploy the Backend to Render.com

Render.com will host your prediction API for free, and they do not require a credit card upfront.

1. Go to [Render.com](https://render.com/) and create a free account.
2. In the Render Dashboard, click **New +** and select **Web Service**.
3. Select **Build and deploy from a Git repository**.
4. Connect your GitHub account and select your repository: `infounify94/globalpulse`.
5. Under **Deployment Configuration**:
   - **Name**: `globalpulse-backend`
   - **Branch**: `master` (or `main`)
   - **Environment**: Select **Docker** (This is very important!).
   - **Instance Type**: Select **Free**.
6. Scroll down to **Environment Variables** and click **Add Environment Variable**. Add all five:
      - Key: `DATABASE_URL` | Value: (Paste the value from Step 1)
      - Key: `SUPABASE_URL` | Value: (Paste the value from Step 1)
      - Key: `SUPABASE_KEY` | Value: (Paste the value from Step 1)
      - Key: `CRICAPI_KEY` | Value: (Paste your CricAPI Key)
      - Key: `CRON_SECRET_TOKEN` | Value: (Paste the random string from Step 2)
7. Click **Create Web Service**.

*Render will now build your Docker container. This will take about 5-10 minutes. Once it says "Live", copy the URL at the top left (e.g., `https://globalpulse-backend.onrender.com`).*

---

## Step 5: Keep the Render Server Awake (Optional but Recommended)

Render's free tier goes to sleep after 15 minutes of inactivity. To prevent users from experiencing a 30-second delay when they open the app, we can use a free service to ping it every 14 minutes.

1. Go to [cron-job.org](https://cron-job.org/) and create a free account.
2. Click **Create Cronjob**.
3. **Title**: `Keep GlobalPulse Awake`
4. **URL**: Paste your Render URL from Step 4, and add `/` at the end (e.g., `https://globalpulse-backend.onrender.com/`).
5. **Execution schedule**: Set it to run every **10 minutes**.
6. Click **Create**. Now your Render server will stay active 24/7!

---

## Step 6: Link GitHub Actions to Your New Backend

Now that your backend is alive, we must tell the GitHub Actions Scheduler where it lives.

1. Copy the public URL you got from Render in Step 4.
2. Go back to your GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions**.
3. Click **New repository secret**.
4. Name: `API_BASE_URL`
5. Value: *Paste your Render URL (no trailing slash)*.

*Your `scheduler.yml` GitHub Action is now fully configured to hit your live backend every 4 hours!*

---

## Step 7: Deploy the Frontend to Vercel

Vercel will host your beautiful dashboard UI.

1. Go to [Vercel.com](https://vercel.com/) and create a free account.
2. Click **Add New Project**.
3. Import your `infounify94/globalpulse` GitHub repository.
4. **CRITICAL STEP**: Under **Root Directory**, click **Edit** and select the `frontend` folder.
5. Under **Framework Preset**, choose **Other**.
6. Click **Deploy**.

*Vercel will deploy instantly. It uses the `vercel.json` file inside your frontend folder to handle routing.*

### Final Vercel Configuration (Rewrites)
Since Vercel needs to forward `/api` requests to your Render backend, you must update the `vercel.json` file.

1. Open your code editor and go to `frontend/vercel.json`.
2. Find the lines that say: `"destination": "https://<YOUR_RAILWAY_URL>/api/$1"`
3. Replace `https://<YOUR_RAILWAY_URL>` with your **Render URL** (e.g. `https://globalpulse-backend.onrender.com`).
4. Commit and push this change to GitHub. Vercel will automatically redeploy with the correct API forwarding!

---

## Step 8: Upload the Initial Champion Model

Your backend requires a Champion Model to exist in Supabase Storage to make predictions.

Since GitHub Actions handles weekly retraining, you can trigger the first training run manually right now!

1. Go to your GitHub Repository.
2. Click the **Actions** tab at the top.
3. On the left sidebar, click **Weekly Retraining**.
4. On the right side, click the **Run workflow** dropdown button, and click **Run workflow**.

*GitHub will now spin up a runner, train your XGBoost/CatBoost models on the historical data in Supabase, and automatically upload the `.joblib` model into your Supabase `models` bucket!*

---

🎉 **Congratulations! GlobalPulse is now fully deployed, scalable, entirely stateless, and running 100% on free-tier cloud architecture!**
