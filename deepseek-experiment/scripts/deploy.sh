#!/bin/bash
# Deployment script for DigitalOcean

set -e

echo "🚀 Deploying Trading Bot to DigitalOcean..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx curl

# Create app directory
sudo mkdir -p /opt/trading-bot
sudo chown $USER:$USER /opt/trading-bot
cd /opt/trading-bot

# Clone repository (or copy files)
# git clone <your-repo-url> .

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create data directories
mkdir -p data/logs

echo "✅ Setup complete!"
