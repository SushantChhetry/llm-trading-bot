# Manual Deployment Guide

Deploy the Alpha Arena Trading Bot to your own VPS or server with full control.

## 📋 Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 20.04+ recommended), macOS (10.15+), or Windows 10+
- **Python**: 3.8 or higher
- **Memory**: Minimum 4GB RAM (8GB+ recommended)
- **Storage**: 10GB+ free space
- **Network**: Stable internet connection

### External Dependencies
- **Database**: PostgreSQL 12+ (or use Supabase)
- **Domain name** (optional, for production with SSL)
- **Server/VPS** with root/sudo access

---

## 🔧 Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/llm-trading-bot.git
cd llm-trading-bot/deepseek-experiment
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt

# Optional: For additional features
pip install asyncpg sqlalchemy[asyncio]  # Database support
pip install redis  # Redis caching
pip install psutil prometheus-client  # Monitoring
```

---

## ⚙️ Configuration

### 1. Environment Variables

Create `.env` file in project root:

```bash
# Environment
ENVIRONMENT=production

# LLM Configuration
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-your-deepseek-api-key-here
LLM_MODEL=deepseek-chat

# Trading Configuration
TRADING_MODE=paper
USE_TESTNET=true
EXCHANGE=bybit
SYMBOL=BTC/USDT
INITIAL_BALANCE=10000.0
RUN_INTERVAL_SECONDS=150

# Risk Management
MAX_POSITION_SIZE=0.1
MAX_LEVERAGE=10.0
STOP_LOSS_PERCENT=2.0
TAKE_PROFIT_PERCENT=3.0

# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
DATABASE_URL=postgresql://postgres.xxx:password@db.xxx.supabase.co:5432/postgres

# Logging
LOG_LEVEL=INFO
LOG_FILE=data/logs/bot.log

# Security
ENABLE_RATE_LIMITING=true
MAX_REQUESTS_PER_MINUTE=60
ENABLE_INPUT_VALIDATION=true
LOG_SENSITIVE_DATA=false
```

### 2. Set Proper Permissions

```bash
# Protect sensitive files
chmod 600 .env
chmod 600 config.yaml

# Ensure data directory is writable
chmod 755 data/
chmod 755 data/logs/
```

---

## 🗄️ Database Setup

### Option 1: Use Supabase (Recommended)

Follow [Database Setup Guide](../database/setup.md) to configure Supabase.

### Option 2: Local PostgreSQL

1. **Install PostgreSQL:**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install postgresql postgresql-contrib

   # macOS
   brew install postgresql
   brew services start postgresql
   ```

2. **Create Database and User:**
   ```sql
   sudo -u postgres psql

   CREATE DATABASE trading_bot;
   CREATE USER trading_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE trading_bot TO trading_user;
   \q
   ```

3. **Initialize Schema:**
   ```bash
   psql -h localhost -U trading_user -d trading_bot -f scripts/init_db.sql
   ```

4. **Update DATABASE_URL:**
   ```bash
   DATABASE_URL=postgresql://trading_user:secure_password@localhost:5432/trading_bot
   ```

---

## 🚀 Systemd Service Setup

### 1. Create Service File

Create `/etc/systemd/system/trading-bot.service`:

```ini
[Unit]
Description=Alpha Arena Trading Bot
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=your_username
Group=your_username
WorkingDirectory=/path/to/llm-trading-bot/deepseek-experiment
Environment="PATH=/path/to/llm-trading-bot/deepseek-experiment/venv/bin"
ExecStart=/path/to/llm-trading-bot/deepseek-experiment/venv/bin/python -m src.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

**Important**: Replace:
- `your_username` with your actual username
- `/path/to/llm-trading-bot/deepseek-experiment` with actual path

### 2. Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable trading-bot

# Start service
sudo systemctl start trading-bot

# Check status
sudo systemctl status trading-bot

# View logs
sudo journalctl -u trading-bot -f
```

### 3. Service Management

```bash
# Stop service
sudo systemctl stop trading-bot

# Restart service
sudo systemctl restart trading-bot

# View logs
sudo journalctl -u trading-bot --tail 100

# View logs in real-time
sudo journalctl -u trading-bot -f
```

---

## 🌐 Nginx Configuration (Optional)

If you want to serve the API server with Nginx:

### 1. Install Nginx

```bash
sudo apt install nginx
```

### 2. Create Configuration

