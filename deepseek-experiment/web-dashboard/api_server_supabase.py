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

# Add project root to path (for container compatibility)
# In container: /app/api_server_supabase.py -> /app is already in PYTHONPATH
# But we add it explicitly to ensure it works in all environments
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config import config
from supabase_client import get_supabase_service

# Configure logging first (needed for import fallback)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Import get_default_configuration with fallback
try:
    from config.config import get_default_configuration
except ImportError as e:
    # Fallback if import fails (e.g., running from different directory)
    logger.warning(f"Failed to import get_default_configuration from config.config: {e}")
    config_path = project_root.parent / "config" / "config.py"
    if config_path.exists():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("config.config", config_path)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            get_default_configuration = config_module.get_default_configuration
            logger.info("Successfully loaded get_default_configuration from fallback path")
        except Exception as fallback_error:
            logger.error(f"Fallback import also failed: {fallback_error}")
            # Last resort: define a minimal default config function
            def get_default_configuration():
                logger.warning("Using minimal default config - config.config not available")
                return {
                    "llm": {"provider": "mock", "api_key": "", "api_url": "", "model": "", "temperature": 0.7, "max_tokens": 500, "timeout": 30},
                    "exchange": {"name": "kraken", "symbol": "BTC/USDT", "use_testnet": True},
                    "trading": {"mode": "paper", "initial_balance": 10000.0, "max_position_size": 0.1, "max_leverage": 10.0, "default_leverage": 1.0, "trading_fee_percent": 0.05, "max_risk_per_trade": 2.0, "stop_loss_percent": 2.0, "take_profit_percent": 3.0, "max_active_positions": 6, "min_confidence_threshold": 0.6, "fee_impact_warning_threshold": 20.0, "run_interval_seconds": 150},
                    "position_management": {"enable_position_monitoring": True, "portfolio_profit_target_pct": 10.0, "enable_trailing_stop_loss": True, "trailing_stop_distance_pct": 1.0, "trailing_stop_activation_pct": 0.5, "enable_partial_profit_taking": True, "partial_profit_percent": 50.0, "partial_profit_target_pct": 1.5},
                    "logging": {"level": "INFO"}
                }
    else:
        # Last resort: define a minimal default config function
        def get_default_configuration():
            logger.warning(f"Config file not found at {config_path}, using minimal default config")
            return {
                "llm": {"provider": "mock", "api_key": "", "api_url": "", "model": "", "temperature": 0.7, "max_tokens": 500, "timeout": 30},
                "exchange": {"name": "kraken", "symbol": "BTC/USDT", "use_testnet": True},
                "trading": {"mode": "paper", "initial_balance": 10000.0, "max_position_size": 0.1, "max_leverage": 10.0, "default_leverage": 1.0, "trading_fee_percent": 0.05, "max_risk_per_trade": 2.0, "stop_loss_percent": 2.0, "take_profit_percent": 3.0, "max_active_positions": 6, "min_confidence_threshold": 0.6, "fee_impact_warning_threshold": 20.0, "run_interval_seconds": 150},
                "position_management": {"enable_position_monitoring": True, "portfolio_profit_target_pct": 10.0, "enable_trailing_stop_loss": True, "trailing_stop_distance_pct": 1.0, "trailing_stop_activation_pct": 0.5, "enable_partial_profit_taking": True, "partial_profit_percent": 50.0, "partial_profit_target_pct": 1.5},
                "logging": {"level": "INFO"}
            }

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
SUPABASE_ERROR = None
try:
    supabase = get_supabase_service()
    # Test the connection by trying to get trades
    try:
        test_trades = supabase.get_trades(limit=1)
        USE_SUPABASE = True
        logger.info(f"Connected to Supabase database (test query returned {len(test_trades)} trades)")
    except Exception as test_e:
        logger.warning(f"Supabase connection test failed: {test_e}")
        USE_SUPABASE = False
        SUPABASE_ERROR = str(test_e)
        supabase = None
except Exception as e:
    logger.warning(f"Supabase connection failed: {e}")
    logger.info("Falling back to JSON file storage")
    USE_SUPABASE = False
    SUPABASE_ERROR = str(e)
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
                "exchange": config_data.get("exchange", "kraken"),
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
            "exchange": params.get("exchange", "kraken"),
            "run_interval_seconds": params.get("run_interval_seconds", 300)
        }

