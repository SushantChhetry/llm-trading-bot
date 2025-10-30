# Vercel + Railway Integration Guide

## 🔒 Repository Visibility: Public vs Private

**You do NOT need to make your repository public!**

Both Vercel and Railway support **private repositories**:

- ✅ **Railway**: Supports private GitHub repos through GitHub integration
- ✅ **Vercel**: Supports private GitHub repos (free tier included)
- ✅ **Both services**: Work identically with private repos

**When to make it public:**
- You want to open-source your project
- You want others to contribute
- You're building a portfolio piece

**Keep it private if:**
- You have API keys or sensitive config (better security)
- It's a personal project
- You want to control access

---

## 🔗 Vercel + Railway Integration Setup

### Step 1: Deploy Railway API Server

1. **Create Railway Service:**
   - Go to https://railway.app
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your private repository
   - Set root directory: `deepseek-experiment/web-dashboard`
   - Set start command: `python api_server_supabase.py`

2. **Configure Railway Environment Variables:**
   ```
   ENVIRONMENT=production
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-supabase-anon-key
   CORS_ORIGINS=https://your-app.vercel.app
   ```

3. **Get Railway Service URL:**
   - In Railway dashboard, go to your service
   - Click "Settings" → "Networking"
   - Copy the "Public Domain" (e.g., `your-api.up.railway.app`)
   - Save this URL - you'll need it for Vercel

---

### Step 2: Deploy Vercel Frontend

1. **Connect Repository to Vercel:**
   - Go to https://vercel.com
   - Click "Add New Project"
   - Import your GitHub repository (works with private repos)
   - Select the repository

2. **Configure Vercel Project:**
   - **Framework Preset**: Vite
   - **Root Directory**: `deepseek-experiment/web-dashboard`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

3. **Update `vercel.json` with Railway URL:**
   Edit `web-dashboard/vercel.json`:
   ```json
   {
     "buildCommand": "npm run build",
     "outputDirectory": "dist",
     "framework": "vite",
     "rewrites": [
       {
         "source": "/api/(.*)",
         "destination": "https://your-api.up.railway.app/api/$1"
       }
     ]
   }
   ```
   Replace `your-api.up.railway.app` with your actual Railway domain.

4. **Configure Vercel Environment Variables:**
   Go to Vercel Dashboard → Your Project → Settings → Environment Variables:
   ```
   VITE_API_URL=https://your-api.up.railway.app/api
   ```
   (Optional - if you're using environment variables in the frontend)

5. **Deploy:**
   - Click "Deploy"
   - Wait for build to complete
   - Copy your Vercel URL (e.g., `your-app.vercel.app`)

---

### Step 3: Update Railway CORS Settings

1. **Update Railway Environment Variable:**
   In Railway dashboard → Your API Service → Variables:
   ```
   CORS_ORIGINS=https://your-app.vercel.app,https://your-app-git-main.vercel.app
   ```
   Add both your production and preview deployment URLs.

2. **Redeploy Railway Service:**
   - Railway will automatically pick up the new CORS settings
   - Or manually trigger a redeploy

---

### Step 4: Verify Integration

#### Test Railway API:
```bash
# Test health endpoint
curl https://your-api.up.railway.app/health

# Test API endpoints
curl https://your-api.up.railway.app/api/status
curl https://your-api.up.railway.app/api/trades
curl https://your-api.up.railway.app/api/portfolio
```

#### Test Vercel Frontend:
1. Open your Vercel URL: `https://your-app.vercel.app`
2. Open browser DevTools (F12) → Network tab
3. Check if API calls are being made to Railway
4. Look for CORS errors in Console tab

#### Expected Behavior:
- ✅ Frontend loads successfully
- ✅ API calls go to Railway (check Network tab)
- ✅ No CORS errors in browser console
- ✅ Dashboard shows trading data

---

## 🔍 Troubleshooting

### Issue: CORS Errors
**Symptoms:** Browser console shows "CORS policy blocked"

**Solution:**
1. Check Railway `CORS_ORIGINS` includes your Vercel URL
2. Make sure Railway service is using `api_server_supabase.py` (not `api_server.py`)
3. Verify `ENVIRONMENT=production` in Railway
4. Check Railway logs: `railway logs`

### Issue: API Returns 404
**Symptoms:** Frontend can't reach Railway API

**Solution:**
1. Verify Railway service is running: `railway status`
2. Check Railway public domain is correct
3. Update `vercel.json` with correct Railway URL
4. Redeploy Vercel after updating `vercel.json`

### Issue: Frontend Build Fails
**Symptoms:** Vercel build fails

**Solution:**
1. Check build logs in Vercel dashboard
2. Ensure `package.json` has all dependencies
3. Verify Node.js version (Vercel auto-detects)
4. Check that `npm run build` works locally

### Issue: API Returns Empty Data
**Symptoms:** Dashboard loads but shows no data

**Solution:**
1. Check Supabase connection in Railway logs
2. Verify Supabase environment variables are set
3. Check if trading bot has written any trades
4. Test Railway API directly: `curl https://your-api.up.railway.app/api/trades`

---

## 📋 Integration Checklist

### Railway Setup:
- [ ] Repository connected (private is fine)
- [ ] Service created with root directory `web-dashboard`
- [ ] Start command: `python api_server_supabase.py`
- [ ] Environment variables configured:
  - [ ] `ENVIRONMENT=production`
  - [ ] `SUPABASE_URL` set
  - [ ] `SUPABASE_KEY` set
  - [ ] `CORS_ORIGINS` includes Vercel URL
- [ ] Service is running and healthy
- [ ] Public domain copied

### Vercel Setup:
- [ ] Repository connected (private is fine)
- [ ] Framework: Vite
- [ ] Root directory: `web-dashboard`
- [ ] Build command: `npm run build`
- [ ] Output directory: `dist`
- [ ] `vercel.json` updated with Railway URL
- [ ] Deployment successful

### Verification:
- [ ] Railway API responds to `/health`
- [ ] Railway API responds to `/api/status`
- [ ] Vercel frontend loads
- [ ] No CORS errors in browser
- [ ] API calls in Network tab show Railway URL
- [ ] Dashboard displays data

---

## 🔄 Automatic Deployments

Both services support automatic deployments:

### Railway:
- Automatically deploys when you push to `main` branch
- Or deploy specific branches via Railway dashboard

### Vercel:
- Automatically deploys when you push to `main` branch
- Creates preview deployments for pull requests
- Updates production on merge to `main`

**Pro Tip:** Use GitHub Actions to deploy both services together, or just push to `main` and both will deploy automatically!

---

## 📝 Quick Reference

### Railway API URL Format:
```
https://your-service-name.up.railway.app
```

### Vercel URL Format:
```
https://your-project-name.vercel.app
```

### CORS Origins Format:
```
https://your-app.vercel.app,https://your-app-git-main.vercel.app,https://your-app-git-branch-name.vercel.app
```

### Update vercel.json:
```json
{
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "https://YOUR_RAILWAY_DOMAIN/api/$1"
    }
  ]
}
```

---

## 🎯 Summary

1. **Repository can stay private** - both services support it
2. **Railway hosts API** - configure CORS with Vercel URL
3. **Vercel hosts frontend** - configure rewrites to proxy to Railway
4. **Both auto-deploy** - push to GitHub and both update

Your integration is complete when:
- Vercel frontend loads ✅
- API calls reach Railway ✅
- No CORS errors ✅
- Data displays correctly ✅

