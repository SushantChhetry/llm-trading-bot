# Railway Deployment Configuration

This project uses **two separate Railway services** that share the same root directory but run different commands.

## Service Architecture

```
deepseek-experiment/          (Root directory for both services)
├── railway.json              (Trading Bot service config)
├── src/
│   └── main.py              (Trading bot entry point)
└── web-dashboard/
    ├── railway.json         (API Server service config)
    └── api_server_supabase.py (API server entry point)
```

## Service 1: Trading Bot

**Purpose**: Runs the trading bot logic

**Railway Configuration**:
- **Root Directory**: `deepseek-experiment`
- **Start Command**: `python -m src.main` (from root `railway.json`)
- **Port**: Not exposed (internal service)
- **Environment Variables**: See `RAILWAY_ENV_VARS_FORMATTED.txt`

**railway.json** (root):
```json
{
  "deploy": {
    "startCommand": "python -m src.main"
  }
}
```

## Service 2: API Server

**Purpose**: Serves REST API for the dashboard

**Railway Configuration**:
- **Root Directory**: `deepseek-experiment`
- **Start Command**: `python web-dashboard/api_server_supabase.py` (from `web-dashboard/railway.json`)
- **Port**: 8001 (exposed via Railway Public Domain)
- **Environment Variables**:
  - `ENVIRONMENT=production`
  - `SUPABASE_URL=...`
  - `SUPABASE_KEY=...`
  - `CORS_ORIGINS=https://your-app.vercel.app`

**railway.json** (web-dashboard/):
```json
{
  "deploy": {
    "startCommand": "python web-dashboard/api_server_supabase.py"
  }
}
```

## Setup Instructions

### 1. Create Trading Bot Service
1. Railway Dashboard → New Project → GitHub Repo
2. Root Directory: `deepseek-experiment`
3. Railway auto-detects `railway.json` with start command
4. Add environment variables
5. Deploy

### 2. Create API Server Service
1. Railway Dashboard → Same Project → + New → GitHub Repo
2. Root Directory: `deepseek-experiment` (same as trading bot)
3. Override Start Command: `python web-dashboard/api_server_supabase.py`
   - Or Railway will use `web-dashboard/railway.json` if detected
4. Add environment variables (different from trading bot)
5. Generate Public Domain
6. Deploy

### 3. Configure CORS
In API Server service variables:
```
CORS_ORIGINS=https://your-frontend.vercel.app
```

### 4. Update Vercel
In `web-dashboard/vercel.json`, set rewrites destination to API Server's Railway URL.

## Why This Structure?

- ✅ Both services share dependencies (`requirements.txt`)
- ✅ Both can import shared modules (`config`, `supabase_client`)
- ✅ Clear separation of concerns
- ✅ Easy to maintain and deploy

## Notes

- Both services use the same `requirements.txt` (root level)
- API server imports from parent: `from config import config`
- Railway supports per-service start command overrides
- Each service can have different environment variables
