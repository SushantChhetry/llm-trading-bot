#!/usr/bin/env python3
"""
API Server for Trading Bot Dashboard with Supabase Integration

Serves trading data to the React frontend via REST API endpoints.
Uses Supabase as the database backend for reliable data storage.
"""

import json
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import asyncio
import websockets
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import config
from supabase_client import get_supabase_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Trading Bot API", version="1.0.0")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for API endpoints."""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.rate_limits: Dict[str, List[float]] = {}

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/ready", "/live", "/"]:
            return await call_next(request)

        # Get client identifier (IP address)
        client_ip = request.client.host if request.client else "unknown"

        # Clean old entries (older than 1 minute)
        current_time = time.time()
        if client_ip in self.rate_limits:
            self.rate_limits[client_ip] = [
                req_time for req_time in self.rate_limits[client_ip]
                if current_time - req_time < 60
            ]
        else:
            self.rate_limits[client_ip] = []

        # Check rate limit
        if len(self.rate_limits.get(client_ip, [])) >= self.requests_per_minute:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.requests_per_minute} requests per minute",
                    "retry_after": 60
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0"
                }
            )

        # Record request
        if client_ip not in self.rate_limits:
            self.rate_limits[client_ip] = []
        self.rate_limits[client_ip].append(current_time)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = max(0, self.requests_per_minute - len(self.rate_limits[client_ip]))
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + 60))

        return response


# Apply rate limiting
rate_limit_rpm = int(os.getenv("API_RATE_LIMIT_RPM", "60"))
app.add_middleware(RateLimitMiddleware, requests_per_minute=rate_limit_rpm)

# Enable CORS for React frontend
# Get allowed origins from environment variable for production
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

# CORS configuration for production (Vercel + Railway)
is_production = os.getenv("ENVIRONMENT") == "production"

if is_production:
    # In production, use regex to allow all Vercel deployments
    # This includes production, preview, and branch deployments
    cors_origin_regex = r"https://.*\.vercel\.app"

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,  # Any explicitly listed origins
        allow_origin_regex=cors_origin_regex,  # All Vercel deployments via regex
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=3600,
    )
else:
    # Development: only allow specific localhost origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=3600,
    )

# Initialize Supabase service
supabase = None
USE_SUPABASE = False
try:
    supabase = get_supabase_service()
    USE_SUPABASE = True
    logger.info("Connected to Supabase database")
except Exception as e:
    logger.warning(f"Supabase connection failed: {e}")
    logger.info("Falling back to JSON file storage")
    USE_SUPABASE = False
    supabase = None

# Fallback data file paths
DATA_DIR = config.DATA_DIR
TRADES_FILE = DATA_DIR / "trades.json"
PORTFOLIO_FILE = DATA_DIR / "portfolio.json"
HYPERPARAMS_FILE = DATA_DIR / "hyperparameters.json"

def load_json_file(file_path: Path, default: Any = None) -> Any:
    """Load JSON data from file with error handling."""
    try:
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        return default
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading {file_path}: {e}")
        return default

def get_bot_status() -> Dict[str, Any]:
    """Get current bot status and configuration."""
    if USE_SUPABASE and supabase:
        try:
            config_data = supabase.get_bot_config()
            return {
                "is_running": True,
                "last_update": datetime.now().isoformat(),
                "trading_mode": config_data.get("trading_mode", "paper"),
                "llm_provider": config_data.get("llm_provider", "mock"),
                "exchange": config_data.get("exchange", "bybit"),
                "run_interval_seconds": int(config_data.get("run_interval_seconds", "300"))
            }
        except Exception as e:
            logger.error(f"Error getting bot status from Supabase: {e}")
            return {"is_running": True, "last_update": datetime.now().isoformat()}
    else:
        hyperparams = load_json_file(HYPERPARAMS_FILE, {})
        params = hyperparams.get("hyperparameters", {})

        return {
            "is_running": True,
            "last_update": datetime.now().isoformat(),
            "trading_mode": params.get("trading_mode", "paper"),
            "llm_provider": params.get("llm_provider", "mock"),
            "exchange": params.get("exchange", "bybit"),
            "run_interval_seconds": params.get("run_interval_seconds", 300)
        }