Create `/etc/nginx/sites-available/trading-bot`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # API server
    location /api/ {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Health check
    location /health {
        proxy_pass http://localhost:8001/health;
    }
}
```

### 3. Enable Site

```bash
sudo ln -s /etc/nginx/sites-available/trading-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🔒 SSL Certificate (Let's Encrypt)

### 1. Install Certbot

```bash
sudo apt install certbot python3-certbot-nginx
```

### 2. Obtain Certificate

```bash
sudo certbot --nginx -d your-domain.com
```

### 3. Auto-Renewal

Certbot automatically sets up renewal. Verify:

```bash
sudo certbot renew --dry-run
```

---

## 📊 Monitoring Setup

### 1. Log Rotation

Create `/etc/logrotate.d/trading-bot`:

```
/path/to/llm-trading-bot/deepseek-experiment/data/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 your_username your_username
    postrotate
        systemctl reload trading-bot
    endscript
}
```

### 2. Health Checks

Set up monitoring to check:
- Service status: `systemctl is-active trading-bot`
- API health: `curl http://localhost:8001/health`
- Disk space: `df -h`
- Memory usage: `free -h`

### 3. Prometheus (Optional)

If using Prometheus, configure scraping endpoint:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'trading-bot'
    static_configs:
      - targets: ['localhost:8001']
    metrics_path: '/metrics'
```

---

## 🔄 Backup and Recovery

### 1. Database Backup

Create backup script `/usr/local/bin/backup-trading-bot.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups/trading-bot"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
pg_dump -h localhost -U trading_user trading_bot > $BACKUP_DIR/trading_bot_$DATE.sql
gzip $BACKUP_DIR/trading_bot_$DATE.sql

# Backup application data
tar -czf $BACKUP_DIR/trading_bot_data_$DATE.tar.gz /path/to/llm-trading-bot/deepseek-experiment/data/

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

Make executable:
```bash
sudo chmod +x /usr/local/bin/backup-trading-bot.sh
```

### 2. Schedule Backups

Add to crontab:
```bash
crontab -e

# Daily backup at 2 AM
0 2 * * * /usr/local/bin/backup-trading-bot.sh
```

### 3. Recovery

```bash
# Restore database
gunzip -c trading_bot_20240101_020000.sql.gz | psql -h localhost -U trading_user trading_bot

# Restore application data
tar -xzf trading_bot_data_20240101.tar.gz -C /
```

---

## 🔒 Security Hardening

### 1. Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 5432/tcp  # Block direct database access
```

### 2. Database Security

```sql
-- Restrict database access
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO trading_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO trading_user;

-- Enable SSL
ALTER SYSTEM SET ssl = on;
SELECT pg_reload_conf();
```

### 3. Application Security

- Set proper file permissions
- Use strong passwords
- Disable unnecessary services
- Keep system updated
- Review logs regularly

---

## 🔄 Updates and Maintenance

### 1. Update Application

```bash
# Stop service
sudo systemctl stop trading-bot

# Backup current version
cp -r /path/to/llm-trading-bot /path/to/llm-trading-bot.backup

# Update code
cd /path/to/llm-trading-bot
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run database migrations (if any)
alembic upgrade head

# Start service
sudo systemctl start trading-bot

# Verify
sudo systemctl status trading-bot
```

### 2. Database Maintenance

```sql
-- Vacuum database
VACUUM ANALYZE;

-- Reindex if needed
REINDEX DATABASE trading_bot;
```

---

## 🚨 Troubleshooting

### Service Won't Start

```bash
# Check status
sudo systemctl status trading-bot

# View logs
sudo journalctl -u trading-bot --tail 100

# Check configuration
python -m src.startup_validator
```

### Database Connection Failed

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U trading_user -d trading_bot -c "SELECT 1;"
```

### Port Already in Use

```bash
# Find process using port
sudo netstat -tulpn | grep :8001

# Kill process
sudo kill -9 <PID>
```

---

## 📋 Quick Reference

| Task | Command |
|------|---------|
| Start service | `sudo systemctl start trading-bot` |
| Stop service | `sudo systemctl stop trading-bot` |
| Restart service | `sudo systemctl restart trading-bot` |
| View logs | `sudo journalctl -u trading-bot -f` |
| Check status | `sudo systemctl status trading-bot` |
| Enable on boot | `sudo systemctl enable trading-bot` |

---

## Related Documentation

- **[Deployment Overview](overview.md)** - Choose deployment method
- **[Railway Deployment](railway.md)** - Easier cloud option
- **[Docker Deployment](docker.md)** - Containerized deployment
- **[Database Setup](../database/setup.md)** - Database configuration
- **[Configuration Reference](../../reference/configuration.md)** - All settings

---

**Last Updated**: See git history for updates.
