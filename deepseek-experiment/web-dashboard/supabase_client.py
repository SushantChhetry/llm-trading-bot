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
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")

        # Strip quotes if present (Railway sometimes includes them)
        if self.supabase_url:
            self.supabase_url = self.supabase_url.strip('"\'')
        if self.supabase_key:
            self.supabase_key = self.supabase_key.strip('"\'')

        if not self.supabase_url:
            raise ValueError("SUPABASE_URL environment variable is required")
        if not self.supabase_key:
            raise ValueError("SUPABASE_KEY environment variable is required")

        try:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        except (TypeError, ImportError, ModuleNotFoundError) as e:
            error_msg = str(e)
            # Compatibility issues with supabase-py dependencies
            if "proxy" in error_msg.lower() or "websockets" in error_msg.lower() or "realtime" in error_msg.lower():
                raise ValueError(
                    f"Supabase client initialization failed due to dependency compatibility issue: {error_msg}\n"
                    "Please ensure you're using supabase-py >=2.9.0 with compatible dependencies:\n"
                    "  pip install --upgrade 'supabase>=2.9.0' 'websockets>=13.0'\n"
                    "Or check your Python version (Python 3.13 requires latest package versions)"
                ) from e
            raise

    def get_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent trades from Supabase"""
        try:
            response = self.supabase.table("trades").select("*").order("timestamp", desc=True).limit(limit).execute()
            if response.data:
                return response.data
            else:
                return []
        except Exception as e:
            print(f"Error fetching trades: {e}")
            raise  # Re-raise to see the actual error

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
            # Ensure fee_impact_pct has a value (database column is NOT NULL)
            insert_data = metrics_data.copy()
            if "fee_impact_pct" not in insert_data or insert_data.get("fee_impact_pct") is None:
                insert_data["fee_impact_pct"] = 0.0

            response = self.supabase.table("behavioral_metrics").insert(insert_data).execute()
            return len(response.data) > 0
        except Exception as e:
            print(f"Error adding behavioral metrics: {e}")
            return False

    def get_portfolio_snapshots(self, limit: int = 1000, order_by: str = "timestamp", desc: bool = True) -> List[Dict[str, Any]]:
        """Get portfolio snapshots history from Supabase"""
        try:
            query = self.supabase.table("portfolio_snapshots").select("*")
            if desc:
                query = query.order(order_by, desc=True)
            else:
                query = query.order(order_by, desc=False)
            response = query.limit(limit).execute()
            if response.data:
                # Reverse to get chronological order if desc was True
                return list(reversed(response.data)) if desc else response.data
            else:
                return []
        except Exception as e:
            print(f"Error fetching portfolio snapshots: {e}")
            return []

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

    def save_configuration(self, config_data: Dict[str, Any], name: str = None, description: str = None, created_by: str = "user") -> Optional[Dict[str, Any]]:
        """Save a new versioned configuration to Supabase"""
        try:
            # Get next version number - try RPC first, fallback to manual calculation
            next_version = 1
            try:
                response = self.supabase.rpc("get_next_config_version").execute()
                if response.data:
                    next_version = response.data
            except Exception:
                # RPC function may not exist or may fail, calculate manually
                pass
            
            # If RPC didn't return a valid version, calculate manually
            if not next_version or not isinstance(next_version, (int, list)):
                try:
                    max_version_resp = self.supabase.table("bot_configurations").select("version").order("version", desc=True).limit(1).execute()
                    if max_version_resp.data and len(max_version_resp.data) > 0:
                        next_version = max_version_resp.data[0]["version"] + 1
                    else:
                        next_version = 1
                except Exception:
                    # Fallback to version 1 if query fails
                    next_version = 1
            
            if isinstance(next_version, list) and len(next_version) > 0:
                next_version = next_version[0]
            elif not isinstance(next_version, int):
                next_version = 1

            # Prepare insert data
            insert_data = {
                "version": next_version,
                "name": name or f"Configuration v{next_version}",
                "description": description or "",
                "config_json": config_data,
                "is_active": False,  # New configs are not active by default
                "is_default": False,
                "created_by": created_by
            }

            response = self.supabase.table("bot_configurations").insert(insert_data).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error saving configuration: {e}")
            raise

    def get_active_configuration(self) -> Optional[Dict[str, Any]]:
        """Get the currently active configuration from Supabase"""
        try:
            response = self.supabase.table("bot_configurations").select("*").eq("is_active", True).limit(1).execute()
            if response.data and len(response.data) > 0:
                config = response.data[0]
                # Merge config_json into the main dict for easier access
                if "config_json" in config:
                    config.update(config["config_json"])
                return config
            return None
        except Exception as e:
            print(f"Error fetching active configuration: {e}")
            return None

    def get_configuration_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all configuration versions from Supabase, ordered by creation date"""
        try:
            response = self.supabase.table("bot_configurations").select("*").order("created_at", desc=True).limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching configuration history: {e}")
            return []

    def activate_configuration(self, version_id: int) -> bool:
        """Activate a specific configuration version by ID"""
        try:
            # First, deactivate all configurations
            self.supabase.table("bot_configurations").update({"is_active": False}).eq("is_active", True).execute()
            
            # Then activate the specified one
            response = self.supabase.table("bot_configurations").update({"is_active": True}).eq("id", version_id).execute()
            return response.data and len(response.data) > 0
        except Exception as e:
            print(f"Error activating configuration: {e}")
            return False

    def get_configuration_by_id(self, config_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific configuration by ID"""
        try:
            response = self.supabase.table("bot_configurations").select("*").eq("id", config_id).limit(1).execute()
            if response.data and len(response.data) > 0:
                config = response.data[0]
                # Merge config_json into the main dict for easier access
                if "config_json" in config:
                    config.update(config["config_json"])
                return config
            return None
        except Exception as e:
            print(f"Error fetching configuration by ID: {e}")
            return None

    def get_default_configuration(self) -> Optional[Dict[str, Any]]:
        """Get the default system configuration from Supabase"""
        try:
            response = self.supabase.table("bot_configurations").select("*").eq("is_default", True).limit(1).execute()
            if response.data and len(response.data) > 0:
                config = response.data[0]
                # Merge config_json into the main dict for easier access
                if "config_json" in config:
                    config.update(config["config_json"])
                return config
            return None
        except Exception as e:
            print(f"Error fetching default configuration: {e}")
            return None

    def reset_to_default(self) -> bool:
        """Reset to default configuration by activating the default config"""
        try:
            default_config = self.get_default_configuration()
            if default_config and "id" in default_config:
                return self.activate_configuration(default_config["id"])
            return False
        except Exception as e:
            print(f"Error resetting to default configuration: {e}")
            return False

# Global instance
supabase_service = None

def get_supabase_service() -> SupabaseService:
    """Get the global Supabase service instance"""
    global supabase_service
    if supabase_service is None:
        supabase_service = SupabaseService()
    return supabase_service
