# Fix Railway Supabase Connection

## Current Status
- ✅ Local Supabase connection works
- ❌ Railway shows "Invalid API key"

## Your Local Credentials (from .env)
```
SUPABASE_URL=https://uedfxgpduaramoagiatz.supabase.co
SUPABASE_KEY=sb_secret_bdWcRv2PDxxFZNoQGXnJMg_rjDvqkml
```

## Issue Identified

Your local key starts with `sb_secret_` which might be:
1. A **secret key** (not anon key) - Railway API server needs `anon` `public` key
2. Or a different format

## Solution: Verify Railway Variables

### Step 1: Check Railway Variables
1. Go to Railway Dashboard → Your API service → **Variables**
2. Check what's set for:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`

### Step 2: Get Correct Anon Key from Supabase
1. Go to https://supabase.com/dashboard
2. Select your project
3. Go to **Project Settings** → **API**
4. Under **"Project API keys"**, find:
   - **`anon` `public`** key (this is what you need)
   - It should start with `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (JWT format)
   - NOT `sb_secret_...`

### Step 3: Update Railway Variables
1. In Railway → Variables
2. Update `SUPABASE_KEY` with the **`anon` `public`** key from Supabase
3. Make sure:
   - No quotes around the value
   - No spaces before/after
   - Exact copy from Supabase dashboard

### Step 4: Verify SUPABASE_URL
Make sure Railway has:
```
SUPABASE_URL=https://uedfxgpduaramoagiatz.supabase.co
```

## Key Format Comparison

**Correct (anon public key):**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVlZGZ4Z3BkdWFyYW1vYWdpYXR6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE2MTYyMzkwMjIsImV4cCI6MTkzMTgxNTAyMn0.abcdefghijklmnopqrstuvwxyz123456789
```

**Your local key (sb_secret):**
```
sb_secret_bdWcRv2PDxxFZNoQGXnJMg_rjDvqkml
```

**Note:** The `sb_secret_` format might work locally but Railway might need the standard JWT format `anon` key.

## After Updating

1. Railway will auto-redeploy
2. Check logs for: `Connected to Supabase database` (success!)
3. Test API: `curl https://your-api.up.railway.app/`
   - Should show: `"database": "Supabase"`

## If Still Not Working

If Railway still shows "Invalid API key" after using the anon key:

1. **Check Railway logs** - Look for exact error message
2. **Verify variable names** - Must be exactly `SUPABASE_URL` and `SUPABASE_KEY` (case-sensitive)
3. **Check for quotes/spaces** - Remove any quotes or trailing spaces
4. **Try regenerating key** in Supabase:
   - Project Settings → API
   - Regenerate the anon key
   - Copy fresh key to Railway
