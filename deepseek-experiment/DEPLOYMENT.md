# 🚀 Deployment Guide

This guide covers deploying the LLM Trading Bot in various environments with proper security, monitoring, and operational procedures.

## 📋 Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 20.04+), macOS (10.15+), or Windows 10+
- **Python**: 3.8 or higher
- **Memory**: Minimum 4GB RAM (8GB+ recommended)
- **Storage**: 10GB+ free space
- **Network**: Stable internet connection

### External Dependencies
- **Database**: PostgreSQL 12+ or SQLite (for development)
- **Redis**: Optional, for caching and session management
- **Docker**: Optional, for containerized deployment

## 🔧 Installation

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/llm-trading-bot.git
cd llm-trading-bot/deepseek-experiment
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install Additional Dependencies (Optional)
```bash
# For database support
pip install asyncpg sqlalchemy[asyncio]

# For Redis caching
pip install redis

# For monitoring
pip install psutil prometheus-client
```

## ⚙️ Configuration

### 1. Environment Variables
Create a `.env` file in the project root:

```bash
# Database Configuration
DATABASE_URL=postgresql://trading_user:secure_password@localhost:5432/trading_bot
DB_PASSWORD=secure_password

# LLM Configuration
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-your-deepseek-api-key-here
LLM_MODEL=deepseek-chat

# Exchange Configuration
EXCHANGE=bybit
EXCHANGE_API_KEY=your-exchange-api-key
EXCHANGE_API_SECRET=your-exchange-api-secret
TESTNET_API_KEY=your-testnet-api-key
TESTNET_API_SECRET=your-testnet-api-secret
USE_TESTNET=true

# Trading Configuration
TRADING_MODE=paper
INITIAL_BALANCE=10000.0
MAX_POSITION_SIZE=0.1
MAX_LEVERAGE=10.0

# Security Configuration
ENABLE_RATE_LIMITING=true
MAX_REQUESTS_PER_MINUTE=60
ENABLE_INPUT_VALIDATION=true

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=data/logs/bot.log

# Monitoring Configuration
ENABLE_METRICS=true
ENABLE_HEALTH_CHECKS=true
ENABLE_ALERTS=true
```

### 2. Configuration File
The system uses `config.yaml` for detailed configuration. Key sections:

```yaml
# Database Configuration
database:
  host: "localhost"
  port: 5432
  database: "trading_bot"
  username: "trading_user"
  password: "${DB_PASSWORD}"

# Security Configuration
security:
  enable_rate_limiting: true
  max_requests_per_minute: 60
  enable_input_validation: true
  enable_api_key_validation: true

# Trading Configuration
trading:
  mode: "paper"
  initial_balance: 10000.0
  max_position_size: 0.1
  max_leverage: 10.0
  run_interval_seconds: 150
```

## 🗄️ Database Setup

### PostgreSQL (Recommended for Production)

1. **Install PostgreSQL**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# macOS
brew install postgresql
brew services start postgresql

# Windows
# Download from https://www.postgresql.org/download/windows/
```

2. **Create Database and User**
```sql
-- Connect as postgres user
sudo -u postgres psql

-- Create database and user
CREATE DATABASE trading_bot;
CREATE USER trading_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE trading_bot TO trading_user;
\q
```

3. **Initialize Schema**
```bash
psql -h localhost -U trading_user -d trading_bot -f scripts/init_db.sql
```

### SQLite (Development)
```bash
# No setup required - database will be created automatically
python -c "from src.database_manager import DatabaseManager; import asyncio; asyncio.run(DatabaseManager('sqlite+aiosqlite:///trading_bot.db')._initialize_connection())"
```

## 🐳 Docker Deployment

### 1. Build Images
```bash
# Build all services
docker-compose build

# Build specific service
docker-compose build trading-bot
```

### 2. Start Services
```bash
# Start all services
docker-compose up -d

# Start specific services
docker-compose up -d postgres api frontend

# Start with trading bot
docker-compose --profile bot up -d
```

### 3. View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f trading-bot
```

### 4. Stop Services
```bash
docker-compose down
```

## 🚀 Production Deployment

### 1. System Preparation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3-pip python3-venv postgresql-client nginx

# Create application user
sudo useradd -m -s /bin/bash tradingbot
sudo usermod -aG sudo tradingbot
```

### 2. Application Setup
```bash
# Switch to application user
sudo su - tradingbot

# Clone and setup application
git clone https://github.com/yourusername/llm-trading-bot.git
cd llm-trading-bot/deepseek-experiment

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Systemd Service
Create `/etc/systemd/system/trading-bot.service`:

```ini
[Unit]
Description=LLM Trading Bot
After=network.target postgresql.service

[Service]
Type=simple
User=tradingbot
Group=tradingbot
WorkingDirectory=/home/tradingbot/llm-trading-bot/deepseek-experiment
Environment=PATH=/home/tradingbot/llm-trading-bot/deepseek-experiment/venv/bin
ExecStart=/home/tradingbot/llm-trading-bot/deepseek-experiment/venv/bin/python -m src.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
sudo systemctl status trading-bot
```

