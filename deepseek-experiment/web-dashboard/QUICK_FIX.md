# Quick Fix for Railway Dockerfile Error

## The Problem
Railway can't find `web-dashboard/Dockerfile`. This happens when the `dockerfilePath` doesn't match Railway's root directory setting.

## Immediate Fix (Choose One)

### Option A: Railway Root = `deepseek-experiment` (Parent Directory) ✅ RECOMMENDED

**In Railway Dashboard:**
1. Go to your API Server service
2. Settings → General → Root Directory
3. Set to: `deepseek-experiment`
4. Save

**railway.json** (already correct):
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "web-dashboard/Dockerfile"
  }
}
```

**Why this is better:**
- ✅ Can access parent `config/` directory
- ✅ Uses the main Dockerfile which copies config properly
- ✅ Better for shared dependencies

---

### Option B: Railway Root = `web-dashboard` (Current Directory)

**Keep Railway root as:** `web-dashboard`

**Update railway.json:**
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile.standalone"
  }
}
```

**Why this works:**
- Uses standalone Dockerfile that creates minimal config
- Works when root is already set to web-dashboard

---

## How to Check Your Current Railway Root

1. Go to Railway Dashboard
2. Select your API Server service
3. Click "Settings" tab
4. Look for "Root Directory" in General settings
5. Note what it says

## After Applying Fix

1. Commit and push changes
2. Railway will automatically redeploy
3. Check build logs to confirm Dockerfile is found
