# Docker Deployment Guide

Deploy the Alpha Arena Trading Bot using Docker and Docker Compose.

## 🐳 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Git repository cloned

### 1. Environment Setup

```bash
# Copy the environment template
cp docker.env.example .env

# Edit the environment variables
nano .env  # or use any text editor
```

### 2. Run the Dashboard Only

```bash
# Start just the API and frontend
docker-compose up -d api frontend

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 3. Run Everything (Including Trading Bot)

```bash
# Start all services including the trading bot
docker-compose --profile bot up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

---

## 🚀 Available Services

### API Server (Backend)
- **Port**: 8001
- **Health Check**: http://localhost:8001/api/status
- **Purpose**: Serves trading data and bot status

### Frontend (React Dashboard)
- **Port**: 3000
- **URL**: http://localhost:3000
- **Purpose**: Web dashboard for monitoring

### Trading Bot (Optional)
- **Profile**: `bot` (only starts with `--profile bot`)
- **Purpose**: Runs the actual trading bot
- **Data**: Writes to shared volume

---

## 🔧 Development Mode

For development with hot reload:

```bash
# Use development compose file
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f
```

---

## 📁 Volume Mounts

- `./data` → `/app/data` (trading data)
- `./logs` → `/app/logs` (log files)

---

## 🌐 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TRADING_MODE` | `paper` | Trading mode (paper/live) |
| `USE_TESTNET` | `true` | Use testnet data |
| `LLM_PROVIDER` | `mock` | LLM provider (mock/deepseek/openai) |
| `LLM_API_KEY` | - | API key for LLM provider |
| `EXCHANGE` | `bybit` | Exchange to use |
| `SYMBOL` | `BTC/USDT` | Trading pair |
| `INITIAL_BALANCE` | `10000.0` | Starting balance |
| `RUN_INTERVAL_SECONDS` | `300` | Bot run interval |

---

## 🛠️ Docker Commands

### Build Images

```bash
# Build all images
docker-compose build

# Build specific service
docker-compose build api
docker-compose build frontend
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f frontend
```

### Execute Commands

```bash
# Access API container
docker-compose exec api bash

# Access frontend container
docker-compose exec frontend sh

# Run trading bot manually
docker-compose run --rm trading-bot python -m src.main
```

### Clean Up

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

---

## 🔍 Troubleshooting

### Port Conflicts

If ports 3000 or 8001 are already in use:

```bash
# Check what's using the ports
lsof -i :3000
lsof -i :8001

# Kill processes or change ports in docker-compose.yml
```

### Permission Issues

```bash
# Fix volume permissions
sudo chown -R $USER:$USER ./data ./logs
```

### Container Won't Start

```bash
# Check logs
docker-compose logs api
docker-compose logs frontend

# Rebuild images
docker-compose build --no-cache
```

### Data Not Persisting

```bash
# Check volume mounts
docker-compose exec api ls -la /app/data
docker-compose exec frontend ls -la /usr/share/nginx/html
```

---

## 📊 Monitoring

### Health Checks
- **API**: http://localhost:8001/api/status
- **Frontend**: http://localhost:3000
- **Docker**: `docker-compose ps`

### Resource Usage

```bash
# View resource usage
docker stats

# View container details
docker-compose ps
```

---

## 🔒 Security Notes

1. **Never commit `.env` files** with real API keys
2. **Use testnet** for development
3. **Set strong passwords** for production
4. **Limit network access** in production

---

## 🚀 Production Deployment

### 1. Environment Setup

```bash
# Create production environment
cp docker.env.example .env.production

# Set production values
nano .env.production
```

### 2. Run Production

```bash
# Use production environment
docker-compose --env-file .env.production up -d

# Or set environment variables
export TRADING_MODE=live
export LLM_PROVIDER=deepseek
export LLM_API_KEY=your_key
docker-compose up -d
```

### 3. Reverse Proxy (Optional)

For production, consider using a reverse proxy like Traefik or Nginx.

---

## 📝 Examples

### Run with DeepSeek API

```bash
export LLM_PROVIDER=deepseek
export LLM_API_KEY=sk-your-deepseek-key
docker-compose up -d
```

### Run with Live Trading

```bash
export TRADING_MODE=live
export USE_TESTNET=false
export EXCHANGE_API_KEY=your_key
export EXCHANGE_API_SECRET=your_secret
docker-compose up -d
```

### Run Only Dashboard (No Bot)

```bash
docker-compose up -d api frontend
```

---

## Related Documentation

- **[Deployment Overview](overview.md)** - Choose deployment method
- **[Configuration Reference](../../reference/configuration.md)** - All settings
- **[Troubleshooting Guide](../../troubleshooting/common-issues.md)** - Common issues

---

**Last Updated**: See git history for updates.
