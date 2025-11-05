#!/bin/bash
# Start both risk service and trading bot in the same container
# This allows deploying both as a single Railway service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Risk Service and Trading Bot...${NC}"

# Function to handle shutdown
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $RISK_PID $BOT_PID 2>/dev/null || true
    wait $RISK_PID $BOT_PID 2>/dev/null || true
    echo -e "${GREEN}Services stopped.${NC}"
    exit 0
}

# Trap SIGTERM and SIGINT
trap cleanup SIGTERM SIGINT

# Ensure risk service uses port 8003 (internal, not Railway's PORT)
# Railway automatically sets PORT env var, but we need risk service on fixed port 8003
# RISK_SERVICE_PORT takes precedence over PORT in risk_service.py
export RISK_SERVICE_PORT=8003
# Store Railway's PORT for reference (trading bot doesn't use it, but keep it available)
RAILWAY_PORT=${PORT:-}
# Note: PORT is still available in env, but risk_service.py will use RISK_SERVICE_PORT first

echo -e "${YELLOW}Port Configuration:${NC}"
echo -e "  Railway PORT (auto-set): ${RAILWAY_PORT:-not set}"
echo -e "  RISK_SERVICE_PORT (explicit): ${RISK_SERVICE_PORT}"
echo -e "  Risk service will use: ${RISK_SERVICE_PORT} (RISK_SERVICE_PORT takes precedence)"

# Start risk service in background
echo -e "${GREEN}Starting Risk Service on port ${RISK_SERVICE_PORT}...${NC}"
python services/risk_service.py &
RISK_PID=$!

# Wait for risk service to be ready
echo -e "${YELLOW}Waiting for Risk Service to be ready...${NC}"
set +e  # Allow health check failures during startup
for i in {1..30}; do
    # Use Python to check health (more reliable than curl)
    if python -c "import requests; requests.get('http://localhost:${RISK_SERVICE_PORT}/health', timeout=1)" 2>/dev/null; then
        echo -e "${GREEN}Risk Service is ready!${NC}"
        set -e  # Re-enable strict error handling
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}Risk Service failed to start after 30 seconds${NC}"
        kill $RISK_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done
set -e  # Re-enable strict error handling (in case loop didn't break)

# Start trading bot in background
echo -e "${GREEN}Starting Trading Bot...${NC}"
python -m src.main &
BOT_PID=$!

# Wait for both processes
echo -e "${GREEN}Both services started. Monitoring...${NC}"
echo -e "Risk Service PID: $RISK_PID"
echo -e "Trading Bot PID: $BOT_PID"

# Monitor processes and restart if they die
while true; do
    if ! kill -0 $RISK_PID 2>/dev/null; then
        echo -e "${RED}Risk Service died! Restarting...${NC}"
        python services/risk_service.py &
        RISK_PID=$!
        sleep 2
    fi
    
    if ! kill -0 $BOT_PID 2>/dev/null; then
        echo -e "${RED}Trading Bot died! Exiting...${NC}"
        kill $RISK_PID 2>/dev/null || true
        exit 1
    fi
    
    sleep 5
done

