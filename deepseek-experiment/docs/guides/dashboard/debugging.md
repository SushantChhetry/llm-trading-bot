# Dashboard Debugging Guide

This guide helps you debug the dashboard and API integration locally using Docker Compose or development setup.

## Quick Start

### 1. Start the Services

```bash
# From the project root directory
cd deepseek-experiment

# Start all services in development mode
docker-compose -f docker-compose.dev.yml up --build
```

This will start:
- **PostgreSQL** on port `5434`
- **API Server** on port `8001` (http://localhost:8001)
- **Frontend** on port `3000` (http://localhost:3000)

### 2. Access the Dashboard

Open your browser to: **http://localhost:3000**

The frontend will automatically proxy `/api/*` requests to the backend at `http://localhost:8001` (configured in `vite.config.ts`).

### 3. View Logs

```bash
# View all logs
docker-compose -f docker-compose.dev.yml logs -f

# View only API logs
docker-compose -f docker-compose.dev.yml logs -f api

# View only frontend logs
docker-compose -f docker-compose.dev.yml logs -f frontend
```

### 4. Test the API Directly

```bash
# Test health endpoint
curl http://localhost:8001/health

# Test API endpoints
curl http://localhost:8001/api/status
curl http://localhost:8001/api/trades
curl http://localhost:8001/api/portfolio
```

## Debugging CORS Issues

The development setup mirrors production CORS configuration:

1. **Backend CORS** (`api_server_supabase.py`):
   - Development: Allows `http://localhost:3000` and `http://127.0.0.1:3000`
   - Production: Uses regex to allow all `*.vercel.app` domains

2. **Frontend Proxy** (`vite.config.ts`):
   - Automatically proxies `/api/*` to `http://localhost:8001`
   - This bypasses CORS issues in development

### Testing CORS Manually

If you want to test CORS behavior similar to production:

```bash
# Test CORS preflight
curl -X OPTIONS http://localhost:8001/api/status \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -v

# Should return 200/204 with CORS headers
```

## Environment Variables

You can customize the setup using environment variables:

```bash
# Create a .env file or export variables
export SUPABASE_URL=your_supabase_url
export SUPABASE_KEY=your_supabase_key
export ENVIRONMENT=development

# Then start docker-compose
docker-compose -f docker-compose.dev.yml up
```

### Available Variables

**API Server:**
- `ENVIRONMENT` - Set to `development` or `production` (affects CORS)
- `PORT` - API server port (default: 8001)
- `CORS_ORIGINS` - Comma-separated list of allowed origins
- `SUPABASE_URL` - Supabase project URL (optional)
- `SUPABASE_KEY` - Supabase service key (optional)

**Frontend:**
- `VITE_API_URL` - API base URL (leave empty to use Vite proxy)

## Simulating Production Environment

To test production-like behavior locally:

### Option 1: Set ENVIRONMENT=production

```bash
# In docker-compose.dev.yml, change:
ENVIRONMENT=production

# This will enable CORS regex for Vercel domains
# You can test with curl using Vercel-like origins
```

### Option 2: Test with Direct API Calls

1. Stop the frontend container
2. Set `VITE_API_URL=http://localhost:8001` in docker-compose
3. Rebuild and start

This simulates what happens when Vercel makes direct API calls to Railway.

## Common Issues

### Frontend Can't Connect to Backend

1. **Check if API is running:**
   ```bash
   curl http://localhost:8001/health
   ```

2. **Check API logs:**
   ```bash
   docker-compose -f docker-compose.dev.yml logs api
   ```

3. **Verify CORS configuration:**
   - Check browser console for CORS errors
   - Verify `ENVIRONMENT` variable is set correctly

### Port Already in Use

```bash
# Stop existing containers
docker-compose -f docker-compose.dev.yml down

# Or change ports in docker-compose.dev.yml
```

### Changes Not Reflecting

```bash
# Rebuild containers after code changes
docker-compose -f docker-compose.dev.yml up --build

# Or restart specific service
docker-compose -f docker-compose.dev.yml restart api
```

## Stopping Services

```bash
# Stop all services
docker-compose -f docker-compose.dev.yml down

# Stop and remove volumes (fresh start)
docker-compose -f docker-compose.dev.yml down -v
```

## Production vs Development

| Aspect | Development (docker-compose.dev.yml) | Production (Railway + Vercel) |
|--------|-------------------------------------|------------------------------|
| CORS | Specific localhost origins | Regex for `*.vercel.app` |
| API URL | Vite proxy `/api/*` | Vercel rewrite or direct |
| Database | Supabase or JSON fallback | Supabase |
| Hot Reload | Yes (frontend) | No |

## Next Steps

Once everything works locally:

1. **Verify API endpoints** respond correctly
2. **Check CORS headers** in browser DevTools
3. **Test error handling** (stop API, see frontend behavior)
4. **Compare logs** with production Railway logs

If local works but production doesn't, check:
- Railway environment variables (especially `ENVIRONMENT=production`)
- Railway deployment URL in `vercel.json`
- Vercel environment variables
