# Railway Deployment Guide

Deploy the Alpha Arena Trading Bot to Railway - the easiest cloud deployment option.

## 🎯 Why Railway?

- ✅ **Easiest setup** - Minimal configuration
- ✅ **Automatic deployments** - Deploys on git push
- ✅ **Free tier** - $5/month credit included
- ✅ **Managed infrastructure** - No server management
- ✅ **Supabase integration** - Works seamlessly

---

## 📋 Prerequisites

1. **Supabase Setup**: Your project URL (e.g., `https://xxx.supabase.co`)
2. **Railway Account**: Sign up at https://railway.app
3. **GitHub Account**: Connect your repository
4. **API Keys**: DeepSeek API key and Supabase anon key

---

## 🚀 Step-by-Step Deployment

### Step 1: Supabase Database Setup

1. **Go to Supabase Dashboard**
   - Visit: https://supabase.com/dashboard
   - Select your project (or create new one)

2. **Initialize Database Schema**
   - Navigate to SQL Editor
   - Copy contents of `scripts/supabase_schema.sql`
   - Paste and run the SQL

3. **Get Your Keys**
   - Go to Settings → API
   - Copy your anon key
   - Copy your project URL

---

### Step 2: Railway Project Setup

1. **Create Railway Project**
   - Go to https://railway.app
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

2. **Configure Repository**
   - Railway will auto-detect your Python project
   - Set root directory to: `deepseek-experiment`
   - Railway uses `railway.json` or `Procfile` for start command

---

### Step 3: Configure Trading Bot Service

1. **Add Environment Variables**
   - Click on your service
   - Go to **Variables** tab
   - Click **+ New Variable**

2. **Minimum Required Variables**
   ```
   ENVIRONMENT=production
   LLM_PROVIDER=deepseek
   LLM_API_KEY=sk-your-deepseek-key
   LLM_MODEL=deepseek-chat
   TRADING_MODE=paper
   USE_TESTNET=true
   EXCHANGE=bybit
   SYMBOL=BTC/USDT
   LOG_LEVEL=INFO
   ```

3. **Recommended Variables**
   ```
   RUN_INTERVAL_SECONDS=150
   INITIAL_BALANCE=10000.0
   MAX_POSITION_SIZE=0.1
   MAX_LEVERAGE=10.0
   STOP_LOSS_PERCENT=2.0
   TAKE_PROFIT_PERCENT=3.0
   MAX_ACTIVE_POSITIONS=6
   MIN_CONFIDENCE_THRESHOLD=0.6
   ```

4. **Database Variables**
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your_supabase_anon_key
   DATABASE_URL=postgresql://postgres.xxx:password@db.xxx.supabase.co:5432/postgres
   ```

   **📋 See [Environment Variables Reference](../../reference/environment-variables.md) for complete list**

---

### Step 4: Deploy API Server (Optional)

If you want the web dashboard:

1. **Add New Service**
   - Click "+ New" → "GitHub Repo" → Select same repo
   - Set root directory: `deepseek-experiment/web-dashboard`
   - Set start command: `python api_server_supabase.py`
   - Expose port: 8001

2. **Add Environment Variables**
   ```
   ENVIRONMENT=production
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your_supabase_anon_key
   CORS_ORIGINS=https://your-app.vercel.app
   PORT=8001
   ```

3. **Get Public Domain** (Required for API Server)

   **Option 1: From Railway Dashboard (Recommended)**
   - Go to your service in Railway dashboard
   - Click on the **"Settings"** tab (gear icon or Settings button)
   - Scroll down to the **"Networking"** section
   - Look for **"Public Domain"**
   - Click **"Generate Domain"** if you don't have one yet
   - Your URL will look like: `your-service-name.up.railway.app`
   - **Copy this URL** - you'll need it for Vercel integration

   **Option 2: From Service Overview**
   - Click on your service in Railway dashboard
   - Look at the top of the service page
   - You should see a section showing the service URL

   **Important Notes:**
   - Railway only shows domains for active services
   - Make sure your service status is "Active" or "Running"
   - You can change the domain name later if needed

   **For detailed instructions**, see the troubleshooting section below.

---

### Step 5: Deploy Frontend to Vercel (Optional)

If you want the web dashboard frontend:

```bash
cd web-dashboard

# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy
vercel --prod
```

Update `vercel.json` with Railway API URL:
```json
{
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "https://your-api.up.railway.app/api/$1"
    }
  ]
}
```

---

## ✅ Verification

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
# Test health endpoint
curl https://your-service.railway.app/api/status

# Test portfolio
curl https://your-service.railway.app/api/portfolio

# Test trades
curl https://your-service.railway.app/api/trades
```

