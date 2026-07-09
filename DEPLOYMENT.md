# GlobalPulse Cloud MVP Deployment Guide

This guide explains how to deploy GlobalPulse to the cloud using Google Cloud Run (Backend API), Vercel (Frontend), Supabase (PostgreSQL & Storage), and GitHub Actions (Schedulers & CI/CD).

## 1. Supabase (Database & Model Storage)
1. Get your `DATABASE_URL`, `SUPABASE_URL`, and `SUPABASE_KEY`.
2. Create a Storage Bucket named `models` in Supabase.
3. Your Champion `.joblib` models will be uploaded here by the training pipeline.

## 2. Google Cloud Run (Backend API)
1. The backend is completely stateless. It will download the Champion model from Supabase Storage into memory at startup.
2. In Google Cloud Console, enable Cloud Run and Cloud Build APIs.
3. Configure your GitHub Actions with `GCP_CREDENTIALS`.
4. Ensure the following environment variables are set in Cloud Run:
   - `DATABASE_URL`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `CRICAPI_KEY`
   - `CRON_SECRET_TOKEN` (Create a strong random string)

## 3. GitHub Actions (Automated Workflows)
In your GitHub Repository **Settings > Secrets and variables > Actions**, add:
- `DATABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `API_BASE_URL` (Your Cloud Run API URL)
- `CRON_SECRET_TOKEN` (Matches the one in Cloud Run)

The `.github/workflows/scheduler.yml` will automatically call the backend every 4 hours to trigger predictions and verifications.

## 4. Vercel (Frontend)
1. Deploy the `frontend` folder to Vercel.
2. Set `API_BASE_URL` in `vercel.json` rewrites or just deploy and let Vercel proxy `/api` traffic to your Cloud Run URL.

## Done!
Any push to `main` will now trigger the `deploy.yml` CI/CD pipeline!