def get_trades(limit: int = 100) -> List[Dict[str, Any]]:
    """Get recent trades."""
    if USE_SUPABASE and supabase:
        try:
            trades = supabase.get_trades(limit)
            logger.debug(f"Fetched {len(trades)} trades from Supabase")
            return trades
        except Exception as e:
            logger.error(f"Error getting trades from Supabase: {e}", exc_info=True)
            # Fallback to JSON file on error
            trades = load_json_file(TRADES_FILE, [])
            return trades[-limit:] if trades else []
    else:
        logger.debug("Using JSON file storage (Supabase not connected)")
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
    return {
        "message": "Trading Bot API Server",
        "version": "1.0.0",
        "database": "Supabase" if USE_SUPABASE else "JSON",
        "supabase_connected": USE_SUPABASE,
        "supabase_error": SUPABASE_ERROR if SUPABASE_ERROR else None
    }

@app.get("/health")
async def health():
    """
    Enhanced health check endpoint for Railway.
    Returns 200 if the service is running, includes bot service health from Supabase.
    """
    health_data = {
        "status": "healthy",
        "service": "trading-bot-api",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "supabase_connected": USE_SUPABASE
    }
    
    # Get bot service health from Supabase
    if USE_SUPABASE and supabase:
        try:
            bot_health = supabase.get_latest_health(service_name="trading-bot")
            if bot_health:
                health_data["bot_service"] = {
                    "status": bot_health.get("status", "unknown"),
                    "last_check": bot_health.get("timestamp"),
                    "details": bot_health.get("details", {})
                }
            else:
                health_data["bot_service"] = {
                    "status": "unknown",
                    "message": "No health check data available"
                }
        except Exception as e:
            health_data["bot_service"] = {
                "status": "error",
                "error": str(e)
            }
    
    return health_data

@app.get("/debug/supabase")
async def debug_supabase():
    """Debug endpoint to check Supabase connection status."""
    debug_info = {
        "supabase_connected": USE_SUPABASE,
        "supabase_error": SUPABASE_ERROR,
        "has_supabase_client": supabase is not None,
        "supabase_url": os.getenv("SUPABASE_URL", "NOT SET")[:50] + "..." if os.getenv("SUPABASE_URL") else "NOT SET",
        "supabase_key_set": bool(os.getenv("SUPABASE_KEY")),
        "supabase_key_length": len(os.getenv("SUPABASE_KEY", ""))
    }

    if USE_SUPABASE and supabase:
        try:
            test_trades = supabase.get_trades(limit=1)
            debug_info["test_query_success"] = True
            debug_info["test_trades_count"] = len(test_trades)
            debug_info["test_trades_sample"] = test_trades[0] if test_trades else None
        except Exception as e:
            debug_info["test_query_success"] = False
            debug_info["test_query_error"] = str(e)

    return debug_info

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

