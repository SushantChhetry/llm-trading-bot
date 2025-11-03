"""
Monitoring and observability utilities for the trading bot.

Provides metrics collection, health checks, and alerting capabilities.
"""

import asyncio
import logging
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """Represents a single metric measurement."""

    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class HealthCheck:
    """Represents a health check result."""

    name: str
    status: str  # "healthy", "unhealthy", "degraded"
    message: str
    timestamp: datetime
    response_time_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collects and stores system and application metrics."""

    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        self.metrics: deque = deque(maxlen=max_metrics)
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)

    def increment_counter(self, name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """Increment a counter metric."""
        self.counters[name] += value
        self._record_metric(name, self.counters[name], "counter", tags or {})

    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge metric value."""
        self.gauges[name] = value
        self._record_metric(name, value, "gauge", tags or {})

    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a histogram value."""
        self.histograms[name].append(value)
        # Keep only last 1000 values
        if len(self.histograms[name]) > 1000:
            self.histograms[name] = self.histograms[name][-1000:]
        self._record_metric(name, value, "histogram", tags or {})

    def _record_metric(self, name: str, value: float, metric_type: str, tags: Dict[str, str]):
        """Record a metric internally."""
        metric = Metric(name=name, value=value, timestamp=datetime.utcnow(), tags=tags)
        self.metrics.append(metric)

    def get_metrics(self, name: str = None, since: datetime = None) -> List[Metric]:
        """Get metrics filtered by name and time."""
        filtered = list(self.metrics)

        if name:
            filtered = [m for m in filtered if m.name == name]

        if since:
            filtered = [m for m in filtered if m.timestamp >= since]

        return filtered

    def get_counter_value(self, name: str) -> float:
        """Get current counter value."""
        return self.counters.get(name, 0.0)

    def get_gauge_value(self, name: str) -> float:
        """Get current gauge value."""
        return self.gauges.get(name, 0.0)

    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """Get histogram statistics."""
        values = self.histograms.get(name, [])
        if not values:
            return {"count": 0, "min": 0, "max": 0, "mean": 0, "p95": 0, "p99": 0}

        values.sort()
        count = len(values)
        min_val = values[0]
        max_val = values[-1]
        mean_val = sum(values) / count

        p95_idx = int(count * 0.95)
        p99_idx = int(count * 0.99)

        return {
            "count": count,
            "min": min_val,
            "max": max_val,
            "mean": mean_val,
            "p95": values[p95_idx] if p95_idx < count else max_val,
            "p99": values[p99_idx] if p99_idx < count else max_val,
        }


class HealthChecker:
    """Performs health checks on system components."""

    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.results: Dict[str, HealthCheck] = {}
        self.check_interval = 30  # seconds
        self.last_check = {}

    def register_check(self, name: str, check_func: Callable, interval: int = 30):
        """Register a health check function."""
        self.checks[name] = check_func
        self.last_check[name] = 0

    async def run_check(self, name: str) -> HealthCheck:
        """Run a specific health check."""
        if name not in self.checks:
            return HealthCheck(
                name=name, status="unhealthy", message="Check not registered", timestamp=datetime.utcnow()
            )

        start_time = time.time()
        try:
            result = await self.checks[name]()
            response_time = (time.time() - start_time) * 1000

            if isinstance(result, dict):
                status = result.get("status", "healthy")
                message = result.get("message", "OK")
                details = result.get("details", {})
            else:
                status = "healthy" if result else "unhealthy"
                message = "OK" if result else "Check failed"
                details = {}

            health_check = HealthCheck(
                name=name,
                status=status,
                message=message,
                timestamp=datetime.utcnow(),
                response_time_ms=response_time,
                details=details,
            )

            self.results[name] = health_check
            return health_check

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            health_check = HealthCheck(
                name=name,
                status="unhealthy",
                message=f"Check failed: {str(e)}",
                timestamp=datetime.utcnow(),
                response_time_ms=response_time,
            )
            self.results[name] = health_check
            return health_check

    async def run_all_checks(self) -> Dict[str, HealthCheck]:
        """Run all registered health checks."""
        tasks = []
        for name in self.checks:
            if time.time() - self.last_check.get(name, 0) >= self.check_interval:
                tasks.append(self.run_check(name))
                self.last_check[name] = time.time()

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Health check failed: {result}")

        return self.results

    def get_overall_health(self) -> str:
        """Get overall system health status."""
        if not self.results:
            return "unknown"

        statuses = [check.status for check in self.results.values()]

        if "unhealthy" in statuses:
            return "unhealthy"
        elif "degraded" in statuses:
            return "degraded"
        else:
            return "healthy"


class AlertManager:
    """Manages alerts and notifications."""

    def __init__(self):
        self.alerts: List[Dict[str, Any]] = []
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.notification_handlers: List[Callable] = []

    def add_alert_rule(self, name: str, condition: Callable, severity: str = "warning", cooldown: int = 300):
        """Add an alert rule."""
        self.alert_rules[name] = {
            "condition": condition,
            "severity": severity,
            "cooldown": cooldown,
            "last_triggered": 0,
        }

    def add_notification_handler(self, handler: Callable):
        """Add a notification handler."""
        self.notification_handlers.append(handler)

    async def check_alerts(self, metrics_collector: MetricsCollector):
        """Check all alert rules and trigger alerts if needed."""
        current_time = time.time()

        for name, rule in self.alert_rules.items():
            # Check cooldown
            if current_time - rule["last_triggered"] < rule["cooldown"]:
                continue

            try:
                if rule["condition"](metrics_collector):
                    await self._trigger_alert(name, rule["severity"], current_time)
                    rule["last_triggered"] = current_time
            except Exception as e:
                logger.error(f"Error checking alert rule {name}: {e}")

    async def _trigger_alert(self, name: str, severity: str, timestamp: float):
        """Trigger an alert."""
        alert = {
            "name": name,
            "severity": severity,
            "timestamp": datetime.fromtimestamp(timestamp),
            "message": f"Alert triggered: {name}",
        }

        self.alerts.append(alert)

        # Send notifications
        for handler in self.notification_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Error sending notification: {e}")

        logger.warning(f"Alert triggered: {name} ({severity})")


class SystemMonitor:
    """Monitors system resources and performance."""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.start_time = time.time()

    async def collect_system_metrics(self):
        """Collect system resource metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics.set_gauge("system.cpu.usage", cpu_percent, {"unit": "percent"})

            # Memory usage
            memory = psutil.virtual_memory()
            self.metrics.set_gauge("system.memory.usage", memory.percent, {"unit": "percent"})
            self.metrics.set_gauge("system.memory.available", memory.available, {"unit": "bytes"})
            self.metrics.set_gauge("system.memory.total", memory.total, {"unit": "bytes"})

            # Disk usage
            disk = psutil.disk_usage("/")
            self.metrics.set_gauge("system.disk.usage", disk.percent, {"unit": "percent"})
            self.metrics.set_gauge("system.disk.free", disk.free, {"unit": "bytes"})

            # Process info
            process = psutil.Process()
            self.metrics.set_gauge("process.memory.usage", process.memory_info().rss, {"unit": "bytes"})
            self.metrics.set_gauge("process.cpu.usage", process.cpu_percent(), {"unit": "percent"})

            # Uptime
            uptime = time.time() - self.start_time
            self.metrics.set_gauge("system.uptime", uptime, {"unit": "seconds"})

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")


