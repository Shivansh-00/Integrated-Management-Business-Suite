# Deploy IBMS Enterprise on Render.com (Free Tier)

## Quick Deploy (One-Click)

Click the button below (or go to **Render Dashboard → New → Blueprint**):

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Shivansh-00/Integrated-Management-Business-Suite)

Render auto-detects `render.yaml` and provisions:
- **Web Service** — Docker-based FastAPI app (free plan, 750 hrs/month)
- **Redis** — 25 MB cache instance wired automatically

## Manual Deploy

### 1. Connect GitHub

1. Sign up / log in at [render.com](https://render.com) using your **GitHub** account.
2. Authorize Render to access `Shivansh-00/Integrated-Management-Business-Suite`.

### 2. Create via Blueprint

1. Go to **Dashboard → New → Blueprint**.
2. Select the repo → Render reads `render.yaml`.
3. Fill in the three secret environment variables when prompted:

| Variable | Where to Find |
|---|---|
| `SUPABASE_URL` | Supabase Dashboard → Settings → API → Project URL |
| `SUPABASE_KEY` | Supabase Dashboard → Settings → API → `service_role` key |
| `GROQ_API_KEY` | [console.groq.com/keys](https://console.groq.com/keys) |

> `JWT_SECRET` is auto-generated. `REDIS_URL` is auto-wired from the Redis instance.

4. Click **Apply** and wait for the build + deploy (~3-5 minutes).

### 3. Verify

```bash
curl https://<your-service>.onrender.com/api/health
```

Expected:
```json
{
  "status": "healthy",
  "version": "2.0.5",
  "redis": true,
  "supabase": true
}
```

## Environment Variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `SUPABASE_URL` | Yes | — | Supabase project URL |
| `SUPABASE_KEY` | Yes | — | `service_role` secret key |
| `JWT_SECRET` | Yes | Auto-generated | 256-bit secret for auth tokens |
| `GROQ_API_KEY` | No | — | AI Copilot (Groq LLM) |
| `REDIS_URL` | No | Auto-wired | From Render Redis instance |
| `COOKIE_SECURE` | No | `true` | HTTPS-only cookies |
| `ALLOWED_ORIGINS` | No | `*` | CORS origins (comma-separated) |
| `PORT` | No | Render sets it | Render injects `PORT=10000` automatically |

## Free Tier Limits

| Resource | Limit |
|---|---|
| Web Service | 750 hrs/month, auto-sleeps after 15 min inactivity |
| Redis | 25 MB, evicts via LRU |
| Bandwidth | 100 GB/month |
| Docker Build | 500 min/month |

> **Cold starts**: Free-tier services spin down after 15 minutes of inactivity. First request after sleep takes ~30-60 seconds.

## Update ALLOWED_ORIGINS (Post-Deploy)

Once you know the Render URL, update `ALLOWED_ORIGINS` in the Render dashboard:

```
ALLOWED_ORIGINS=https://ibms-enterprise.onrender.com
```

## Troubleshooting

| Issue | Fix |
|---|---|
| Build fails on `pip install` | Check `requirements.txt` for platform-specific packages |
| Health check fails | Verify `SUPABASE_URL` and `SUPABASE_KEY` are set correctly |
| Redis shows `false` | Check Redis instance is running in Render dashboard |
| 502 Bad Gateway | App may be starting — wait 30s and retry |
| WebSocket disconnects | Free tier sleeps; use keep-alive pings from client |