@app.get("/metrics")
async def metrics(service_name: Optional[str] = None, metric_name: Optional[str] = None, limit: int = 1000):
    """
    Get metrics in Prometheus-style format (JSON).
    Supports filtering by service_name and metric_name.
    """
    if not USE_SUPABASE or not supabase:
        return {
            "error": "Supabase not available",
            "metrics": []
        }
    
    try:
        from datetime import timedelta
        # Default to last 24 hours if no filter specified
        since = datetime.now() - timedelta(hours=24) if not service_name and not metric_name else None
        
        metrics_data = supabase.get_metrics(
            service_name=service_name,
            metric_name=metric_name,
            since=since,
            limit=limit
        )
        
        return {
            "service": "trading-bot-api",
            "timestamp": datetime.now().isoformat(),
            "count": len(metrics_data),
            "metrics": metrics_data
        }
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/observability")
async def observability():
    """
    Comprehensive observability endpoint.
    Returns metrics, health status, and alerts for all services.
    """
    if not USE_SUPABASE or not supabase:
        return {
            "error": "Supabase not available",
            "services": {}
        }
    
    try:
        from datetime import timedelta
        
        # Get metrics for all services (last hour)
        since = datetime.now() - timedelta(hours=1)
        all_metrics = supabase.get_metrics(since=since, limit=5000)
        
        # Get health status for all services
        bot_health = supabase.get_latest_health(service_name="trading-bot")
        api_health = {
            "status": "healthy",
            "service_name": "trading-bot-api",
            "timestamp": datetime.now().isoformat(),
            "details": {
                "supabase_connected": USE_SUPABASE
            }
        }
        
        # Group metrics by service
        services_metrics = {}
        for metric in all_metrics:
            svc_name = metric.get("service_name", "unknown")
            if svc_name not in services_metrics:
                services_metrics[svc_name] = []
            services_metrics[svc_name].append(metric)
        
        # Aggregate metrics by type
        metrics_summary = {}
        for svc_name, metrics_list in services_metrics.items():
            counters = {}
            gauges = {}
            histograms = {}
            
            for metric in metrics_list:
                metric_name = metric.get("metric_name", "")
                metric_type = metric.get("metric_type", "gauge")
                value = metric.get("value", 0)
                
                if metric_type == "counter":
                    counters[metric_name] = counters.get(metric_name, 0) + value
                elif metric_type == "gauge":
                    # For gauges, take the latest value
                    if metric_name not in gauges or metric.get("timestamp", "") > gauges[metric_name].get("timestamp", ""):
                        gauges[metric_name] = {
                            "value": value,
                            "timestamp": metric.get("timestamp", "")
                        }
                elif metric_type == "histogram":
                    if metric_name not in histograms:
                        histograms[metric_name] = []
                    histograms[metric_name].append(value)
            
            metrics_summary[svc_name] = {
                "counters": {k: v for k, v in counters.items()},
                "gauges": {k: v.get("value") if isinstance(v, dict) else v for k, v in gauges.items()},
                "histograms": {k: {"count": len(v), "min": min(v) if v else 0, "max": max(v) if v else 0, "avg": sum(v)/len(v) if v else 0} for k, v in histograms.items()}
            }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "services": {
                "trading-bot": {
                    "health": bot_health,
                    "metrics": metrics_summary.get("trading-bot", {})
                },
                "trading-bot-api": {
                    "health": api_health,
                    "metrics": {}
                }
            },
            "metrics_summary": metrics_summary
        }
    except Exception as e:
        logger.error(f"Error fetching observability data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/historical")
async def metrics_historical(
    service_name: Optional[str] = None,
    metric_name: Optional[str] = None,
    hours: int = 24,
    limit: int = 10000
):
    """
    Get historical metrics data for time-series analysis.
    """
    if not USE_SUPABASE or not supabase:
        return {
            "error": "Supabase not available",
            "metrics": []
        }
    
    try:
        from datetime import timedelta
        since = datetime.now() - timedelta(hours=hours)
        
        metrics_data = supabase.get_metrics(
            service_name=service_name,
            metric_name=metric_name,
            since=since,
            limit=limit
        )
        
        # Group by metric name and create time series
        time_series = {}
        for metric in metrics_data:
            name = metric.get("metric_name", "unknown")
            if name not in time_series:
                time_series[name] = []
            time_series[name].append({
                "timestamp": metric.get("timestamp", ""),
                "value": metric.get("value", 0),
                "type": metric.get("metric_type", "gauge")
            })
        
        return {
            "service": service_name or "all",
            "metric": metric_name or "all",
            "time_range_hours": hours,
            "count": len(metrics_data),
            "time_series": time_series,
            "raw_metrics": metrics_data[:100]  # Include first 100 for reference
        }
    except Exception as e:
        logger.error(f"Error fetching historical metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/snapshots")
async def portfolio_snapshots(limit: int = 1000):
    """Get portfolio snapshots history."""
    if USE_SUPABASE and supabase:
        try:
            snapshots = supabase.get_portfolio_snapshots(limit)
            logger.debug(f"Fetched {len(snapshots)} portfolio snapshots from Supabase")
            return snapshots
        except Exception as e:
            logger.error(f"Error getting portfolio snapshots from Supabase: {e}")
            return []
    else:
        # Fallback: generate snapshots from trades and current portfolio
        logger.debug("Using fallback portfolio snapshots (Supabase not connected)")
        portfolio = get_portfolio()
        trades = get_trades(10000)
        
        if not trades:
            return []
        
        # Generate snapshots from trades
        snapshots = []
        initial_balance = portfolio.get("initial_balance", config.INITIAL_BALANCE)
        running_value = initial_balance
        running_return = 0
        
        sorted_trades = sorted(trades, key=lambda t: t.get("timestamp", ""))
        
        for trade in sorted_trades:
            if trade.get("side") == "buy":
                running_value -= trade.get("amount_usdt", 0)
            elif trade.get("side") == "sell":
                running_value += trade.get("quantity", 0) * trade.get("price", 0)
                if trade.get("profit"):
                    running_return += trade.get("profit", 0)
            
            snapshots.append({
                "timestamp": trade.get("timestamp", datetime.now().isoformat()),
                "balance": running_value,
                "total_value": running_value,
                "positions_value": 0,
                "total_return": running_return,
                "total_return_pct": (running_return / initial_balance * 100) if initial_balance > 0 else 0,
                "unrealized_pnl": 0,
                "realized_pnl": running_return,
                "total_fees": 0,
                "active_positions": 0,
            })
        
        return snapshots

