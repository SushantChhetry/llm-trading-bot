# DigitalOcean + Supabase Deployment Guide

## Quick Start

### Prerequisites
1. **Supabase Setup**: Your project is at https://uedfxgpduaramoagiatz.supabase.co
2. **DigitalOcean Account**: Create account and add SSH key
3. **API Keys**: Get DeepSeek API key and Supabase anon key

### Step 1: Supabase Database Setup
1. Go to your Supabase project dashboard
2. Navigate to SQL Editor
3. Copy and paste contents of `scripts/supabase_schema.sql`
4. Run the SQL to create tables
5. Get your anon key from Settings > API

### Step 2: DigitalOcean Droplet Setup
1. Create a new droplet:
   - OS: Ubuntu 22.04 LTS
   - Size: Basic ($6/month - 1GB RAM, 25GB SSD, 1 vCPU)
   - Region: Choose closest to you
   - Authentication: SSH key
   - Hostname: trading-bot

### Step 3: Deploy to DigitalOcean
```bash
# SSH into your droplet
ssh root@YOUR_DROPLET_IP

# Clone repository
git clone YOUR_REPO_URL /opt/trading-bot
cd /opt/trading-bot

# Copy and edit environment file
cp env.production.template .env
nano .env  # Update with your actual API keys

# Run deployment
bash scripts/deploy.sh
bash scripts/setup_systemd.sh
bash scripts/setup_nginx.sh
bash scripts/configure_logrotate.sh

# Start services
sudo systemctl start trading-bot
sudo systemctl start trading-api
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
# Check bot status
sudo systemctl status trading-bot

# Check API status
sudo systemctl status trading-api

# View logs
sudo journalctl -u trading-bot -f
```

### Test API Endpoints
```bash
# Test API
curl http://YOUR_DROPLET_IP/api/status

# Check portfolio
curl http://YOUR_DROPLET_IP/api/portfolio

# View trades
curl http://YOUR_DROPLET_IP/api/trades
```

### Access Web Dashboard
- Vercel URL: `https://your-app.vercel.app`
- Direct API: `http://YOUR_DROPLET_IP/api/`

## Monitoring

### Quick Status Check
```bash
bash scripts/monitor.sh
```

### Log Files
- Application logs: `/opt/trading-bot/data/logs/trading-bot.log`
- Error logs: `/opt/trading-bot/data/logs/trading-bot.error.log`
- JSON logs: `/opt/trading-bot/data/logs/trading-bot.json.log`

### System Logs
```bash
# Bot logs
sudo journalctl -u trading-bot -f

# API logs
sudo journalctl -u trading-api -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## Maintenance

### Update Application
```bash
cd /opt/trading-bot
git pull origin main
sudo systemctl restart trading-bot
sudo systemctl restart trading-api
```

### Backup Data
```bash
# Daily backup (already configured in crontab)
cd /opt/trading-bot
tar -czf /opt/backups/trading-bot-$(date +%Y%m%d).tar.gz data/
```

### Restart Services
```bash
sudo systemctl restart trading-bot
sudo systemctl restart trading-api
sudo systemctl restart nginx
```

## Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   sudo journalctl -u trading-bot -n 50
   ```

2. **API not responding**
   ```bash
   curl -v http://localhost:8001/api/status
   sudo systemctl status trading-api
   ```

3. **Database connection issues**
   ```bash
   # Check Supabase connection
   python -c "from web_dashboard.supabase_client import get_supabase_service; print(get_supabase_service())"
   ```

4. **Permission issues**
   ```bash
   sudo chown -R $USER:$USER /opt/trading-bot
   chmod -R 755 /opt/trading-bot
   ```

## Cost Breakdown
- DigitalOcean Basic Droplet: $6/month
- Supabase Free Tier: $0 (500MB database, 2GB bandwidth)
- Vercel Free Tier: $0 (unlimited static sites)
- **Total: $6/month**

## Security Notes
- API keys are stored in environment variables
- Database access is restricted to application
- Logs are rotated daily to prevent disk space issues
- Services restart automatically on failure
