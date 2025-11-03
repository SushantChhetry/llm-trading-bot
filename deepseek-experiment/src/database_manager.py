"""
Database manager for the trading bot.

Provides unified data persistence with transaction management and data validation.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from contextlib import asynccontextmanager
import asyncpg
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid

from .resilience import database_retry_handler, circuit_breaker, CircuitBreakerConfig

logger = logging.getLogger(__name__)

# SQLAlchemy base
Base = declarative_base()


class Trade(Base):
    """Trade model for database storage."""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)
    trade_id = Column(String(50), unique=True, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # buy, sell, short
    direction = Column(String(10), nullable=False)  # long, short, none
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    amount_usdt = Column(Float, nullable=False)
    leverage = Column(Float, default=1.0)
    margin_used = Column(Float, default=0.0)
    margin_returned = Column(Float, default=0.0)
    trading_fee = Column(Float, default=0.0)
    profit = Column(Float, default=0.0)
    profit_pct = Column(Float, default=0.0)
    confidence = Column(Float, nullable=False)
    mode = Column(String(20), default="paper")
    llm_justification = Column(Text)
    llm_risk_assessment = Column(String(20))
    llm_position_size_usdt = Column(Float, default=0.0)
    exit_plan = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class Position(Base):
    """Position model for database storage."""

    __tablename__ = "positions"

    id = Column(Integer, primary_key=True)
    position_id = Column(String(50), unique=True, nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # long, short
    quantity = Column(Float, nullable=False)
    avg_price = Column(Float, nullable=False)
    current_price = Column(Float)
    value = Column(Float, nullable=False)
    leverage = Column(Float, default=1.0)
    margin_used = Column(Float, default=0.0)
    notional_value = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PortfolioSnapshot(Base):
    """Portfolio snapshot model for database storage."""

    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True)
    snapshot_id = Column(String(50), unique=True, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    balance = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)
    positions_value = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    total_fees = Column(Float, default=0.0)
    active_positions = Column(Integer, default=0)
    total_trades = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class BehavioralMetrics(Base):
    """Behavioral metrics model for database storage."""

    __tablename__ = "behavioral_metrics"

    id = Column(Integer, primary_key=True)
    metrics_id = Column(String(50), unique=True, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    bullish_tilt = Column(Float, nullable=False)
    avg_holding_period_hours = Column(Float, nullable=False)
    trade_frequency_per_day = Column(Float, nullable=False)
    avg_position_size_usdt = Column(Float, nullable=False)
    avg_confidence = Column(Float, nullable=False)
    exit_plan_tightness = Column(Float, nullable=False)
    active_positions_count = Column(Integer, nullable=False)
    total_trading_fees = Column(Float, nullable=False)
    fee_impact_pct = Column(Float, nullable=False)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    volatility = Column(Float)
    win_rate = Column(Float)
    profit_factor = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class DatabaseManager:
    """Manages database operations with transaction support and resilience."""

    def __init__(self, database_url: str, fallback_to_json: bool = True):
        """
        Initialize database manager.

        Args:
            database_url: Database connection URL
            fallback_to_json: Whether to fallback to JSON files if database fails
        """
        self.database_url = database_url
        self.fallback_to_json = fallback_to_json
        self.engine = None
        self.session_factory = None
        self.is_connected = False

        # Fallback JSON file paths
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self.trades_file = self.data_dir / "trades.json"
        self.positions_file = self.data_dir / "positions.json"
        self.portfolio_file = self.data_dir / "portfolio.json"
        self.metrics_file = self.data_dir / "behavioral_metrics.json"

        # Initialize connection
        asyncio.create_task(self._initialize_connection())

    async def _initialize_connection(self):
        """Initialize database connection."""
        try:
            self.engine = create_async_engine(
                self.database_url, echo=False, pool_size=10, max_overflow=20, pool_pre_ping=True
            )

            self.session_factory = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            self.is_connected = True
            logger.info("Database connection established successfully")

        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            if self.fallback_to_json:
                logger.info("Falling back to JSON file storage")
                self.is_connected = False
            else:
                raise

    @asynccontextmanager
    async def get_session(self):
        """Get database session with automatic cleanup."""
        if not self.is_connected:
            raise Exception("Database not connected")

        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    @circuit_breaker(CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60))
    async def save_trade(self, trade_data: Dict[str, Any]) -> str:
        """
        Save trade to database.

        Args:
            trade_data: Trade data dictionary

        Returns:
            Trade ID
        """
        if not self.is_connected:
            return await self._save_trade_json(trade_data)

        trade_id = str(uuid.uuid4())

        trade = Trade(
            trade_id=trade_id,
            timestamp=datetime.fromisoformat(trade_data.get("timestamp", datetime.utcnow().isoformat())),
            symbol=trade_data.get("symbol", ""),
            side=trade_data.get("side", ""),
            direction=trade_data.get("direction", ""),
            price=float(trade_data.get("price", 0)),
            quantity=float(trade_data.get("quantity", 0)),
            amount_usdt=float(trade_data.get("amount_usdt", 0)),
            leverage=float(trade_data.get("leverage", 1.0)),
            margin_used=float(trade_data.get("margin_used", 0)),
            margin_returned=float(trade_data.get("margin_returned", 0)),
            trading_fee=float(trade_data.get("trading_fee", 0)),
            profit=float(trade_data.get("profit", 0)),
            profit_pct=float(trade_data.get("profit_pct", 0)),
            confidence=float(trade_data.get("confidence", 0)),
            mode=trade_data.get("mode", "paper"),
            llm_justification=trade_data.get("llm_justification", ""),
            llm_risk_assessment=trade_data.get("llm_risk_assessment", ""),
            llm_position_size_usdt=float(trade_data.get("llm_position_size_usdt", 0)),
            exit_plan=trade_data.get("exit_plan", {}),
        )

        async with self.get_session() as session:
            session.add(trade)
            await session.flush()
            await session.refresh(trade)

        logger.info(f"Trade saved to database: {trade_id}")
        return trade_id

    async def _save_trade_json(self, trade_data: Dict[str, Any]) -> str:
        """Fallback: Save trade to JSON file."""
        trade_id = str(uuid.uuid4())
        trade_data["id"] = trade_id
        trade_data["trade_id"] = trade_id

        try:
            trades = []
            if self.trades_file.exists():
                with open(self.trades_file, "r") as f:
                    trades = json.load(f)

            trades.append(trade_data)

            with open(self.trades_file, "w") as f:
                json.dump(trades, f, indent=2, default=str)

            logger.info(f"Trade saved to JSON: {trade_id}")
            return trade_id

        except Exception as e:
            logger.error(f"Failed to save trade to JSON: {e}")
            raise

    @circuit_breaker(CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60))
    async def save_position(self, position_data: Dict[str, Any]) -> str:
        """Save position to database."""
        if not self.is_connected:
            return await self._save_position_json(position_data)

        position_id = str(uuid.uuid4())

        position = Position(
            position_id=position_id,
            symbol=position_data.get("symbol", ""),
            side=position_data.get("side", ""),
            quantity=float(position_data.get("quantity", 0)),
            avg_price=float(position_data.get("avg_price", 0)),
            current_price=float(position_data.get("current_price", 0)),
            value=float(position_data.get("value", 0)),
            leverage=float(position_data.get("leverage", 1.0)),
            margin_used=float(position_data.get("margin_used", 0)),
            notional_value=float(position_data.get("notional_value", 0)),
            unrealized_pnl=float(position_data.get("unrealized_pnl", 0)),
            is_active=position_data.get("is_active", True),
            opened_at=datetime.fromisoformat(position_data.get("opened_at", datetime.utcnow().isoformat())),
        )

        async with self.get_session() as session:
            session.add(position)
            await session.flush()
            await session.refresh(position)

        logger.info(f"Position saved to database: {position_id}")
        return position_id

    async def _save_position_json(self, position_data: Dict[str, Any]) -> str:
        """Fallback: Save position to JSON file."""
        position_id = str(uuid.uuid4())
        position_data["id"] = position_id
        position_data["position_id"] = position_id

        try:
            positions = {}
            if self.positions_file.exists():
                with open(self.positions_file, "r") as f:
                    positions = json.load(f)

            symbol = position_data.get("symbol", "UNKNOWN")
            positions[symbol] = position_data

            with open(self.positions_file, "w") as f:
                json.dump(positions, f, indent=2, default=str)

            logger.info(f"Position saved to JSON: {position_id}")
            return position_id

        except Exception as e:
            logger.error(f"Failed to save position to JSON: {e}")
            raise

    @circuit_breaker(CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60))
    async def save_portfolio_snapshot(self, portfolio_data: Dict[str, Any]) -> str:
        """Save portfolio snapshot to database."""
        if not self.is_connected:
            return await self._save_portfolio_json(portfolio_data)

        snapshot_id = str(uuid.uuid4())

        snapshot = PortfolioSnapshot(
            snapshot_id=snapshot_id,
            timestamp=datetime.fromisoformat(portfolio_data.get("timestamp", datetime.utcnow().isoformat())),
            balance=float(portfolio_data.get("balance", 0)),
            total_value=float(portfolio_data.get("total_value", 0)),
            positions_value=float(portfolio_data.get("positions_value", 0)),
            unrealized_pnl=float(portfolio_data.get("unrealized_pnl", 0)),
            realized_pnl=float(portfolio_data.get("realized_pnl", 0)),
            total_fees=float(portfolio_data.get("total_fees", 0)),
            active_positions=int(portfolio_data.get("active_positions", 0)),
            total_trades=int(portfolio_data.get("total_trades", 0)),
        )

        async with self.get_session() as session:
            session.add(snapshot)
            await session.flush()
            await session.refresh(snapshot)

        logger.info(f"Portfolio snapshot saved to database: {snapshot_id}")
        return snapshot_id

    async def _save_portfolio_json(self, portfolio_data: Dict[str, Any]) -> str:
        """Fallback: Save portfolio to JSON file."""
        snapshot_id = str(uuid.uuid4())
        portfolio_data["id"] = snapshot_id
        portfolio_data["snapshot_id"] = snapshot_id

        try:
            with open(self.portfolio_file, "w") as f:
                json.dump(portfolio_data, f, indent=2, default=str)

            logger.info(f"Portfolio snapshot saved to JSON: {snapshot_id}")
            return snapshot_id

        except Exception as e:
            logger.error(f"Failed to save portfolio to JSON: {e}")
            raise

    @circuit_breaker(CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60))
    async def save_behavioral_metrics(self, metrics_data: Dict[str, Any]) -> str:
        """Save behavioral metrics to database."""
        if not self.is_connected:
            return await self._save_metrics_json(metrics_data)

        metrics_id = str(uuid.uuid4())

        metrics = BehavioralMetrics(
            metrics_id=metrics_id,
            timestamp=datetime.fromisoformat(metrics_data.get("timestamp", datetime.utcnow().isoformat())),
            bullish_tilt=float(metrics_data.get("bullish_tilt", 0)),
            avg_holding_period_hours=float(metrics_data.get("avg_holding_period_hours", 0)),
            trade_frequency_per_day=float(metrics_data.get("trade_frequency_per_day", 0)),
            avg_position_size_usdt=float(metrics_data.get("avg_position_size_usdt", 0)),
            avg_confidence=float(metrics_data.get("avg_confidence", 0)),
            exit_plan_tightness=float(metrics_data.get("exit_plan_tightness", 0)),
            active_positions_count=int(metrics_data.get("active_positions_count", 0)),
            total_trading_fees=float(metrics_data.get("total_trading_fees", 0)),
            fee_impact_pct=float(metrics_data.get("fee_impact_pct", 0)),
            sharpe_ratio=float(metrics_data.get("sharpe_ratio", 0)) if metrics_data.get("sharpe_ratio") else None,
            max_drawdown=float(metrics_data.get("max_drawdown", 0)) if metrics_data.get("max_drawdown") else None,
            volatility=float(metrics_data.get("volatility", 0)) if metrics_data.get("volatility") else None,
            win_rate=float(metrics_data.get("win_rate", 0)) if metrics_data.get("win_rate") else None,
            profit_factor=float(metrics_data.get("profit_factor", 0)) if metrics_data.get("profit_factor") else None,
        )

        async with self.get_session() as session:
            session.add(metrics)
            await session.flush()
            await session.refresh(metrics)

        logger.info(f"Behavioral metrics saved to database: {metrics_id}")
        return metrics_id

    async def _save_metrics_json(self, metrics_data: Dict[str, Any]) -> str:
        """Fallback: Save metrics to JSON file."""
        metrics_id = str(uuid.uuid4())
        metrics_data["id"] = metrics_id
        metrics_data["metrics_id"] = metrics_id

        try:
            metrics_list = []
            if self.metrics_file.exists():
                with open(self.metrics_file, "r") as f:
                    metrics_list = json.load(f)

            metrics_list.append(metrics_data)

            with open(self.metrics_file, "w") as f:
                json.dump(metrics_list, f, indent=2, default=str)

            logger.info(f"Behavioral metrics saved to JSON: {metrics_id}")
            return metrics_id

        except Exception as e:
            logger.error(f"Failed to save metrics to JSON: {e}")
            raise

    async def get_recent_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent trades from database."""
        if not self.is_connected:
            return await self._get_trades_json(limit)

        async with self.get_session() as session:
            result = await session.execute(sa.select(Trade).order_by(Trade.timestamp.desc()).limit(limit))
            trades = result.scalars().all()

            return [
                {
                    "id": trade.id,
                    "trade_id": trade.trade_id,
                    "timestamp": trade.timestamp.isoformat(),
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "direction": trade.direction,
                    "price": trade.price,
                    "quantity": trade.quantity,
                    "amount_usdt": trade.amount_usdt,
                    "leverage": trade.leverage,
                    "margin_used": trade.margin_used,
                    "margin_returned": trade.margin_returned,
                    "trading_fee": trade.trading_fee,
                    "profit": trade.profit,
                    "profit_pct": trade.profit_pct,
                    "confidence": trade.confidence,
                    "mode": trade.mode,
                    "llm_justification": trade.llm_justification,
                    "llm_risk_assessment": trade.llm_risk_assessment,
                    "llm_position_size_usdt": trade.llm_position_size_usdt,
                    "exit_plan": trade.exit_plan,
                }
                for trade in trades
            ]

    async def _get_trades_json(self, limit: int) -> List[Dict[str, Any]]:
        """Fallback: Get trades from JSON file."""
        try:
            if not self.trades_file.exists():
                return []

            with open(self.trades_file, "r") as f:
                trades = json.load(f)

            return trades[-limit:] if len(trades) > limit else trades

        except Exception as e:
            logger.error(f"Failed to load trades from JSON: {e}")
            return []

    async def get_active_positions(self) -> Dict[str, Dict[str, Any]]:
        """Get active positions from database."""
        if not self.is_connected:
            return await self._get_positions_json()

        async with self.get_session() as session:
            result = await session.execute(sa.select(Position).where(Position.is_active == True))
            positions = result.scalars().all()

            return {
                pos.symbol: {
                    "id": pos.id,
                    "position_id": pos.position_id,
                    "symbol": pos.symbol,
                    "side": pos.side,
                    "quantity": pos.quantity,
                    "avg_price": pos.avg_price,
                    "current_price": pos.current_price,
                    "value": pos.value,
                    "leverage": pos.leverage,
                    "margin_used": pos.margin_used,
                    "notional_value": pos.notional_value,
                    "unrealized_pnl": pos.unrealized_pnl,
                    "is_active": pos.is_active,
                    "opened_at": pos.opened_at.isoformat() if pos.opened_at else None,
                    "closed_at": pos.closed_at.isoformat() if pos.closed_at else None,
                }
                for pos in positions
            }

    async def _get_positions_json(self) -> Dict[str, Dict[str, Any]]:
        """Fallback: Get positions from JSON file."""
        try:
            if not self.positions_file.exists():
                return {}

            with open(self.positions_file, "r") as f:
                return json.load(f)

        except Exception as e:
            logger.error(f"Failed to load positions from JSON: {e}")
            return {}

    async def close(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")


# Global database manager instance
database_manager = None


async def get_database_manager() -> DatabaseManager:
    """Get global database manager instance."""
    global database_manager
    if database_manager is None:
        from .config_manager import config_manager

        database_url = config_manager.database.url
        database_manager = DatabaseManager(database_url)
    return database_manager