# Configuration Management Endpoints
@app.get("/api/config/current")
async def get_current_config():
    """Get the currently active configuration from Supabase."""
    if not USE_SUPABASE or not supabase:
        # Return default config if Supabase not available
        try:
            return {
                "config": get_default_configuration(),
                "source": "default",
                "is_active": True,
                "version": None
            }
        except Exception as e:
            logger.error(f"Error getting default config: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get configuration: {str(e)}")
    
    try:
        active_config = supabase.get_active_configuration()
        if active_config:
            # Extract config_json and metadata
            config_json = active_config.get("config_json", {})
            return {
                "config": config_json,
                "source": "supabase",
                "is_active": True,
                "version": active_config.get("version"),
                "name": active_config.get("name"),
                "description": active_config.get("description"),
                "created_at": active_config.get("created_at"),
                "id": active_config.get("id")
            }
        else:
            # No active config, return defaults
            return {
                "config": get_default_configuration(),
                "source": "default",
                "is_active": False,
                "version": None
            }
    except Exception as e:
        logger.error(f"Error getting current configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config/default")
async def get_default_config():
    """Get the default system configuration."""
    try:
        default_config = get_default_configuration()
        
        # Also check if there's a default in Supabase
        if USE_SUPABASE and supabase:
            supabase_default = supabase.get_default_configuration()
            if supabase_default:
                return {
                    "config": supabase_default.get("config_json", default_config),
                    "source": "supabase_default",
                    "is_default": True,
                    "version": supabase_default.get("version"),
                    "name": supabase_default.get("name"),
                    "id": supabase_default.get("id")
                }
        
        return {
            "config": default_config,
            "source": "config.py",
            "is_default": True,
            "version": None
        }
    except Exception as e:
        logger.error(f"Error getting default configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config/history")
async def get_config_history(limit: int = 50):
    """Get all configuration versions from Supabase."""
    if not USE_SUPABASE or not supabase:
        raise HTTPException(status_code=503, detail="Supabase not available")
    
    try:
        history = supabase.get_configuration_history(limit)
        return {
            "configurations": history,
            "count": len(history)
        }
    except Exception as e:
        logger.error(f"Error getting configuration history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/save")
