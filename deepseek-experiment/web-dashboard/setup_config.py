#!/usr/bin/env python3
"""
Setup script to create config structure for Nixpacks/Railway builds.
This ensures the config module is available before api_server_supabase.py imports it.

Handles two scenarios:
1. If config/ directory already exists (parent root) - verify it's set up correctly
2. If config/ doesn't exist (web-dashboard root) - create from config_config.py
"""
import os
import sys
from pathlib import Path

def setup_config():
    """Create config directory structure if it doesn't exist."""
    config_dir = Path("config")
    
    # Check if config directory already exists (parent root scenario)
    if config_dir.exists() and (config_dir / "config.py").exists():
        print(f"✓ Config directory already exists at {config_dir.absolute()}")
        # Verify __init__.py exists
        init_py = config_dir / "__init__.py"
        if not init_py.exists():
            print(f"  Creating missing {init_py}...")
            # Use the same __init__.py content we created earlier
            init_content = '''"""Configuration module for the trading bot."""
from types import SimpleNamespace
import importlib.util
from pathlib import Path

# Load config.py as a module
_config_file = Path(__file__).parent / "config.py"
spec = importlib.util.spec_from_file_location("_config_module", _config_file)
_config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_config_module)

# Create config object from module-level variables
config = SimpleNamespace(
    PROJECT_ROOT=_config_module.PROJECT_ROOT,
    DATA_DIR=_config_module.DATA_DIR,
    LOG_DIR=_config_module.LOG_DIR,
    EXCHANGE=_config_module.EXCHANGE,
    USE_TESTNET=_config_module.USE_TESTNET,
    EXCHANGE_API_KEY=_config_module.EXCHANGE_API_KEY,
    EXCHANGE_API_SECRET=_config_module.EXCHANGE_API_SECRET,
    TESTNET_API_KEY=_config_module.TESTNET_API_KEY,
    TESTNET_API_SECRET=_config_module.TESTNET_API_SECRET,
    SYMBOL=_config_module.SYMBOL,
    INITIAL_BALANCE=_config_module.INITIAL_BALANCE,
    LLM_PROVIDER=_config_module.LLM_PROVIDER,
    LLM_API_KEY=_config_module.LLM_API_KEY,
    LLM_API_URL=_config_module.LLM_API_URL,
    LLM_MODEL=_config_module.LLM_MODEL,
    RUN_INTERVAL_SECONDS=_config_module.RUN_INTERVAL_SECONDS,
    TRADING_MODE=_config_module.TRADING_MODE,
    LOG_LEVEL=_config_module.LOG_LEVEL,
    LOG_FILE=_config_module.LOG_FILE,
    MAX_POSITION_SIZE=_config_module.MAX_POSITION_SIZE,
    STOP_LOSS_PERCENT=_config_module.STOP_LOSS_PERCENT,
    TAKE_PROFIT_PERCENT=_config_module.TAKE_PROFIT_PERCENT,
    MAX_LEVERAGE=_config_module.MAX_LEVERAGE,
    DEFAULT_LEVERAGE=_config_module.DEFAULT_LEVERAGE,
    TRADING_FEE_PERCENT=_config_module.TRADING_FEE_PERCENT,
    MAX_RISK_PER_TRADE=_config_module.MAX_RISK_PER_TRADE,
    MAX_ACTIVE_POSITIONS=_config_module.MAX_ACTIVE_POSITIONS,
    MIN_CONFIDENCE_THRESHOLD=_config_module.MIN_CONFIDENCE_THRESHOLD,
    FEE_IMPACT_WARNING_THRESHOLD=_config_module.FEE_IMPACT_WARNING_THRESHOLD,
)
'''
            init_py.write_text(init_content)
            print(f"  ✓ Created {init_py}")
        else:
            print(f"  ✓ {init_py} already exists")
        return
    
    # Config directory doesn't exist - create it from config_config.py (web-dashboard root)
    print("Creating config directory structure from config_config.py...")
    config_dir.mkdir(exist_ok=True)
    
    # Copy config_config.py to config/config.py
    config_py = config_dir / "config.py"
    config_config_py = Path("config_config.py")
    if config_config_py.exists():
        import shutil
        shutil.copy(config_config_py, config_py)
        print(f"  ✓ Created {config_py} from {config_config_py}")
    else:
        print(f"  ✗ Error: {config_config_py} not found!")
        sys.exit(1)
    
    # Create __init__.py (simple version for config_config.py)
    init_py = config_dir / "__init__.py"
    init_content = '''"""Configuration module for the trading bot."""
from .config import config
'''
    init_py.write_text(init_content)
    print(f"  ✓ Created {init_py}")

if __name__ == "__main__":
    setup_config()
    print("✓ Config setup complete")
