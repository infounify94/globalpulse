# GlobalPulse — Cloudflare Tunnel Deployment Guide

Deploy GlobalPulse to the internet **for free** using Cloudflare Tunnels.
No domain required. No port forwarding. No VPS needed for basic usage.

---

## What This Gives You

- ✅ Public HTTPS URL (e.g. `https://globalpulse.yourdomain.com`)
- ✅ No open firewall ports
- ✅ Free Cloudflare DDoS protection
- ✅ Works from your local machine or any server

---

## Step 1: Sign Up for Cloudflare (Free)

1. Go to **https://cloudflare.com** → Create a free account
2. Add your domain (or use a Cloudflare-provided `*.trycloudflare.com` URL for zero-config)

---

## Step 2: Install cloudflared

**Windows (PowerShell):**
```powershell
winget install Cloudflare.cloudflared
```

**Or download from:** https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/

---

## Step 3: Start GlobalPulse Locally First

```bash
# Start all services with Docker Compose
docker-compose up --build

# Verify it's running
curl http://localhost:8000/health   # Should return {"status": "ok"}
# Open http://localhost:8501        # Streamlit dashboard
```

---

## Step 4A: Quick Tunnel (No Account Needed — Temporary URL)

Perfect for testing. Gives you a temporary public HTTPS URL instantly:

```bash
# Expose the Streamlit dashboard
cloudflared tunnel --url http://localhost:8501

# In a separate terminal, expose the API
cloudflared tunnel --url http://localhost:8000
```

Cloudflare prints a URL like: `https://abc123.trycloudflare.com`
Share this link with anyone — it's fully HTTPS and DDoS protected.

---

## Step 4B: Permanent Named Tunnel (Recommended for Production)

```bash
# 1. Login to Cloudflare
cloudflared tunnel login

# 2. Create a named tunnel
cloudflared tunnel create globalpulse

# 3. Create tunnel config file
# Save this to ~/.cloudflared/config.yml
```

Create the file `C:\Users\YourName\.cloudflared\config.yml`:
```yaml
tunnel: <YOUR_TUNNEL_ID>   # shown after 'tunnel create'
credentials-file: C:\Users\YourName\.cloudflared\<TUNNEL_ID>.json

ingress:
  - hostname: app.yourdomain.com
    service: http://localhost:8501
  - hostname: api.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404
```

```bash
# 4. Create DNS records in Cloudflare (auto-points your domain)
cloudflared tunnel route dns globalpulse app.yourdomain.com
cloudflared tunnel route dns globalpulse api.yourdomain.com

# 5. Run the tunnel
cloudflared tunnel run globalpulse
```

---

## Step 5: Run as a Windows Service (Auto-Start on Boot)

```powershell
# Install as a Windows service (runs even when you're not logged in)
cloudflared service install

# Start the service
Start-Service cloudflared
```

---

## Final Architecture

```
Internet → Cloudflare Edge → Cloudflare Tunnel → Your Machine
                                                      ↓
                                               Docker Compose
                                            ┌─────────────────┐
                                            │  Nginx :80/443  │
                                            │  API    :8000   │
                                            │  Dashboard:8501 │
                                            │  Postgres:5432  │
                                            └─────────────────┘
```

---

## Local Development (Without Cloudflare)

Just run:
```bash
# Start everything locally
docker-compose up --build

# Or without Docker:
python etl_run.py --all          # Import all historical data
uvicorn api:app --reload         # Start prediction API on port 8000
streamlit run dashboard/app.py   # Start dashboard on port 8501
```

Access locally:
- Dashboard: http://localhost:8501
- API Docs:  http://localhost:8000/docs
- Health:    http://localhost:8000/health
