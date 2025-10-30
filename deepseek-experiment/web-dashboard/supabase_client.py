"""
Supabase client for trading bot database operations
"""
import os
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
import json
from datetime import datetime
from pathlib import Path

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Load .env file
load_env_file()

class SupabaseService:
    def __init__(self):
        self.supabase_url = "https://uedfxgpduaramoagiatz.supabase.co"
        self.supabase_key = os.getenv("SUPABASE_KEY")
        
        if not self.supabase_key:
            raise ValueError("SUPABASE_KEY environment variable is required")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
    
    def get_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent trades from Supabase"""
        try:
            response = self.supabase.table("trades").select("*").order("timestamp", desc=True).limit(limit).execute()
            return response.data
        except Exception as e:
            print(f"Error fetching trades: {e}")
            return []
    
    def add_trade(self, trade_data: Dict[str, Any]) -> bool:
        """Add a new trade to Supabase"""
        try:
            response = self.supabase.table("trades").insert(trade_data).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"Error adding trade: {e}")
            return False
    
    def get_portfolio(self) -> Optional[Dict[str, Any]]:
        """Get latest portfolio snapshot from Supabase"""
        try:
            response = self.supabase.table("portfolio_snapshots").select("*").order("timestamp", desc=True).limit(1).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error fetching portfolio: {e}")
            return None
    
    def update_portfolio(self, portfolio_data: Dict[str, Any]) -> bool:
        """Update portfolio snapshot in Supabase"""
        try:
            response = self.supabase.table("portfolio_snapshots").insert(portfolio_data).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"Error updating portfolio: {e}")
            return False
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get active positions from Supabase"""
        try:
            response = self.supabase.table("positions").select("*").eq("is_active", True).execute()
            return response.data
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return []
    
    def update_position(self, position_data: Dict[str, Any]) -> bool:
        """Update or create position in Supabase"""
        try:
            # Check if position exists
            existing = self.supabase.table("positions").select("id").eq("symbol", position_data["symbol"]).eq("is_active", True).execute()
            
            if existing.data:
                # Update existing position
                response = self.supabase.table("positions").update(position_data).eq("id", existing.data[0]["id"]).execute()
            else:
                # Create new position
                response = self.supabase.table("positions").insert(position_data).execute()
            
            return len(response.data) > 0
        except Exception as e:
            print(f"Error updating position: {e}")
            return False
    
    def close_position(self, symbol: str) -> bool:
        """Close a position by setting is_active to False"""
        try:
            response = self.supabase.table("positions").update({"is_active": False, "closed_at": datetime.now().isoformat()}).eq("symbol", symbol).eq("is_active", True).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"Error closing position: {e}")
            return False
    
    def get_behavioral_metrics(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get behavioral metrics from Supabase"""
        try:
            response = self.supabase.table("behavioral_metrics").select("*").order("timestamp", desc=True).limit(limit).execute()
            return response.data
        except Exception as e:
            print(f"Error fetching behavioral metrics: {e}")
            return []
    
    def add_behavioral_metrics(self, metrics_data: Dict[str, Any]) -> bool:
        """Add behavioral metrics to Supabase"""
        try:
            response = self.supabase.table("behavioral_metrics").insert(metrics_data).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"Error adding behavioral metrics: {e}")
            return False
    
    def get_bot_config(self) -> Dict[str, str]:
        """Get bot configuration from Supabase"""
        try:
            response = self.supabase.table("bot_config").select("*").execute()
            return {item["key"]: item["value"] for item in response.data}
        except Exception as e:
            print(f"Error fetching bot config: {e}")
            return {}
    
    def update_bot_config(self, key: str, value: str) -> bool:
        """Update bot configuration in Supabase"""
        try:
            response = self.supabase.table("bot_config").upsert({"key": key, "value": value, "updated_at": datetime.now().isoformat()}).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"Error updating bot config: {e}")
            return False

# Global instance
supabase_service = None

def get_supabase_service() -> SupabaseService:
    """Get the global Supabase service instance"""
    global supabase_service
    if supabase_service is None:
        supabase_service = SupabaseService()
    return supabase_service
