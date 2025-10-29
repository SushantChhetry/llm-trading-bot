#!/bin/bash

# Trading Bot Docker Startup Script

set -e

echo "🚀 Starting Trading Bot Dashboard with Docker..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp docker.env.example .env
    echo "✅ Created .env file. Please edit it with your configuration."
fi

# Parse command line arguments
MODE="dashboard"
PROFILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --bot)
            MODE="full"
            PROFILE="--profile bot"
            shift
            ;;
        --dev)
            MODE="dev"
            shift
            ;;
        --help)
            echo "Usage: $0 [--bot] [--dev] [--help]"
            echo "  --bot    Start with trading bot"
            echo "  --dev    Start in development mode"
            echo "  --help   Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Start services based on mode
case $MODE in
    "dashboard")
        echo "📊 Starting dashboard only (API + Frontend)..."
        docker-compose up -d api frontend
        ;;
    "full")
        echo "🤖 Starting full system (API + Frontend + Trading Bot)..."
        docker-compose $PROFILE up -d
        ;;
    "dev")
        echo "🔧 Starting in development mode..."
        docker-compose -f docker-compose.dev.yml up -d
        ;;
esac

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Check API
if curl -s http://localhost:8001/api/status > /dev/null; then
    echo "✅ API server is running on http://localhost:8001"
else
    echo "❌ API server is not responding"
fi

# Check Frontend
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Frontend is running on http://localhost:3000"
else
    echo "❌ Frontend is not responding"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📊 Dashboard: http://localhost:3000"
echo "🔌 API: http://localhost:8001"
echo ""
echo "📋 Useful commands:"
echo "  View logs: docker-compose logs -f"
echo "  Stop: docker-compose down"
echo "  Status: docker-compose ps"
echo ""
