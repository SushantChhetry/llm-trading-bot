#!/bin/bash
# Quick status check

echo "=== Trading Bot Status ==="
sudo systemctl status trading-bot --no-pager

echo -e "\n=== API Server Status ==="
sudo systemctl status trading-api --no-pager

echo -e "\n=== Recent Bot Logs ==="
sudo journalctl -u trading-bot -n 20 --no-pager

echo -e "\n=== Disk Usage ==="
df -h /opt/trading-bot

echo -e "\n=== Portfolio Summary ==="
curl -s http://localhost:8001/api/portfolio | python3 -m json.tool
