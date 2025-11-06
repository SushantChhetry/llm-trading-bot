# Railway Deployment Configuration

This project uses **three separate Railway services** that share the same root directory but run different commands. All services use **Railpack** (Railway's default builder) which auto-detects Python projects and eliminates Dockerfile complexity.

## How Railway Differentiates Services

**Key Point**: Railway differentiates services by the **location** of their `railway.json` files, even when both share the same root directory.

- **Trading Bot**: Uses `deepseek-experiment/railway.json` (root level)
- **Risk Service**: Uses `deepseek-experiment/services/railway.json` (subdirectory)
- **API Server**: Uses `deepseek-experiment/web-dashboard/railway.json` (subdirectory)

Both services can have the same root directory (`deepseek-experiment`) because Railway automatically finds the correct config file based on its location.

## Service Architecture

```
deepseek-experiment/          (Root directory for all services)
├── railway.json              (Trading Bot service config - uses Railpack)
├── src/
│   └── main.py              (Trading bot entry point)
├── services/
│   ├── railway.json         (Risk Service config - uses Railpack)
│   ├── risk_service.py       (Risk service entry point)
│   └── risk_daemon.py        (Risk daemon - optional background process)
└── web-dashboard/
    ├── railway.json         (API Server service config)
    └── api_server_supabase.py (API server entry point)
```

## Service 1: Trading Bot

**Purpose**: Runs the trading bot logic

**Railway Configuration**:
- **Service Name**: `trading-bot` (or your preferred name)
- **Root Directory**: `deepseek-experiment`
- **Builder**: **Railpack** (default) - auto-detects Python project
- **Config File**: Railway auto-detects `deepseek-experiment/railway.json` (root level)
- **Start Command**: `python -m src.main` (from root `railway.json`)
- **Port**: Not exposed (internal service)
- **Environment Variables**: 
  - `RISK_SERVICE_URL=http://risk-service.railway.internal:8003` (for private networking)
  - See `RAILWAY_ENV_VARS_FORMATTED.txt` for other variables

**railway.json** (root):
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "RAILPACK"
  },
  "deploy": {
    "startCommand": "python -m src.main",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10,
    "sleepApplication": false,
    "numReplicas": 1
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
2. **Service Name**: `trading-bot` (important for service discovery)
3. **Root Directory**: `deepseek-experiment`
4. **Builder**: Set to **Railpack** (or leave as default) - remove any Dockerfile configuration
5. Railway auto-detects `railway.json` in root with start command
6. **Environment Variables**: 
   - `RISK_SERVICE_URL=http://risk-service.railway.internal:8003` (service name must match!)
   - Add other required variables (see `RAILWAY_ENV_VARS_FORMATTED.txt`)
7. Deploy

### 2. Create Risk Service
1. Railway Dashboard → Same Project → + New → GitHub Repo
2. **Service Name**: `risk-service` (must match hostname in RISK_SERVICE_URL)
3. **Root Directory**: `deepseek-experiment` (same as trading bot!)
4. **Builder**: Set to **Railpack** (or leave as default) - remove any Dockerfile configuration
5. Railway auto-detects `services/railway.json` in subdirectory
6. **Environment Variables**:
   - `RISK_SERVICE_PORT=8003` (optional, defaults to 8003)
   - No other required variables (uses defaults)
7. Generate Public Domain (optional, for external access)
8. Deploy

**Note**: The trading bot connects to the risk service using the `RISK_SERVICE_URL` environment variable. When deployed as separate services, use Railway's private networking: `http://risk-service.railway.internal:8003`. The service name (`risk-service`) becomes the hostname for private networking.

### 3. Create API Server Service
1. Railway Dashboard → Same Project → + New → GitHub Repo
2. Root Directory: `deepseek-experiment` (same as trading bot)
3. Override Start Command: `python web-dashboard/api_server_supabase.py`
   - Or Railway will use `web-dashboard/railway.json` if detected
4. Add environment variables (different from trading bot)
5. Generate Public Domain
6. Deploy

### 4. Configure Risk Service Connection
In Trading Bot service environment variables:
```
RISK_SERVICE_URL=http://risk-service.railway.internal:8003
```

**Important**: The service name in Railway (`risk-service`) becomes the hostname for private networking. Make sure the service name matches the hostname in the URL.

If using public domain instead of private networking:
```
RISK_SERVICE_URL=https://your-risk-service.up.railway.app
```

### 5. Configure CORS
In API Server service variables:
```
CORS_ORIGINS=https://your-frontend.vercel.app
```

### 6. Update Vercel
In `web-dashboard/vercel.json`, set rewrites destination to API Server's Railway URL.

## Why This Structure?

- ✅ Both services share dependencies (`requirements.txt`)
- ✅ Both can import shared modules (`config`, `supabase_client`)
- ✅ Clear separation of concerns
- ✅ Easy to maintain and deploy
- ✅ No Dockerfile needed - Railpack auto-detects Python projects
- ✅ Simpler configuration - just `railway.json` files

## Why Railpack?

- ✅ Railway's **default** app builder (recommended, not deprecated)
- ✅ Auto-detects Python projects and uses `requirements.txt`
- ✅ No Dockerfile needed - eliminates path configuration issues
- ✅ Better integration with Railway's platform
- ✅ More reliable builds without Dockerfile complexity

## Notes

- All services use the same `requirements.txt` (root level)
- API server imports from parent: `from config import config`
- Railway automatically finds the correct `railway.json` based on file location
- Each service can have different environment variables
- Service names in Railway become hostnames for private networking (e.g., `risk-service` → `http://risk-service.railway.internal:8003`)

## Optional: Watch Paths for Optimization

To prevent unnecessary rebuilds, you can configure watch paths in Railway:
- **Trading Bot**: Watch `["src/**", "railway.json", "requirements.txt"]`
- **Risk Service**: Watch `["services/**", "requirements.txt"]`
- **API Server**: Watch `["web-dashboard/**", "requirements.txt"]`

This ensures each service only rebuilds when its relevant code changes.
