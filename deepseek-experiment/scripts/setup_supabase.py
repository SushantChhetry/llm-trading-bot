#!/usr/bin/env python3
"""
Setup script for Supabase integration
"""

import os
import sys
from pathlib import Path

def setup_supabase():
    """Setup Supabase configuration"""
    print("🚀 Setting up Supabase integration for Trading Bot")
    print()
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("📝 Creating .env file...")
        env_content = """# Trading Bot Environment Variables

# Supabase Configuration
SUPABASE_KEY=your_supabase_anon_key_here

# LLM Configuration
LLM_PROVIDER=deepseek
LLM_API_KEY=your_api_key_here
LLM_MODEL=deepseek-chat

# Trading Configuration
TRADING_MODE=paper
USE_TESTNET=true
EXCHANGE=bybit
SYMBOL=BTC/USDT
INITIAL_BALANCE=10000.0
MAX_POSITION_SIZE=0.1
STOP_LOSS_PERCENT=2.0
TAKE_PROFIT_PERCENT=3.0
RUN_INTERVAL_SECONDS=300

# Behavioral Simulation
MAX_ACTIVE_POSITIONS=6
MIN_CONFIDENCE_THRESHOLD=0.6
FEE_IMPACT_WARNING_THRESHOLD=20.0

# Logging
LOG_LEVEL=INFO
"""
        with open(env_file, 'w') as f:
            f.write(env_content)
        print("✅ Created .env file")
    else:
        print("✅ .env file already exists")
    
    print()
    print("📋 Next steps:")
    print("1. Get your Supabase project URL and anon key from https://supabase.com")
    print("2. Update the SUPABASE_KEY in .env file")
    print("3. Run the SQL schema in your Supabase SQL editor:")
    print("   - Go to your Supabase project dashboard")
    print("   - Navigate to SQL Editor")
    print("   - Copy and paste the contents of scripts/supabase_schema.sql")
    print("   - Run the SQL to create the tables")
    print()
    print("4. Start the API server with Supabase:")
    print("   python web-dashboard/api_server_supabase.py")
    print()
    print("5. Or start with Docker:")
    print("   docker-compose -f docker-compose.dev.yml up -d")
    print()
    print("🔗 Supabase Project URL: https://uedfxgpduaramoagiatz.supabase.co")
    print("📊 Database will be available at: postgresql://postgres:[password]@db.uedfxgpduaramoagiatz.supabase.co:5432/postgres")

if __name__ == "__main__":
    setup_supabase()
