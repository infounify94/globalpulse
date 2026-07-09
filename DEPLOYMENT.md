# GlobalPulse: Complete Cloud MVP Deployment Guide

This guide will walk you through deploying GlobalPulse to a **100% Free, Cloud-Native Architecture** using Vercel, Google Cloud Run, Supabase, and GitHub Actions.

Follow these steps precisely in order.

---

## Step 1: Set up Supabase (Database & Model Storage)

We use Supabase to host our PostgreSQL database and store our trained machine learning models.

1. **Create a Supabase Project**
   - Go to [Supabase](https://supabase.com/) and create a new project.
   - Wait for the database to provision.

2. **Get Your Database Credentials**
   - Go to **Project Settings** -> **Database**.
   - Under **Connection String**, copy the URI. 
   - Replace `[YOUR-PASSWORD]` with your actual password.
   - *This is your `DATABASE_URL`*.

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

## Step 2: Generate a Cron Secret Token

Your automated cron jobs (running on GitHub Actions) will securely ping your backend to trigger predictions and verifications. We need a secret token to protect these routes.

1. Generate a random, secure string (e.g., `gp_secret_998822xxYYzz!`).
2. Save this somewhere safe. *This is your `CRON_SECRET_TOKEN`*.

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

## Step 4: Deploy the Backend to Google Cloud Run

Google Cloud Run will host your prediction API for free.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g., `globalpulse-backend`).
3. Search for **Cloud Run** and enable the API.
4. Click **Create Service**.
5. Select **Continuously deploy new revisions from a source repository**.
6. Click **Set up with Cloud Build** and authorize GitHub.
7. Select your repository: `infounify94/globalpulse`.
8. Under **Build Configuration**:
   - Branch: `^master$` or `^main$` (whichever branch you are using).
   - Build Type: **Dockerfile** (Path: `/Dockerfile`).
9. Under **Authentication**, select **Allow unauthenticated invocations**.
10. Expand the **Container, Variables & Secrets, Connections, Security** section:
    - Click **Variables & Secrets**.
    - Add the following Environment Variables manually:
      - `DATABASE_URL` (Paste the value)
      - `SUPABASE_URL` (Paste the value)
      - `SUPABASE_KEY` (Paste the value)
      - `CRICAPI_KEY` (Paste the value)
      - `CRON_SECRET_TOKEN` (Paste the value)
11. Click **Create**.

*Google Cloud Run will now build and deploy your Dockerfile. This may take 3-5 minutes. Once finished, it will give you a public URL (e.g., `https://globalpulse-xxx.a.run.app`).*

---

## Step 5: Link GitHub Actions to Your New Backend

Now that your backend is alive, we must tell the GitHub Actions Scheduler where it lives.

1. Copy the public URL you got from Google Cloud Run in Step 4.
2. Go back to your GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions**.
3. Click **New repository secret**.
4. Name: `API_BASE_URL`
5. Value: *Paste your Google Cloud Run URL (no trailing slash)*.

*Your `scheduler.yml` GitHub Action is now fully configured to hit your live backend every 4 hours!*

---

## Step 6: Deploy the Frontend to Vercel

Vercel will host your beautiful dashboard UI.

1. Go to [Vercel.com](https://vercel.com/) and create a free account.
2. Click **Add New Project**.
3. Import your `infounify94/globalpulse` GitHub repository.
4. **CRITICAL STEP**: Under **Root Directory**, click **Edit** and select the `frontend` folder.
5. Under **Framework Preset**, choose **Other**.
6. Click **Deploy**.

*Vercel will deploy instantly. It uses the `vercel.json` file inside your frontend folder to handle routing.*

### Final Vercel Configuration (Rewrites)
Since Vercel needs to forward `/api` requests to your Cloud Run backend, you must update the `vercel.json` file.

1. Open your code editor and go to `frontend/vercel.json`.
2. Find the lines that say: `"destination": "https://<YOUR_RAILWAY_URL>/api/$1"`
3. Replace `https://<YOUR_RAILWAY_URL>` with your **Google Cloud Run URL**.
4. Commit and push this change to GitHub. Vercel will automatically redeploy with the correct API forwarding!

---

## Step 7: Upload the Initial Champion Model

Your backend requires a Champion Model to exist in Supabase Storage to make predictions.

Since GitHub Actions handles weekly retraining, you can trigger the first training run manually right now!

1. Go to your GitHub Repository.
2. Click the **Actions** tab at the top.
3. On the left sidebar, click **Weekly Retraining**.
4. On the right side, click the **Run workflow** dropdown button, and click **Run workflow**.

*GitHub will now spin up a runner, train your XGBoost/CatBoost models on the historical data in Supabase, and automatically upload the `.joblib` model into your Supabase `models` bucket!*

---

🎉 **Congratulations! GlobalPulse is now fully deployed, scalable, entirely stateless, and running 100% on free-tier cloud architecture!**
