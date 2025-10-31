#!/usr/bin/env python3
"""
API Server for Trading Bot Dashboard

Serves trading data to the React frontend via REST API endpoints.
Uses Supabase as the database backend for reliable data storage.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import asyncio
import websockets
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import config
from supabase_client import get_supabase_service

app = FastAPI(title="Trading Bot API", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data file paths
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
        print(f"Error loading {file_path}: {e}")
        return default

def get_bot_status() -> Dict[str, Any]:
    """Get current bot status and configuration."""
    hyperparams = load_json_file(HYPERPARAMS_FILE, {})
    params = hyperparams.get("hyperparameters", {})
    
    return {
        "is_running": True,  # Assume running if API is responding
        "last_update": datetime.now().isoformat(),
        "trading_mode": params.get("trading_mode", config.TRADING_MODE),
        "llm_provider": params.get("llm_provider", config.LLM_PROVIDER),
        "exchange": params.get("exchange", config.EXCHANGE),
        "run_interval_seconds": params.get("run_interval_seconds", config.RUN_INTERVAL_SECONDS),
    }

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Trading Bot API Server", "status": "running"}

@app.get("/api/trades")
async def get_trades():
    """Get all trading history."""
    trades = load_json_file(TRADES_FILE, [])
    return trades

@app.get("/api/portfolio")
async def get_portfolio():
    """Get current portfolio state."""
    portfolio = load_json_file(PORTFOLIO_FILE)
    trades = load_json_file(TRADES_FILE, [])
    
    if not portfolio:
        # Return default portfolio if no data
        return {
            "balance": config.INITIAL_BALANCE,
            "total_value": config.INITIAL_BALANCE,
            "positions_value": 0,
            "total_return": 0,
            "total_return_pct": 0,
            "open_positions": 0,
            "total_trades": len(trades),
            "initial_balance": config.INITIAL_BALANCE,
        }
    
    # Ensure all required fields are present
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
    
    # Return complete portfolio with all required fields
    return {
        "balance": balance,
        "total_value": total_value,
        "positions_value": positions_value,
        "total_return": total_return,
        "total_return_pct": total_return_pct,
        "open_positions": open_positions,
        "total_trades": len(trades),
        "initial_balance": initial_balance,
        **{k: v for k, v in portfolio.items() if k not in ["balance", "total_value", "positions_value", "total_return", "total_return_pct", "open_positions", "total_trades", "initial_balance"]}
    }

@app.get("/api/status")
async def get_status():
    """Get bot status and configuration."""
    return get_bot_status()

@app.get("/api/latest-trade")
async def get_latest_trade():
    """Get the most recent trade."""
    trades = load_json_file(TRADES_FILE, [])
    if trades:
        return trades[-1]
    return None

@app.get("/api/stats")
async def get_stats():
    """Get trading statistics."""
    trades = load_json_file(TRADES_FILE, [])
    portfolio = load_json_file(PORTFOLIO_FILE, {})
    
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "avg_profit": 0,
            "total_profit": 0,
            "best_trade": 0,
            "worst_trade": 0,
        }
    
    # Calculate statistics
    profitable_trades = [t for t in trades if t.get("profit", 0) > 0]
    total_profit = sum(t.get("profit", 0) for t in trades)
    
    profits = [t.get("profit", 0) for t in trades if "profit" in t]
    
    return {
        "total_trades": len(trades),
        "win_rate": len(profitable_trades) / len(trades) * 100 if trades else 0,
        "avg_profit": total_profit / len(trades) if trades else 0,
        "total_profit": total_profit,
        "best_trade": max(profits) if profits else 0,
        "worst_trade": min(profits) if profits else 0,
        "portfolio_value": portfolio.get("total_value", 0),
        "total_return_pct": portfolio.get("total_return_pct", 0),
    }

# WebSocket endpoint for real-time updates
connected_clients = set()

async def websocket_endpoint(websocket, path):
    """WebSocket endpoint for real-time updates."""
    connected_clients.add(websocket)
    print(f"Client connected. Total clients: {len(connected_clients)}")
    
    try:
        while True:
            # Send periodic updates
            await asyncio.sleep(5)  # Update every 5 seconds
            
            # Get latest data
            portfolio = load_json_file(PORTFOLIO_FILE)
            trades = load_json_file(TRADES_FILE, [])
            status = get_bot_status()
            
            update_data = {
                "type": "update",
                "timestamp": datetime.now().isoformat(),
                "portfolio": portfolio,
                "latest_trade": trades[-1] if trades else None,
                "status": status,
            }
            
            # Send to all connected clients
            if connected_clients:
                await asyncio.gather(
                    *[client.send(json.dumps(update_data)) for client in connected_clients],
                    return_exceptions=True
                )
                
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(websocket)
        print(f"Client disconnected. Total clients: {len(connected_clients)}")

def start_websocket_server():
    """Start WebSocket server in a separate thread."""
    async def run_websocket():
        async with websockets.serve(websocket_endpoint, "localhost", 8002):
            await asyncio.Future()  # Run forever
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_websocket())

if __name__ == "__main__":
    import threading
    
    # Start WebSocket server in background thread
    ws_thread = threading.Thread(target=start_websocket_server, daemon=True)
    ws_thread.start()
    
    # Start FastAPI server
    print("🚀 Starting Trading Bot API Server...")
    print("📊 API available at: http://localhost:8001")
    print("🔌 WebSocket available at: ws://localhost:8002")
    print("🌐 Dashboard available at: http://localhost:3000")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)
