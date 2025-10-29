#!/bin/bash

echo "🚀 Setting up Trading Bot Web Dashboard..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first:"
    echo "   https://nodejs.org/"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 first:"
    echo "   https://python.org/"
    exit 1
fi

echo "✅ Node.js and Python 3 are installed"

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Node.js dependencies"
    exit 1
fi

echo "✅ Node.js dependencies installed"

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Python dependencies"
    exit 1
fi

echo "✅ Python dependencies installed"

echo ""
echo "🎉 Setup complete! To start the dashboard:"
echo ""
echo "1. Start the API server (Terminal 1):"
echo "   python api_server.py"
echo ""
echo "2. Start the React app (Terminal 2):"
echo "   npm run dev"
echo ""
echo "3. Open your browser to: http://localhost:3000"
echo ""
echo "📊 Your trading bot dashboard will be ready!"