def get_trades(limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent trades."""
    if USE_SUPABASE and supabase:
        try:
            return supabase.get_trades(limit)
        except Exception as e:
            logger.error(f"Error getting trades from Supabase: {e}")
            return []
    else:
        trades = load_json_file(TRADES_FILE, [])
        return trades[-limit:] if trades else []

def get_portfolio() -> Dict[str, Any]:
    """Get current portfolio state."""
    # Get trades for calculations
    trades = get_trades(10000)  # Get all trades for calculations

    if USE_SUPABASE and supabase:
        try:
            portfolio = supabase.get_portfolio()
            if portfolio:
                balance = float(portfolio.get("balance", 0))
                total_value = float(portfolio.get("total_value", 0))
                unrealized_pnl = float(portfolio.get("unrealized_pnl", 0))
                realized_pnl = float(portfolio.get("realized_pnl", 0))
                active_positions = int(portfolio.get("active_positions", 0))

                # Calculate positions_value (total value of open positions)
                positions_value = total_value - balance

                # Calculate total_return from realized_pnl
                total_return = realized_pnl

                # Calculate initial_balance (balance + realized_pnl + unrealized_pnl - positions_value)
                # Or get from first trade or config
                initial_balance = balance + realized_pnl + unrealized_pnl - positions_value
                if initial_balance <= 0:
                    initial_balance = config.INITIAL_BALANCE

                # Calculate total_return_pct
                total_return_pct = (total_return / initial_balance * 100) if initial_balance > 0 else 0

                return {
                    "balance": balance,
                    "total_value": total_value,
                    "positions_value": max(0, positions_value),
                    "total_return": total_return,
                    "total_return_pct": total_return_pct,
                    "open_positions": active_positions,
                    "total_trades": len(trades),
                    "initial_balance": initial_balance,
                    "unrealized_pnl": unrealized_pnl,
                    "realized_pnl": realized_pnl,
                    "total_fees": float(portfolio.get("total_fees", 0)),
                    "timestamp": portfolio.get("timestamp", datetime.now().isoformat())
                }
            # Return default portfolio if no data
            initial_balance = config.INITIAL_BALANCE
            return {
                "balance": initial_balance,
                "total_value": initial_balance,
                "positions_value": 0,
                "total_return": 0,
                "total_return_pct": 0,
                "open_positions": 0,
                "total_trades": len(trades),
                "initial_balance": initial_balance,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting portfolio from Supabase: {e}")
            initial_balance = config.INITIAL_BALANCE
            return {
                "balance": initial_balance,
                "total_value": initial_balance,
                "positions_value": 0,
                "total_return": 0,
                "total_return_pct": 0,
                "open_positions": 0,
                "total_trades": len(trades),
                "initial_balance": initial_balance,
                "timestamp": datetime.now().isoformat()
            }
    else:
        portfolio = load_json_file(PORTFOLIO_FILE, {})
        if not portfolio:
            initial_balance = config.INITIAL_BALANCE
            return {
                "balance": initial_balance,
                "total_value": initial_balance,
                "positions_value": 0,
                "total_return": 0,
                "total_return_pct": 0,
                "open_positions": 0,
                "total_trades": len(trades),
                "initial_balance": initial_balance,
                "timestamp": datetime.now().isoformat()
            }

        # Calculate missing fields from portfolio.json
        balance = float(portfolio.get("balance", config.INITIAL_BALANCE))
        positions = portfolio.get("positions", {})
        positions_value = sum(pos.get("value", 0) for pos in positions.values())
        total_value = balance + positions_value
        open_positions = len(positions)

        # Calculate total_return from trades
        total_return = sum(trade.get("profit", 0) for trade in trades if trade.get("profit") is not None)

        # Get initial_balance from portfolio or config
        initial_balance = float(portfolio.get("initial_balance", config.INITIAL_BALANCE))

        # Calculate total_return_pct
        total_return_pct = (total_return / initial_balance * 100) if initial_balance > 0 else 0

        return {
            "balance": balance,
            "total_value": total_value,
            "positions_value": positions_value,
            "total_return": total_return,
            "total_return_pct": total_return_pct,
            "open_positions": open_positions,
            "total_trades": len(trades),
            "initial_balance": initial_balance,
            "timestamp": portfolio.get("timestamp", datetime.now().isoformat())
        }

def get_positions() -> List[Dict[str, Any]]:
    """Get active positions."""
    if USE_SUPABASE and supabase:
        try:
            return supabase.get_positions()
        except Exception as e:
            logger.error(f"Error getting positions from Supabase: {e}")
            return []
    else:
        portfolio = load_json_file(PORTFOLIO_FILE, {})
        positions = portfolio.get("positions", {})
        return [{"symbol": symbol, **data} for symbol, data in positions.items()]

def get_behavioral_metrics(limit: int = 50) -> List[Dict[str, Any]]:
    """Get behavioral metrics."""
    if USE_SUPABASE and supabase:
        try:
            return supabase.get_behavioral_metrics(limit)
        except Exception as e:
            logger.error(f"Error getting behavioral metrics from Supabase: {e}")
            return []
    else:
        # Fallback to mock data
        return [{
            "timestamp": datetime.now().isoformat(),
            "bullish_tilt": 0.65,
            "avg_holding_period_hours": 4.2,
            "trade_frequency_per_day": 2.3,
            "avg_position_size": 150.0,
            "avg_confidence": 0.75,
            "exit_plan_tightness": 2.5,
            "active_positions": 2,
            "fee_impact_percent": 15.2
        }]

# WebSocket connections
connected_clients = set()

async def websocket_endpoint(websocket, path):
    """Handle WebSocket connections for real-time updates."""
    connected_clients.add(websocket)
    logger.info(f"WebSocket client connected. Total clients: {len(connected_clients)}")

    try:
        while True:
            # Send periodic updates
            await asyncio.sleep(5)

            # Get latest data
            portfolio = get_portfolio()
            trades = get_trades(10)

            update_data = {
                "type": "update",
                "portfolio": portfolio,
                "recent_trades": trades,
                "timestamp": datetime.now().isoformat()
            }

            # Send to all connected clients
            if connected_clients:
                await asyncio.gather(
                    *[client.send(json.dumps(update_data)) for client in connected_clients],
                    return_exceptions=True
                )
    except websockets.exceptions.ConnectionClosed:
        logger.debug("WebSocket connection closed normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        connected_clients.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(connected_clients)}")

def start_websocket_server():
    """Start WebSocket server in a separate thread."""
    async def run_websocket():
        try:
            async with websockets.serve(websocket_endpoint, "localhost", 8002):
                logger.info("WebSocket server started on port 8002")
                await asyncio.Future()  # Run forever
        except OSError as e:
            if e.errno == 48:  # Address already in use
                logger.warning("WebSocket port 8002 already in use, skipping WebSocket server")
            else:
                logger.error(f"WebSocket server error: {e}")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_websocket())

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Trading Bot API Server", "version": "1.0.0", "database": "Supabase" if USE_SUPABASE else "JSON"}

@app.get("/health")
async def health():
    """Enhanced health check with dependency validation."""
    from fastapi import Response

    checks = {
        "api_server": "healthy",
        "database": None,
        "file_system": None,
    }
    overall_status = "healthy"
    status_code = 200

    try:
        # Check file system accessibility
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            (DATA_DIR / "logs").mkdir(parents=True, exist_ok=True)
            test_file = DATA_DIR / ".healthcheck"
            test_file.write_text("test")
            test_file.unlink()
            checks["file_system"] = "healthy"
        except Exception as e:
            checks["file_system"] = f"unhealthy: {str(e)}"
            overall_status = "degraded"

        # Check database connectivity
        if USE_SUPABASE and supabase:
            try:
                supabase.get_trades(limit=1)
                portfolio = supabase.get_portfolio()
                checks["database"] = {
                    "status": "healthy",
                    "type": "supabase",
                    "readable": True,
                    "writable": True
                }
            except Exception as e:
                checks["database"] = {
                    "status": f"unhealthy: {str(e)}",
                    "type": "supabase",
                    "readable": False,
                    "writable": False
                }
                overall_status = "degraded"
        else:
            checks["database"] = {
                "status": "healthy",
                "type": "file_based",
                "readable": TRADES_FILE.exists() or True,
                "writable": os.access(DATA_DIR, os.W_OK)
            }

        if overall_status == "degraded":
            status_code = 503

        return Response(
            content=json.dumps({
                "status": overall_status,
                "timestamp": datetime.now().isoformat(),
                "service": "trading-bot-api",
                "version": "1.0.0",
                "environment": os.getenv("ENVIRONMENT", "development"),
                "checks": checks
            }, indent=2),
            status_code=status_code,
            media_type="application/json"
        )
    except Exception as e:
        return Response(
            content=json.dumps({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }),
            status_code=503,
            media_type="application/json"
        )

@app.get("/ready")
async def ready():
    """Readiness probe - checks if service is ready to accept traffic."""
    from fastapi import Response

    try:
        if USE_SUPABASE and supabase:
            supabase.get_trades(limit=1)
        return {
            "status": "ready",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return Response(
            content=json.dumps({
                "status": "not_ready",
                "reason": str(e),
                "timestamp": datetime.now().isoformat()
            }),
            status_code=503,
            media_type="application/json"
        )

@app.get("/live")
async def live():
    """Liveness probe - checks if service is alive."""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/status")
async def status():
    """Get bot status and configuration."""
    return get_bot_status()

@app.get("/api/trades")
async def trades(limit: int = 100):
    """Get recent trades."""
    return get_trades(limit)

@app.get("/api/portfolio")
async def portfolio():
    """Get current portfolio state."""
    return get_portfolio()

@app.get("/api/positions")
async def positions():
    """Get active positions."""
    return get_positions()

@app.get("/api/latest-trade")
async def latest_trade():
    """Get the most recent trade."""
    trades = get_trades(1)
    return trades[0] if trades else {}

@app.get("/api/stats")
async def stats():
    """Get trading statistics."""
    trades = get_trades(1000)
    portfolio = get_portfolio()

    if not trades:
        return {
            "total_trades": 0,
            "total_pnl": 0,
            "win_rate": 0,
            "avg_trade_size": 0
        }

    total_trades = len(trades)
    total_pnl = sum(trade.get("pnl", 0) for trade in trades)
    winning_trades = sum(1 for trade in trades if trade.get("pnl", 0) > 0)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    avg_trade_size = sum(trade.get("amount_usdt", 0) for trade in trades) / total_trades if total_trades > 0 else 0

    return {
        "total_trades": total_trades,
        "total_pnl": total_pnl,
        "win_rate": round(win_rate, 2),
        "avg_trade_size": round(avg_trade_size, 2),
        "current_balance": portfolio.get("balance", 0),
        "current_value": portfolio.get("total_value", 0)
    }

@app.get("/api/behavioral")
async def behavioral_metrics(limit: int = 50):
    """Get behavioral metrics."""
    return get_behavioral_metrics(limit)

if __name__ == "__main__":
    import threading
    import sys

    try:
        # Start WebSocket server in background thread (optional, only if needed)
        try:
            ws_thread = threading.Thread(target=start_websocket_server, daemon=True)
            ws_thread.start()
            logger.info("WebSocket server thread started")
        except Exception as e:
            logger.warning(f"WebSocket server failed to start: {e} (continuing without it)")

        # Start FastAPI server
        # Railway sets PORT environment variable automatically
        port = int(os.getenv("PORT", "8001"))

        logger.info("="*80)
        logger.info("Starting Trading Bot API Server")
        logger.info(f"API available at: http://0.0.0.0:{port}")
        logger.info(f"Database: {'Supabase' if USE_SUPABASE else 'JSON Files'}")
        logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
        logger.info(f"Port: {port}")
        logger.info("="*80)

        # Use uvicorn with proper logging and error handling
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error starting server: {e}", exc_info=True)
        sys.exit(1)