async def save_config(request: Request):
    """Save a new configuration version to Supabase."""
    if not USE_SUPABASE or not supabase:
        raise HTTPException(status_code=503, detail="Supabase not available")
    
    try:
        body = await request.json()
        config_data = body.get("config")
        name = body.get("name", "Custom Configuration")
        description = body.get("description", "")
        activate = body.get("activate", False)
        
        if not config_data:
            raise HTTPException(status_code=400, detail="Configuration data is required")
        
        # Validate configuration structure
        required_sections = ["llm", "exchange", "trading"]
        for section in required_sections:
            if section not in config_data:
                raise HTTPException(status_code=400, detail=f"Missing required section: {section}")
        
        # Validate LLM configuration
        llm = config_data.get("llm", {})
        if llm.get("temperature", 0) < 0 or llm.get("temperature", 0) > 2:
            raise HTTPException(status_code=400, detail="LLM temperature must be between 0 and 2")
        if llm.get("max_tokens", 0) < 1 or llm.get("max_tokens", 0) > 100000:
            raise HTTPException(status_code=400, detail="Max tokens must be between 1 and 100,000")
        if llm.get("timeout", 0) < 1 or llm.get("timeout", 0) > 300:
            raise HTTPException(status_code=400, detail="Timeout must be between 1 and 300 seconds")
        
        # Validate Trading configuration
        trading = config_data.get("trading", {})
        if trading.get("mode") not in ["paper", "live"]:
            raise HTTPException(status_code=400, detail="Trading mode must be 'paper' or 'live'")
        if trading.get("initial_balance", 0) <= 0:
            raise HTTPException(status_code=400, detail="Initial balance must be greater than 0")
        if trading.get("max_position_size", 0) <= 0 or trading.get("max_position_size", 0) > 1:
            raise HTTPException(status_code=400, detail="Max position size must be between 0 and 1")
        if trading.get("max_leverage", 0) < 1 or trading.get("max_leverage", 0) > 100:
            raise HTTPException(status_code=400, detail="Max leverage must be between 1 and 100")
        if trading.get("stop_loss_percent", 0) <= 0 or trading.get("stop_loss_percent", 0) > 50:
            raise HTTPException(status_code=400, detail="Stop loss must be between 0 and 50%")
        if trading.get("take_profit_percent", 0) <= 0 or trading.get("take_profit_percent", 0) > 100:
            raise HTTPException(status_code=400, detail="Take profit must be between 0 and 100%")
        if trading.get("max_active_positions", 0) < 1 or trading.get("max_active_positions", 0) > 50:
            raise HTTPException(status_code=400, detail="Max active positions must be between 1 and 50")
        if trading.get("min_confidence_threshold", 0) < 0 or trading.get("min_confidence_threshold", 0) > 1:
            raise HTTPException(status_code=400, detail="Min confidence threshold must be between 0 and 1")
        if trading.get("run_interval_seconds", 0) < 10 or trading.get("run_interval_seconds", 0) > 3600:
            raise HTTPException(status_code=400, detail="Run interval must be between 10 and 3600 seconds")
        
        # Validate Exchange configuration
        exchange = config_data.get("exchange", {})
        if exchange.get("name") not in ["kraken", "bybit", "binance", "coinbase"]:
            raise HTTPException(status_code=400, detail="Invalid exchange name")
        if not exchange.get("symbol") or not exchange.get("symbol", "").strip():
            raise HTTPException(status_code=400, detail="Trading symbol is required")
        
        # Validate Position Management (if present)
        position_mgmt = config_data.get("position_management", {})
        if position_mgmt.get("portfolio_profit_target_pct", 0) < 0 or position_mgmt.get("portfolio_profit_target_pct", 0) > 100:
            raise HTTPException(status_code=400, detail="Portfolio profit target must be between 0 and 100%")
        if position_mgmt.get("trailing_stop_distance_pct", 0) < 0 or position_mgmt.get("trailing_stop_distance_pct", 0) > 10:
            raise HTTPException(status_code=400, detail="Trailing stop distance must be between 0 and 10%")
        if position_mgmt.get("partial_profit_percent", 0) < 0 or position_mgmt.get("partial_profit_percent", 0) > 100:
            raise HTTPException(status_code=400, detail="Partial profit percent must be between 0 and 100%")
        
        # Save configuration
        saved_config = supabase.save_configuration(
            config_data=config_data,
            name=name,
            description=description,
            created_by="api_user"
        )
        
        if not saved_config:
            raise HTTPException(status_code=500, detail="Failed to save configuration")
        
        # Activate if requested
        if activate:
            config_id = saved_config.get("id")
            if config_id:
                supabase.activate_configuration(config_id)
                saved_config["is_active"] = True
        
        return {
            "success": True,
            "configuration": saved_config,
            "message": "Configuration saved successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/activate/{config_id}")
async def activate_config(config_id: int):
    """Activate a specific configuration version."""
    if not USE_SUPABASE or not supabase:
        raise HTTPException(status_code=503, detail="Supabase not available")
    
    try:
        success = supabase.activate_configuration(config_id)
        if success:
            config = supabase.get_configuration_by_id(config_id)
            return {
                "success": True,
                "configuration": config,
                "message": f"Configuration {config_id} activated successfully"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config/reset")
async def reset_config():
    """Reset to default configuration."""
    if not USE_SUPABASE or not supabase:
        raise HTTPException(status_code=503, detail="Supabase not available")
    
    try:
        # Try to reset to default in Supabase
        success = supabase.reset_to_default()
        
        if success:
            default_config = supabase.get_default_configuration()
            return {
                "success": True,
                "configuration": default_config,
                "message": "Reset to default configuration successfully"
            }
        else:
            # No default in Supabase, return config.py defaults
            return {
                "success": True,
                "config": get_default_configuration(),
                "source": "config.py",
                "message": "Using config.py defaults (no default in Supabase)"
            }
    except Exception as e:
        logger.error(f"Error resetting configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

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
