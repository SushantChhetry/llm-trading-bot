# How to Get Your Railway URL

## Step-by-Step Instructions

### Option 1: From Railway Dashboard (Recommended)

1. **Log in to Railway:**
   - Go to https://railway.app
   - Sign in with your GitHub account

2. **Open Your Project:**
   - Click on your project from the dashboard
   - If you haven't created one yet, click "New Project" → "Deploy from GitHub repo"

3. **Select Your Service:**
   - Click on the service you want (e.g., your API server service)
   - This should be the service running `api_server_supabase.py`

4. **Get the Public Domain:**
   - Click on the **"Settings"** tab (gear icon or Settings button)
   - Scroll down to the **"Networking"** section
   - Look for **"Public Domain"**
   - Click **"Generate Domain"** if you don't have one yet
   - Your URL will look like: `your-service-name.up.railway.app`
   - **Copy this URL** - this is your Railway URL!

### Option 2: From Service Overview

1. **In Your Service:**
   - Click on your service in Railway dashboard
   - Look at the top of the service page
   - You should see a section showing the service URL
   - It might show as "Public Domain" or "Custom Domain"

### Option 3: From Deployment Logs

1. **Check Recent Deployments:**
   - Go to your service
   - Click on the **"Deployments"** tab
   - Look at the latest deployment
   - The URL is sometimes shown in the deployment logs

---

## What Your Railway URL Looks Like

Railway URLs typically follow this format:
```
https://your-service-name.up.railway.app
```

Examples:
- `https://api-trading-bot.up.railway.app`
- `https://trading-api-production.up.railway.app`
- `https://my-trading-bot-api.up.railway.app`

---

## Important Notes

### If You Don't See a Public Domain:

1. **Generate One:**
   - Go to Settings → Networking
   - Click "Generate Domain"
   - Railway will create a random domain name
   - You can change it later if needed

2. **Make Sure Service is Running:**
   - Railway only shows domains for active services
   - Check that your service status is "Active" or "Running"

### Custom Domains (Optional):

- Railway also supports custom domains
- Go to Settings → Networking → Custom Domain
- Add your own domain (e.g., `api.yourdomain.com`)
- Requires DNS configuration

---

## Quick Checklist

- [ ] Logged into Railway dashboard
- [ ] Opened your project
- [ ] Selected your API service
- [ ] Went to Settings → Networking
- [ ] Found or generated Public Domain
- [ ] Copied the URL (format: `https://something.up.railway.app`)

---

## Use Your Railway URL

Once you have your Railway URL, use it in:

1. **`vercel.json`** - Update the rewrites destination
2. **Railway Environment Variables** - Set `CORS_ORIGINS` with your Vercel URL
3. **Testing** - Use `curl` or browser to test your API endpoints

Example usage in `vercel.json`:
```json
{
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "https://your-copied-railway-url.up.railway.app/api/$1"
    }
  ]
}
```

---

## Troubleshooting

### "I don't see a Public Domain option"
- Make sure you're in the correct service (API server, not trading bot)
- Check that the service has been deployed at least once
- Try refreshing the page

### "The URL doesn't work"
- Make sure your service is running (status should be "Active")
- Check Railway logs for any errors
- Verify the service is listening on the correct port (8001 for API server)

### "How do I change the domain name?"
- Go to Settings → Networking → Public Domain
- Click "Change Domain" or "Generate New Domain"
- Note: Changing domain will break existing integrations until you update them

---

## Example Screenshot Locations

In Railway Dashboard:
```
Project Dashboard
  └── Your Service
      ├── Overview Tab (shows URL at top)
      ├── Settings Tab
      │   └── Networking Section
      │       └── Public Domain ← YOUR URL IS HERE
      └── Deployments Tab (URL in logs)
```