### Verify Bot is Running

1. Check Railway logs for startup messages
2. Look for "Starting trading bot" in logs
3. Verify database connection in logs
4. Check that trades are being generated

---

## 🔧 Configuration Details

### Root Directory

Set to: `deepseek-experiment`

### Start Command

Railway uses from `railway.json`:
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python -m src.main"
  }
}
```

Or from `Procfile`:
```
web: python -m src.main
```

### Environment Variables

See [Environment Variables Reference](../../reference/environment-variables.md) for complete reference.

---

## 📊 Monitoring

### View Logs

```bash
# Via Railway CLI
railway logs
railway logs --tail 100

# Via Dashboard
# Go to your service → View logs
```

### Health Checks

Railway automatically monitors:
- Service uptime
- Resource usage
- Deployment status

---

## 🔄 Updates

### Automatic Deployments

Railway automatically deploys when you push to connected branch:
```bash
git push origin main
# Railway automatically builds and deploys
```

### Manual Deployments

1. Go to Railway dashboard
2. Select your service
3. Click "Deployments"
4. Click "Redeploy"

---

## 🆘 Troubleshooting

### Getting Railway URL

**"I don't see a Public Domain option"**
- Make sure you're in the correct service (API server, not trading bot)
- Check that the service has been deployed at least once
- Try refreshing the page
- Ensure service status is "Active" or "Running"

**"The URL doesn't work"**
- Make sure your service is running (status should be "Active")
- Check Railway logs for any errors
- Verify the service is listening on the correct port (8001 for API server)
- Test the URL: `curl https://your-service.up.railway.app/health`

**Railway URL Format:**
```
https://your-service-name.up.railway.app
```

**Use Your Railway URL In:**
- `vercel.json` - Update the rewrites destination
- Railway Environment Variables - Set `CORS_ORIGINS` with your Vercel URL
- Testing - Use `curl` or browser to test your API endpoints

### Service Won't Start

**Symptoms**: Service shows "Failed" status

**Solutions**:
1. Check environment variables are set correctly
2. Verify `LLM_API_KEY` is valid
3. Check logs: `railway logs`
4. Ensure root directory is `deepseek-experiment`

### Build Errors

**Symptoms**: Build fails in Railway

**Solutions**:
1. Check `requirements.txt` is valid
2. Verify Python version compatibility
3. Review build logs for specific errors
4. Test locally first: `pip install -r requirements.txt`

### Database Connection Issues

**Symptoms**: Can't connect to Supabase

**Solutions**:
1. Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct
2. Check `DATABASE_URL` format (port 5432, not 6543)
3. Verify Supabase project is active
4. Check network restrictions in Supabase

### CORS Errors (API Server)

**Symptoms**: Frontend can't reach API

**Solutions**:
1. Verify `CORS_ORIGINS` includes your frontend URL
2. Check origin is exact match (no trailing slashes)
3. Ensure `ENVIRONMENT=production` is set
4. Add all Vercel preview URLs to CORS_ORIGINS

---

## 💰 Costs

### Railway Pricing

- **Free Tier**: $5/month credit included
- **Pay-as-you-go**: After credit is used
- **Typical Usage**: $5-15/month

### Cost Optimization

- Monitor usage in Railway dashboard
- Set up usage alerts
- Use mock mode for testing
- Optimize `RUN_INTERVAL_SECONDS` to reduce API calls

---

## 🔒 Security

### Best Practices

- ✅ Use Railway's encrypted environment variables
- ✅ Never commit API keys to git
- ✅ Use different keys for dev/prod
- ✅ Enable Railway audit log
- ✅ Rotate keys regularly

---

## 📋 Quick Reference

| Task | Action |
|------|--------|
| Deploy | Push to GitHub (automatic) |
| View Logs | `railway logs` or Railway dashboard |
| Restart | Railway dashboard → Redeploy |
| Update Config | Railway dashboard → Variables |
| Check Status | Railway dashboard → Service status |

---

## Related Documentation

- **[Deployment Overview](overview.md)** - Choose deployment method
- **[Environment Variables Reference](../../reference/environment-variables.md)** - Complete environment variables
- **[Vercel Integration](vercel-integration.md)** - Deploy frontend to Vercel
- **[Configuration Reference](../../reference/configuration.md)** - All settings
- **[Troubleshooting Guide](../../troubleshooting/common-issues.md)** - Common issues

---

**Last Updated**: See git history for updates.
