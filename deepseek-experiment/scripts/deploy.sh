#!/bin/bash
# Deployment script for Railway
# Note: Railway uses automatic deployments via GitHub
# This script is for local setup/testing

set -e

echo "🚀 Setting up Trading Bot for Railway deployment..."

# Railway automatically handles:
# - Python environment setup
# - Dependency installation via requirements.txt
# - Service orchestration
# - Environment variable management
# - Health checks and monitoring

# For Railway deployment:
# 1. Connect your GitHub repo to Railway
# 2. Railway will auto-detect Python project
# 3. Set environment variables in Railway dashboard
# 4. Railway will build and deploy automatically

# For local development/testing:
echo "📦 Setting up local development environment..."

# Check Python version
python3 --version

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create data directories
mkdir -p data/logs
mkdir -p data/experiments/results

echo "✅ Local setup complete!"
echo "💡 For Railway deployment, use the Railway dashboard or CLI"
echo "💡 Run: railway login && railway up"
