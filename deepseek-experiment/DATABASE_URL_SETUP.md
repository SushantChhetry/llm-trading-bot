# How to Set DATABASE_URL

## Option 1: Local Development (.env file) - Recommended

Create or edit `.env` file in the `deepseek-experiment/` directory:

```bash
cd deepseek-experiment
nano .env  # or use any text editor
```

Add this line:
```bash
DATABASE_URL=postgresql://postgres.xxx:your_password@db.xxx.supabase.co:5432/postgres
```

**Important**: Replace:
- `xxx` with your Supabase project reference
- `your_password` with your actual database password

## Option 2: Export in Terminal (Temporary)

For testing right now:
```bash
export DATABASE_URL="postgresql://postgres.xxx:your_password@db.xxx.supabase.co:5432/postgres"
```

⚠️ This only works for your current terminal session.

## Option 3: Railway (Production)

1. Go to Railway dashboard
2. Select your service (Trading Bot or API Server)
3. Go to **Variables** tab
4. Click **+ New Variable**
5. Add:
   - **Key**: `DATABASE_URL`
   - **Value**: `postgresql://postgres.xxx:password@db.xxx.supabase.co:5432/postgres`

## How to Get the Connection String from Supabase

### Step-by-Step:

1. **Go to Supabase Dashboard**
   - Visit: https://supabase.com/dashboard
   - Select your project

2. **Navigate to Database Settings**
   - Click **Project Settings** (gear icon in sidebar)
   - Click **Database** in left menu

3. **Get Connection String**
   - Scroll to **Connection string** section
   - Select **"Direct connection"** (NOT Connection pooling)
   - The URI should show port **5432**
   - Copy the full URI

4. **Replace `[YOUR-PASSWORD]`**
   - In the copied URI, replace `[YOUR-PASSWORD]` with your actual database password
   - If you don't know the password:
     - Go to **Database** → **Connection string**
     - Or reset it in **Database** → **Database Settings**

### Example Connection String Format:

```
postgresql://postgres.abcdefghijklmnop:[YOUR-PASSWORD]@db.abcdefghijklmnop.supabase.co:5432/postgres
```

After replacing `[YOUR-PASSWORD]`:
```
postgresql://postgres.abcdefghijklmnop:MySecurePassword123@db.abcdefghijklmnop.supabase.co:5432/postgres
```

## Quick Setup Command

Once you have the connection string, add it to `.env`:

```bash
cd deepseek-experiment
echo 'DATABASE_URL=postgresql://postgres.xxx:password@db.xxx.supabase.co:5432/postgres' >> .env
```

(Replace with your actual connection string)

## Verify It's Set

```bash
# Check if .env is loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('DATABASE_URL:', os.getenv('DATABASE_URL', 'NOT SET')[:50] + '...' if os.getenv('DATABASE_URL') else 'NOT SET')"

# Or test Alembic connection
python scripts/test_alembic_connection.py
```

## Security Notes

- ✅ `.env` files are typically git-ignored (check `.gitignore`)
- ✅ Never commit `DATABASE_URL` to version control
- ✅ Use different passwords for development/production
- ✅ Railway automatically encrypts environment variables

## Troubleshooting

**"DATABASE_URL not found"**
- Check `.env` file exists in `deepseek-experiment/` directory
- Verify the variable name is exactly `DATABASE_URL` (case-sensitive)
- Make sure you're running from the correct directory

**"Connection refused"**
- Verify you're using "Direct connection" (port 5432)
- Check your IP isn't blocked in Supabase Network Restrictions
- Verify password is correct

**"Module 'dotenv' not found"**
- Install: `pip install python-dotenv`
