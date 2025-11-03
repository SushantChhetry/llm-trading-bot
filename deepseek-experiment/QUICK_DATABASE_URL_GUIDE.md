# Quick Guide: Finding DATABASE_URL from Supabase

## 🎯 Step-by-Step Visual Guide

### Step 1: Open Supabase Dashboard
1. Go to: https://supabase.com/dashboard
2. Select your project

### Step 2: Navigate to Database Settings
```
Left Sidebar → ⚙️ Project Settings → Database (left menu)
```

### Step 3: Get Connection String
1. Scroll down to **"Connection string"** section
2. **IMPORTANT**: Select **"Direct connection"** (NOT "Connection pooling")
3. You should see port **5432** (NOT 6543)
4. Click the **copy icon** next to the URI

### Step 4: The Connection String Looks Like This:
```
postgresql://postgres.abcdefghijklmnop:[YOUR-PASSWORD]@db.abcdefghijklmnop.supabase.co:5432/postgres
```

### Step 5: Replace `[YOUR-PASSWORD]`
Replace `[YOUR-PASSWORD]` with your actual database password.

**Don't know your password?**
- Go to: **Project Settings → Database → Database Settings**
- Reset your database password if needed

### Step 6: Set It Up

**For Local Development (.env file):**
```bash
cd deepseek-experiment
echo 'DATABASE_URL=postgresql://postgres.xxx:your_actual_password@db.xxx.supabase.co:5432/postgres' >> .env
```

**Or edit `.env` manually:**
```bash
nano .env  # or use any editor
# Add: DATABASE_URL=postgresql://...
```

**For Railway (Production):**
1. Go to Railway dashboard
2. Select your service
3. **Variables** tab → **+ New Variable**
4. Key: `DATABASE_URL`
5. Value: Your full connection string (with password replaced)

## ✅ Verify It Works

```bash
cd deepseek-experiment
python scripts/test_alembic_connection.py
```

## 📍 Exact Location in Supabase UI

```
Dashboard
  └── Your Project
      └── Settings (⚙️ icon in sidebar)
          └── Database
              └── Connection string section
                  └── [Direct connection tab] ← SELECT THIS
                      └── URI: postgresql://... ← COPY THIS
```

## ⚠️ Important Notes

- ✅ Use **"Direct connection"** (port 5432) for Alembic
- ❌ Don't use **"Connection pooling"** (port 6543)
- ✅ Replace `[YOUR-PASSWORD]` with your actual password
- ✅ Never commit `.env` files to git (already in `.gitignore`)

## 🔍 Visual Reference

The connection string format:
```
postgresql://[USER].[PROJECT_REF]:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
```

Example:
```
postgresql://postgres.abcdefghijklmnop:MyPassword123@db.abcdefghijklmnop.supabase.co:5432/postgres
```
