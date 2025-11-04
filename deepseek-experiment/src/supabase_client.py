"""
Supabase client for trading bot database operations
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from supabase import Client, create_client

logger = logging.getLogger(__name__)


# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value


# Load .env file
load_env_file()


class SupabaseService:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")  # Anon key (for reads)
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")  # Service role key (for writes)
        
        # Track if observability tables exist to avoid repeated error messages
        self._observability_metrics_table_exists = True
        self._service_health_table_exists = True
        self._observability_error_logged = False
        self._health_check_error_logged = False

        if not self.supabase_url:
            raise ValueError("SUPABASE_URL environment variable is required")
        
        # Use service key if available (for writes), fall back to anon key (for reads only)
        # Service role key bypasses RLS, anon key is subject to RLS policies
        key_to_use = self.supabase_service_key or self.supabase_key
        
        if not key_to_use:
            raise ValueError("SUPABASE_KEY or SUPABASE_SERVICE_KEY environment variable is required")
        
        # Warn if using anon key for writes (will fail with proper RLS)
        if not self.supabase_service_key and self.supabase_key:
            import warnings
            warnings.warn(
                "⚠️  Using SUPABASE_KEY (anon key) for all operations. "
                "Set SUPABASE_SERVICE_KEY for write operations to work with RLS policies. "
                "Write operations may fail once database RLS is properly configured.",
                UserWarning
            )

        try:
            self.supabase: Client = create_client(self.supabase_url, key_to_use)
        except TypeError as e:
            error_msg = str(e)
            if "proxy" in error_msg.lower():
                # Compatibility issue: supabase-py version mismatch with gotrue/httpx
                raise ValueError(
                    f"Supabase client initialization failed due to version compatibility issue: {error_msg}\n"
                    "Please upgrade supabase-py to version >=2.9.0:\n"
                    "  pip install --upgrade 'supabase>=2.9.0'\n"
                    "Or install compatible versions:\n"
                    "  pip install 'supabase==2.8.1' 'gotrue==2.8.1' 'httpx==0.24.1'"
                ) from e
            raise

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
            response = (
                self.supabase.table("portfolio_snapshots").select("*").order("timestamp", desc=True).limit(1).execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error fetching portfolio: {e}")
            return None

    def update_portfolio(self, portfolio_data: Dict[str, Any]) -> bool:
        """Update portfolio snapshot in Supabase"""
        try:
            # Filter out None values to avoid schema issues
            filtered_data = {k: v for k, v in portfolio_data.items() if v is not None}
            response = self.supabase.table("portfolio_snapshots").insert(filtered_data).execute()
            return len(response.data) > 0
        except Exception as e:
            error_msg = str(e)
            # Check if it's a schema error (missing column)
            if "PGRST204" in error_msg or "column" in error_msg.lower() and "schema cache" in error_msg.lower():
                print(f"Error updating portfolio - missing column in database schema: {e}")
                print("💡 Run the migration script: scripts/add_missing_columns.sql in your Supabase SQL Editor")
            else:
                print(f"Error updating portfolio: {e}")
            return False

    def get_portfolio_snapshots(self, limit: int = 1000, order_by: str = "timestamp", desc: bool = True) -> List[Dict[str, Any]]:
        """Get portfolio snapshots from Supabase"""
        try:
            query = self.supabase.table("portfolio_snapshots").select("*")
            if desc:
                query = query.order(order_by, desc=True)
            else:
                query = query.order(order_by, desc=False)
            response = query.limit(limit).execute()
            return response.data
        except Exception as e:
            print(f"Error fetching portfolio snapshots: {e}")
            return []

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
            existing = (
                self.supabase.table("positions")
                .select("id")
                .eq("symbol", position_data["symbol"])
                .eq("is_active", True)
                .execute()
            )

            if existing.data:
                # Update existing position
                response = (
                    self.supabase.table("positions").update(position_data).eq("id", existing.data[0]["id"]).execute()
                )
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
            response = (
                self.supabase.table("positions")
                .update({"is_active": False, "closed_at": datetime.now().isoformat()})
                .eq("symbol", symbol)
                .eq("is_active", True)
                .execute()
            )
            return len(response.data) > 0
        except Exception as e:
            print(f"Error closing position: {e}")
            return False

    def get_behavioral_metrics(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get behavioral metrics from Supabase"""
        try:
            response = (
                self.supabase.table("behavioral_metrics")
                .select("*")
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
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
            response = (
                self.supabase.table("bot_config")
                .upsert({"key": key, "value": value, "updated_at": datetime.now().isoformat()})
                .execute()
            )
            return len(response.data) > 0
        except Exception as e:
            print(f"Error updating bot config: {e}")
            return False

    def add_metric(
        self,
        service_name: str,
        metric_name: str,
        value: float,
        metric_type: str = "gauge",
        tags: Optional[Dict[str, Any]] = None,
        unit: str = "",
    ) -> bool:
        """Add a metric to observability_metrics table"""
        # Skip if we know the table doesn't exist
        if not self._observability_metrics_table_exists:
            return False
            
        try:
            metric_data = {
                "timestamp": datetime.now().isoformat(),
                "service_name": service_name,
                "metric_name": metric_name,
                "value": float(value),
                "metric_type": metric_type,
                "tags": tags or {},
                "unit": unit,
            }
            response = self.supabase.table("observability_metrics").insert(metric_data).execute()
            return len(response.data) > 0
        except Exception as e:
            error_str = str(e)
            # Check if it's the "table not found" error (PGRST205)
            if "PGRST205" in error_str or ("schema cache" in error_str.lower() and "observability_metrics" in error_str.lower()):
                self._observability_metrics_table_exists = False
                if not self._observability_error_logged:
                    logger.warning(
                        "observability_metrics table not found in Supabase. "
                        "Metrics will not be saved. To enable metrics, run the schema migration: "
                        "scripts/supabase_schema.sql in your Supabase SQL Editor."
                    )
                    self._observability_error_logged = True
            else:
                # Log other errors at debug level to reduce noise
                logger.debug(f"Error adding metric: {e}")
            return False

    def add_health_check(
        self, service_name: str, status: str, details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add a health check snapshot to service_health table"""
        # Skip if we know the table doesn't exist
        if not self._service_health_table_exists:
            return False
            
        try:
            if status not in ["healthy", "degraded", "unhealthy"]:
                raise ValueError(f"Invalid status: {status}. Must be 'healthy', 'degraded', or 'unhealthy'")

            health_data = {
                "timestamp": datetime.now().isoformat(),
                "service_name": service_name,
                "status": status,
                "details": details or {},
            }
            response = self.supabase.table("service_health").insert(health_data).execute()
            return len(response.data) > 0
        except Exception as e:
            error_str = str(e)
            # Check if it's the "table not found" error (PGRST205)
            if "PGRST205" in error_str or ("schema cache" in error_str.lower() and "service_health" in error_str.lower()):
                self._service_health_table_exists = False
                if not self._health_check_error_logged:
                    logger.warning(
                        "service_health table not found in Supabase. "
                        "Health checks will not be saved. To enable health checks, run the schema migration: "
                        "scripts/supabase_schema.sql in your Supabase SQL Editor."
                    )
                    self._health_check_error_logged = True
            else:
                # Log other errors at debug level to reduce noise
                logger.debug(f"Error adding health check: {e}")
            return False

    def get_metrics(
        self,
        service_name: Optional[str] = None,
        metric_name: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Get metrics from observability_metrics table"""
        try:
            query = self.supabase.table("observability_metrics").select("*")

            if service_name:
                query = query.eq("service_name", service_name)

            if metric_name:
                query = query.eq("metric_name", metric_name)

            if since:
                query = query.gte("timestamp", since.isoformat())

            response = query.order("timestamp", desc=True).limit(limit).execute()
            return response.data
        except Exception as e:
            print(f"Error fetching metrics: {e}")
            return []

    def get_latest_health(self, service_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the latest health check for a service (or all services)"""
        try:
            query = self.supabase.table("service_health").select("*")

            if service_name:
                query = query.eq("service_name", service_name)

            response = query.order("timestamp", desc=True).limit(1).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error fetching latest health: {e}")
            return None


# Global instance
supabase_service = None


def get_supabase_service() -> SupabaseService:
    """Get the global Supabase service instance"""
    global supabase_service
    if supabase_service is None:
        supabase_service = SupabaseService()
    return supabase_service