class TradingMetrics:
    """Collects trading-specific metrics."""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector

    def record_trade(self, trade_data: Dict[str, Any]):
        """Record trade metrics."""
        self.metrics.increment_counter("trades.total")
        self.metrics.increment_counter(f"trades.{trade_data.get('side', 'unknown')}")

        if trade_data.get("profit"):
            profit = trade_data["profit"]
            self.metrics.record_histogram("trades.profit", profit)
            self.metrics.increment_counter("trades.profit_total", profit)

        if trade_data.get("confidence"):
            confidence = trade_data["confidence"]
            self.metrics.record_histogram("trades.confidence", confidence)

        if trade_data.get("leverage"):
            leverage = trade_data["leverage"]
            self.metrics.record_histogram("trades.leverage", leverage)

    def record_portfolio_value(self, value: float):
        """Record portfolio value."""
        self.metrics.set_gauge("portfolio.value", value, {"unit": "usdt"})

    def record_position_count(self, count: int):
        """Record active position count."""
        self.metrics.set_gauge("portfolio.positions", count)

    def record_api_call(self, provider: str, success: bool, response_time: float):
        """Record API call metrics."""
        self.metrics.increment_counter(f"api.calls.{provider}")
        if success:
            self.metrics.increment_counter(f"api.success.{provider}")
        else:
            self.metrics.increment_counter(f"api.errors.{provider}")

        self.metrics.record_histogram(f"api.response_time.{provider}", response_time)


