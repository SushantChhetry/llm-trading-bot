# How to Find Supabase Credentials

## Step 1: Get Supabase URL and Key

1. **Go to Supabase Dashboard**
   - Visit: https://supabase.com/dashboard
   - Sign in and select your project

2. **Get SUPABASE_URL**
   - Click **Project Settings** (gear icon in left sidebar)
   - Click **API** in the left menu
   - Under **"Project URL"**, you'll see something like:
     ```
     https://abcdefghijklmnop.supabase.co
     ```
   - **Copy this entire URL** - this is your `SUPABASE_URL`

3. **Get SUPABASE_KEY**
   - Still in **Project Settings → API**
   - Under **"Project API keys"**, you'll see:
     - **`anon` `public`** key (this is what you need)
     - **`service_role` `secret`** key (don't use this for API server)
   - Click the **eye icon** or **copy icon** next to `anon` `public`
   - **Copy this key** - it will look like:
     ```
     eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2RlZmdoaWprbG1ub3AiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTYxNjIzOTAyMiwiZXhwIjoxOTMxODE1MDIyfQ.abcdefghijklmnopqrstuvwxyz123456789
     ```
   - This is your `SUPABASE_KEY`

## Step 2: Add to Railway

1. **Go to Railway Dashboard**
   - Navigate to your API service

2. **Add Variables**
   - Click **Variables** tab
   - Click **+ New Variable**
   - Add:
     - **Name**: `SUPABASE_URL`
     - **Value**: `https://your-project-id.supabase.co` (paste your URL)
     - Click **Add**

   - Click **+ New Variable** again
   - Add:
     - **Name**: `SUPABASE_KEY`
     - **Value**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (paste your key)
     - Click **Add**

3. **Important Notes:**
   - ❌ **NO quotes** - Don't add quotes around the values
   - ❌ **NO spaces** - Make sure there are no trailing spaces
   - ✅ **Exact format** - Copy exactly from Supabase dashboard
   - ✅ **Case sensitive** - Variable names must be exactly: `SUPABASE_URL` and `SUPABASE_KEY`

## Step 3: Verify Setup

After adding variables, Railway will automatically redeploy. Check:

1. **Railway Logs** - Look for:
   - ✅ `Connected to Supabase database` (success)
   - ❌ `Supabase connection failed: Invalid API key` (check your key)
   - ❌ `SUPABASE_URL environment variable is required` (variable not set)

2. **Test API** - Call the root endpoint:
   ```bash
   curl https://your-api.up.railway.app/
   ```
   Should show: `"database": "Supabase"` (not "JSON")

## Common Issues

### Issue 1: Still showing "JSON" database
- **Cause**: Variables not set or wrong format
- **Fix**:
  - Check Railway Variables tab - make sure both are there
  - Remove quotes if you added them
  - Redeploy the service

### Issue 2: "Invalid API key" error
- **Cause**: Wrong key or URL
- **Fix**:
  - Make sure you're using the `anon` `public` key (not service_role)
  - Verify the URL is exactly: `https://xxx.supabase.co`
  - Check for typos or extra spaces

### Issue 3: Variables not showing in logs
- **Cause**: Service not redeployed
- **Fix**:
  - Go to Railway Dashboard → Deployments
  - Click "Redeploy" or wait for auto-redeploy
  - Check latest deployment logs

## Step 4: Run SQL Schema

After credentials are set, you need to create the database tables:

1. **Go to Supabase Dashboard**
   - Navigate to **SQL Editor**

2. **Run Schema**
   - Click **New Query**
   - Copy contents from `scripts/supabase_schema.sql`
   - Paste into SQL editor
   - Click **Run** (or press Cmd/Ctrl + Enter)

3. **Verify Tables Created**
   - Go to **Table Editor**
   - You should see:
     - `trades`
     - `portfolio_snapshots`
     - `positions`
     - `behavioral_metrics`
     - `bot_config`

## Quick Reference

**SUPABASE_URL Format:**
```
https://abcdefghijklmnop.supabase.co
```

**SUPABASE_KEY Format:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2RlZmdoaWprbG1ub3AiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTYxNjIzOTAyMiwiZXhwIjoxOTMxODE1MDIyfQ.abcdefghijklmnopqrstuvwxyz123456789
```

**Railway Variables:**
- Variable name: `SUPABASE_URL` (exact, case-sensitive)
- Variable name: `SUPABASE_KEY` (exact, case-sensitive)
