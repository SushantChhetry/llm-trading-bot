# Trading Bot Web Dashboard

A modern, real-time web dashboard for monitoring your LLM trading bot performance. Built with React, Vite, Radix UI, and Recharts.

## Features

- 📊 **Real-time P&L Chart** - Live portfolio value tracking with time series visualization
- 💰 **Portfolio Overview** - Current balance, returns, positions, and trade statistics
- 📈 **Recent Trades** - Latest trading activity with LLM reasoning and confidence scores
- 🤖 **Bot Status** - Live configuration and status monitoring
- ⚡ **Real-time Updates** - Data refreshes every 5 seconds automatically
- 🎨 **Modern UI** - Clean, professional interface with dark/light mode support

## Quick Start

### 1. Install Dependencies

```bash
# Install Node.js dependencies
npm install

# Install Python API server dependencies
pip install -r requirements.txt
```

### 2. Start the Services

```bash
# Terminal 1: Start the API server
python api_server.py

# Terminal 2: Start the React development server
npm run dev
```

### 3. Access the Dashboard

Open your browser to: http://localhost:3000

## Development

### Frontend (React + Vite)

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Backend (FastAPI)

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start API server
python api_server.py

# API will be available at http://localhost:8000
# WebSocket at ws://localhost:8001
```

## API Endpoints

- `GET /api/trades` - Get all trading history
- `GET /api/portfolio` - Get current portfolio state
- `GET /api/status` - Get bot status and configuration
- `GET /api/latest-trade` - Get most recent trade
- `GET /api/stats` - Get trading statistics
- `WS /ws` - WebSocket for real-time updates

## Integration with Trading Bot

The dashboard reads data from your trading bot's JSON files:
- `data/trades.json` - Trading history
- `data/portfolio.json` - Portfolio state
- `data/hyperparameters.json` - Bot configuration

Make sure your trading bot is running and generating these files for the dashboard to display data.

## Customization

### Styling
- Uses Tailwind CSS with custom design system
- Radix UI components for accessibility
- Dark/light mode support via CSS variables

### Charts
- Recharts library for responsive charts
- Custom tooltips and animations
- Real-time data updates

### Data Updates
- Polls API every 5 seconds
- WebSocket support for instant updates
- Error handling and retry logic

## Production Deployment

### Frontend
```bash
npm run build
# Deploy dist/ folder to your hosting service
```

### Backend
```bash
# Use a production WSGI server like Gunicorn
gunicorn api_server:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Troubleshooting

### No Data Showing
- Ensure your trading bot is running and generating data files
- Check that the API server can read the data files
- Verify file permissions in the `data/` directory

### Connection Issues
- Make sure the API server is running on port 8000
- Check CORS settings if accessing from different domains
- Verify WebSocket connection on port 8001

### Performance
- Large trade histories may slow down the chart rendering
- Consider implementing pagination for trade history
- Use WebSocket for real-time updates instead of polling