class MonitoringService:
    """Main monitoring service that coordinates all monitoring components."""

    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.health_checker = HealthChecker()
        self.alert_manager = AlertManager()
        self.system_monitor = SystemMonitor(self.metrics_collector)
        self.trading_metrics = TradingMetrics(self.metrics_collector)

        # Register default health checks
        self._register_default_health_checks()

        # Register default alert rules
        self._register_default_alert_rules()

        self.running = False
        self.monitoring_task = None

    def _register_default_health_checks(self):
        """Register default health checks."""

        async def check_database():
            # This would check database connectivity
            return {"status": "healthy", "message": "Database OK"}

        async def check_llm_api():
            # This would check LLM API connectivity
            return {"status": "healthy", "message": "LLM API OK"}

        async def check_exchange_api():
            # This would check exchange API connectivity
            return {"status": "healthy", "message": "Exchange API OK"}

        self.health_checker.register_check("database", check_database)
        self.health_checker.register_check("llm_api", check_llm_api)
        self.health_checker.register_check("exchange_api", check_exchange_api)

    def _register_default_alert_rules(self):
        """Register default alert rules."""

        def high_cpu_usage(metrics):
            return metrics.get_gauge_value("system.cpu.usage") > 80

        def high_memory_usage(metrics):
            return metrics.get_gauge_value("system.memory.usage") > 85

        def low_portfolio_value(metrics):
            return metrics.get_gauge_value("portfolio.value") < 5000

        def high_error_rate(metrics):
            total_calls = metrics.get_counter_value("api.calls.deepseek")
            errors = metrics.get_counter_value("api.errors.deepseek")
            return total_calls > 0 and (errors / total_calls) > 0.1

        self.alert_manager.add_alert_rule("high_cpu", high_cpu_usage, "warning")
        self.alert_manager.add_alert_rule("high_memory", high_memory_usage, "warning")
        self.alert_manager.add_alert_rule("low_portfolio", low_portfolio_value, "critical")
        self.alert_manager.add_alert_rule("high_error_rate", high_error_rate, "warning")

    async def start(self):
        """Start the monitoring service."""
        if self.running:
            return

        self.running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Monitoring service started")

    async def stop(self):
        """Stop the monitoring service."""
        self.running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Monitoring service stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                # Collect system metrics
                await self.system_monitor.collect_system_metrics()

                # Run health checks
                await self.health_checker.run_all_checks()

                # Check alerts
                await self.alert_manager.check_alerts(self.metrics_collector)

                # Wait before next iteration
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current metrics."""
        return {
            "counters": dict(self.metrics_collector.counters),
            "gauges": dict(self.metrics_collector.gauges),
            "histogram_stats": {
                name: self.metrics_collector.get_histogram_stats(name) for name in self.metrics_collector.histograms
            },
            "health_status": self.health_checker.get_overall_health(),
            "recent_alerts": self.alert_manager.alerts[-10:],  # Last 10 alerts
        }

    def export_metrics(self, file_path: Path):
        """Export metrics to file."""
        summary = self.get_metrics_summary()
        with open(file_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)


# Global monitoring service instance
monitoring_service = MonitoringService()
