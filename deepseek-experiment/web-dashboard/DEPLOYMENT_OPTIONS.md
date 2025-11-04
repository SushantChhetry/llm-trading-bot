# Railway Deployment Options - Complete Guide

## Current Status
- ❌ Error: `Dockerfile 'web-dashboard/Dockerfile' does not exist`
- 🔍 Root cause: Mismatch between Railway root directory and dockerfilePath

## Option 1: Parent Directory Root (RECOMMENDED) ⭐

### Configuration
- **Railway Root Directory**: `deepseek-experiment`
- **dockerfilePath**: `web-dashboard/Dockerfile`
- **Dockerfile**: Uses main `Dockerfile` (copies config from parent)

### Advantages
✅ Can access parent `config/` directory
✅ Shares dependencies with trading bot
✅ Clean separation of services
✅ Uses actual config module (not minimal)

### Setup Steps
1. In Railway Dashboard → API Server service → Settings → General
2. Set **Root Directory** to: `deepseek-experiment`
3. Update `railway.json`:
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "web-dashboard/Dockerfile"
  }
}
```

---

## Option 2: Web-Dashboard Root (CURRENT FIX)

### Configuration
- **Railway Root Directory**: `deepseek-experiment/web-dashboard` (or just `web-dashboard`)
- **dockerfilePath**: `Dockerfile.standalone`
- **Dockerfile**: Uses `Dockerfile.standalone` (creates minimal config)

### Advantages
✅ Works if Railway root is already set to web-dashboard
✅ Self-contained deployment
✅ No need to change Railway settings

### Disadvantages
⚠️ Creates minimal config (not full config module)
⚠️ Can't access parent directories
⚠️ Duplication of config logic

### Setup Steps
1. Keep Railway Root Directory as: `web-dashboard` (or `deepseek-experiment/web-dashboard`)
2. `railway.json` is already configured correctly:
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile.standalone"
  }
}
```

---

## How to Determine Which Option to Use

### Check Railway Root Directory:
1. Railway Dashboard → Your API Server Service
2. Settings → General tab
3. Look for "Root Directory" field

### If it shows:
- `deepseek-experiment` → Use **Option 1**
- `web-dashboard` or `deepseek-experiment/web-dashboard` → Use **Option 2** (already configured)

---

## Current Configuration (After Fix)

**railway.json** is now set for **Option 2** (web-dashboard root):
- Uses `Dockerfile.standalone`
- Works when Railway root is `web-dashboard`

**To switch to Option 1:**
1. Change Railway root to `deepseek-experiment`
2. Update `dockerfilePath` to `web-dashboard/Dockerfile`

---

## Files Overview

| File | Purpose | When to Use |
|------|---------|-------------|
| `Dockerfile` | Main Dockerfile (expects parent root) | Option 1 (root = deepseek-experiment) |
| `Dockerfile.standalone` | Standalone (works from web-dashboard) | Option 2 (root = web-dashboard) |
| `railway.json` | Railway configuration | Already configured for Option 2 |

---

## Recommendation

**If you can change Railway settings:** Use **Option 1** (parent root)
- Better architecture
- Real config module
- Cleaner separation

**If Railway root is already set to web-dashboard:** Use **Option 2** (current fix)
- No Railway changes needed
- Already configured
- Will work immediately