### 4. Nginx Configuration
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
    }

    # Web dashboard
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://localhost:8002;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/trading-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. SSL Certificate (Let's Encrypt)
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 📊 Monitoring Setup

### 1. Prometheus (Optional)
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'trading-bot'
    static_configs:
      - targets: ['localhost:8001']
    metrics_path: '/metrics'
    scrape_interval: 5s
```

### 2. Grafana Dashboard (Optional)
Import the provided Grafana dashboard configuration for trading bot metrics.

### 3. Log Management
```bash
# Install logrotate
sudo apt install logrotate

# Create logrotate config
sudo tee /etc/logrotate.d/trading-bot << EOF
/home/tradingbot/llm-trading-bot/deepseek-experiment/data/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 tradingbot tradingbot
    postrotate
        systemctl reload trading-bot
    endscript
}
EOF
```

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
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO trading_user;

-- Enable SSL
ALTER SYSTEM SET ssl = on;
SELECT pg_reload_conf();
```

### 3. Application Security
```bash
# Set proper file permissions
chmod 600 .env
chmod 600 config.yaml
chmod 755 data/
chmod 755 data/logs/

# Disable unnecessary services
sudo systemctl disable apache2
sudo systemctl stop apache2
```

## 🔄 Backup and Recovery

### 1. Database Backup
```bash
# Create backup script
cat > backup_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/tradingbot/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
pg_dump -h localhost -U trading_user trading_bot > $BACKUP_DIR/trading_bot_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/trading_bot_$DATE.sql

# Keep only last 30 days
find $BACKUP_DIR -name "trading_bot_*.sql.gz" -mtime +30 -delete
EOF

chmod +x backup_db.sh

# Schedule backup
crontab -e
# Add: 0 2 * * * /home/tradingbot/backup_db.sh
```

### 2. Application Data Backup
```bash
# Backup application data
tar -czf trading_bot_data_$(date +%Y%m%d).tar.gz data/
```

### 3. Recovery Procedure
```bash
# Restore database
gunzip -c trading_bot_20240101_020000.sql.gz | psql -h localhost -U trading_user trading_bot

# Restore application data
tar -xzf trading_bot_data_20240101.tar.gz
```

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check PostgreSQL status
   sudo systemctl status postgresql
   
   # Check connection
   psql -h localhost -U trading_user -d trading_bot -c "SELECT 1;"
   ```

2. **API Key Validation Failed**
   ```bash
   # Check API key format
   python -c "from src.security import SecurityManager; sm = SecurityManager(); print(sm.validate_api_key('your-key', 'deepseek'))"
   ```

3. **Port Already in Use**
   ```bash
   # Find process using port
   sudo netstat -tulpn | grep :8001
   
   # Kill process
   sudo kill -9 <PID>
   ```

4. **Permission Denied**
   ```bash
   # Fix ownership
   sudo chown -R tradingbot:tradingbot /home/tradingbot/llm-trading-bot/
   
   # Fix permissions
   chmod -R 755 /home/tradingbot/llm-trading-bot/
   ```

### Log Analysis
```bash
# View recent logs
tail -f data/logs/bot.log

# Search for errors
grep -i error data/logs/bot.log

# Monitor system resources
htop
iostat -x 1
```

## 📈 Performance Optimization

### 1. Database Optimization
```sql
-- Create indexes for better performance
CREATE INDEX CONCURRENTLY idx_trades_timestamp ON trades(timestamp);
CREATE INDEX CONCURRENTLY idx_trades_symbol ON trades(symbol);
CREATE INDEX CONCURRENTLY idx_positions_active ON positions(is_active);

-- Analyze tables
ANALYZE trades;
ANALYZE positions;
ANALYZE portfolio_snapshots;
```

### 2. Application Optimization
```yaml
# config.yaml
performance:
  enable_caching: true
  cache_ttl: 300
  enable_async_operations: true
  max_concurrent_requests: 10
  connection_pool_size: 20
```

### 3. System Optimization
```bash
# Increase file limits
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# Optimize PostgreSQL
# Edit /etc/postgresql/*/main/postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

## 🔄 Updates and Maintenance

### 1. Application Updates
```bash
# Stop service
sudo systemctl stop trading-bot

# Backup current version
cp -r /home/tradingbot/llm-trading-bot /home/tradingbot/llm-trading-bot.backup

# Update code
cd /home/tradingbot/llm-trading-bot
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run database migrations (if any)
python scripts/migrate.py

# Start service
sudo systemctl start trading-bot
```

### 2. Database Maintenance
```sql
-- Vacuum database
VACUUM ANALYZE;

-- Reindex if needed
REINDEX DATABASE trading_bot;
```

### 3. Log Rotation
```bash
# Manual log rotation
sudo logrotate -f /etc/logrotate.d/trading-bot
```

## 📞 Support

For deployment issues:
1. Check logs: `tail -f data/logs/bot.log`
2. Check system status: `sudo systemctl status trading-bot`
3. Review configuration: `cat config.yaml`
4. Check database connectivity: `psql -h localhost -U trading_user -d trading_bot`

For additional support, create an issue on GitHub with:
- System information
- Error logs
- Configuration details
- Steps to reproduce
