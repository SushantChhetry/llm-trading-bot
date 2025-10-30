# Railway + Supabase Deployment Guide

## Quick Start

### Prerequisites
1. **Supabase Setup**: Your project is at https://uedfxgpduaramoagiatz.supabase.co
2. **Railway Account**: Sign up at https://railway.app and connect your GitHub account
3. **API Keys**: Get DeepSeek API key and Supabase anon key

### Step 1: Supabase Database Setup
1. Go to your Supabase project dashboard
2. Navigate to SQL Editor
3. Copy and paste contents of `scripts/supabase_schema.sql`
4. Run the SQL to create tables
5. Get your anon key from Settings > API

### Step 2: Railway Project Setup
1. Create a new Railway project:
   - Go to https://railway.app
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

### Step 3: Deploy Backend to Railway
1. **Add Backend Service**:
   - Click "+ New" → "GitHub Repo" → Select your repo
   - Railway will auto-detect the Python project
   - Set root directory to `deepseek-experiment`
   - **Add Environment Variables** (see `RAILWAY_ENV_VARS.md` for complete list):
     
     **Minimum Required:**
     ```
     ENVIRONMENT=production
     LLM_PROVIDER=deepseek
     LLM_API_KEY=your_deepseek_api_key
     LLM_MODEL=deepseek-chat
     TRADING_MODE=paper
     USE_TESTNET=true
     EXCHANGE=bybit
     SYMBOL=BTC/USDT
     LOG_LEVEL=INFO
     ```
     
     **📋 See `RAILWAY_ENV_VARS.md` for the complete list of all environment variables.**

2. **Configure Service**:
   - Set the root directory to `deepseek-experiment`
   - Railway will automatically:
     - Detect Python
     - Install dependencies from `requirements.txt`
     - Use the start command from `railway.json` or `Procfile`: `python -m src.main`
     - Run the application
   
   **Note**: The `railway.json` file is already configured with the correct start command, so Railway will automatically use it.

3. **Add API Server Service** (Optional):
   - Create another service for the API
   - Root directory: `deepseek-experiment/web-dashboard`
   - Install command: `pip install -r requirements.txt`
   - Start command: `python api_server_supabase.py`
   - Expose port: 8001
   - **Add Environment Variables:**
     ```
     ENVIRONMENT=production
     SUPABASE_URL=https://uedfxgpduaramoagiatz.supabase.co
     SUPABASE_KEY=your_supabase_anon_key
     CORS_ORIGINS=https://your-app.vercel.app
     ```

### Step 4: Deploy Frontend to Vercel
```bash
cd web-dashboard

# Install Vercel CLI
npm install -g vercel

# Login to Vercel
vercel login

# Deploy
vercel --prod

# Update CORS in api_server_supabase.py with your Vercel domain
```

## Verification

### Check Services
```bash
# Via Railway dashboard:
# - Go to https://railway.app
# - Open your project
# - Check service status (should show "Active")
# - View deployment history

# Or via Railway CLI:
railway status
railway logs
```

### Test API Endpoints
```bash
# Test API (using Railway-provided URL)
curl https://your-service.railway.app/api/status

# Check portfolio
curl https://your-service.railway.app/api/portfolio

# View trades
curl https://your-service.railway.app/api/trades
```

### Access Web Dashboard
- Vercel URL: `https://your-app.vercel.app`
- Railway API: `https://your-service.railway.app/api/`

## Monitoring

### Quick Status Check
```bash
# Via Railway dashboard:
# - Go to your project at https://railway.app
# - Click on your service
# - View logs, metrics, and deployment status

# Or via Railway CLI:
railway logs
railway status
```

### Log Files
Railway automatically collects and displays logs in the dashboard:
- Application logs: Available in Railway dashboard → Service → Logs
- Error logs: Filtered automatically in Railway dashboard
- JSON logs: Parsed and displayed in structured format

### Viewing Logs
```bash
# Via Railway CLI (install: npm i -g @railway/cli)
railway logs --tail 100

# In Railway Dashboard:
# - Go to your service
# - Click "Deployments" tab
# - Click on a deployment to view logs
# - Use filters to search for errors or specific events
```

## Maintenance

### Update Application
```bash
# With Railway, deployments are automatic via GitHub
# Just push to your main branch:
git push origin main

# Railway will automatically:
# - Build the new version
# - Run tests if configured
# - Deploy the update
# - Switch traffic to new deployment
```

### Backup Data
```bash
# Railway provides automatic backups for PostgreSQL databases
# For application data, use Railway's volume persistence feature
# Configure backups in Railway dashboard → Project → Settings → Backups
```

### Restart Services
```bash
# In Railway dashboard:
# - Go to your service
# - Click "Deployments" tab
# - Click "Redeploy" on the latest deployment

# Or via Railway CLI:
railway redeploy
```

## Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   # Check logs in Railway dashboard
   # Or via CLI:
   railway logs --tail 100
   
   # Check deployment status
   railway status
   ```

2. **API not responding**
   ```bash
   # Check Railway service URL
   curl -v https://your-service.railway.app/api/status
   
   # View service logs
   railway logs api
   ```

3. **Database connection issues**
   ```bash
   # Check Supabase connection
   python -c "from web_dashboard.supabase_client import get_supabase_service; print(get_supabase_service())"
   
   # Verify environment variables in Railway dashboard
   # Settings → Variables → Check SUPABASE_URL and SUPABASE_ANON_KEY
   ```

4. **Environment variable issues**
   ```bash
   # View environment variables (via CLI)
   railway variables
   
   # Or check in Railway dashboard:
   # Settings → Variables
   ```

5. **Deployment failures**
   ```bash
   # View build logs
   railway logs --build
   
   # Check requirements.txt is valid
   pip install -r requirements.txt --dry-run
   ```

## Cost Breakdown
- Railway Starter Plan: $5/month (includes $5 usage credit, pay-as-you-go after)
- Supabase Free Tier: $0 (500MB database, 2GB bandwidth)
- Vercel Free Tier: $0 (unlimited static sites)
- **Total: ~$5-10/month** (depending on usage)

## Security Notes
- API keys are stored in environment variables
- Database access is restricted to application
- Logs are rotated daily to prevent disk space issues
- Services restart automatically on failure
