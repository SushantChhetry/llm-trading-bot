"""
Tests for kill switch functionality.

Tests that kill switch activation prevents trade execution and that
all kill switch trigger conditions work correctly.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import time
import requests

from services.risk_service import RiskService, RiskStatus, KillSwitchThresholds, RiskLimits
from src.risk_client import RiskClient, OrderValidationResult


class TestKillSwitch(unittest.TestCase):
    """Test kill switch functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.risk_service = RiskService()
        self.risk_client = RiskClient(risk_service_url="http://localhost:8003")
    
    def test_kill_switch_activation(self):
        """Test that kill switch can be activated."""
        # Activate kill switch
        self.risk_service.activate_kill_switch("Test activation")
        
        # Verify kill switch is active
        self.assertTrue(self.risk_service.kill_switch_active)
        self.assertEqual(self.risk_service.kill_switch_reason, "Test activation")
        
        # Verify risk state reflects kill switch
        risk_state = self.risk_service.get_risk_state()
        self.assertTrue(risk_state["kill_switch_active"])
        self.assertEqual(risk_state["kill_switch_reason"], "Test activation")
    
    def test_kill_switch_prevents_trade(self):
        """Test that kill switch prevents trade execution."""
        # Activate kill switch
        self.risk_service.activate_kill_switch("Test prevention")
        
        # Try to validate an order
        from services.risk_service import OrderRequest
        order = OrderRequest(
            strategy_id="test",
            symbol="BTC/USDT",
            side="buy",
            quantity=0.1,
            price=50000.0,
            leverage=1.0,
            current_nav=10000.0,
            position_value=5000.0,
            timestamp=time.time()
        )
        
        status, reason, details = self.risk_service.validate_order(order)
        
        # Should be rejected due to kill switch
        self.assertEqual(status, RiskStatus.KILL_SWITCH)
        self.assertIn("kill switch", reason.lower())
        self.assertTrue(details.get("kill_switch", False))
    
    def test_kill_switch_deactivation(self):
        """Test that kill switch can be deactivated."""
        # Activate kill switch
        self.risk_service.activate_kill_switch("Test")
        self.assertTrue(self.risk_service.kill_switch_active)
        
        # Deactivate kill switch
        self.risk_service.deactivate_kill_switch()
        
        # Verify kill switch is inactive
        self.assertFalse(self.risk_service.kill_switch_active)
        self.assertIsNone(self.risk_service.kill_switch_reason)
        
        # Verify risk state reflects deactivation
        risk_state = self.risk_service.get_risk_state()
        self.assertFalse(risk_state["kill_switch_active"])
        self.assertIsNone(risk_state["kill_switch_reason"])
    
    def test_exchange_outage_trigger(self):
        """Test that exchange outage triggers kill switch."""
        # Simulate exchange outage (no data for >30s)
        self.risk_service.risk_state.last_data_update = time.time() - 35.0
        
        # Check kill switches
        triggered = self.risk_service.check_kill_switches({})
        
        # Should trigger kill switch
        self.assertTrue(triggered)
        self.assertTrue(self.risk_service.kill_switch_active)
        self.assertIn("outage", self.risk_service.kill_switch_reason.lower())
    
    def test_funding_rate_spike_trigger(self):
        """Test that funding rate spike triggers kill switch."""
        # Set funding rate spike (>500 bps = 0.05)
        self.risk_service.risk_state.funding_rate = 0.06  # 600 bps
        
        # Check kill switches
        triggered = self.risk_service.check_kill_switches({})
        
        # Should trigger kill switch
        self.assertTrue(triggered)
        self.assertTrue(self.risk_service.kill_switch_active)
        self.assertIn("funding", self.risk_service.kill_switch_reason.lower())
    
    def test_api_latency_spike_trigger(self):
        """Test that API latency spike triggers kill switch."""
        # Set API latency spike (>100ms p99)
        self.risk_service.risk_state.api_latency_p99 = 150.0
        
        # Check kill switches
        triggered = self.risk_service.check_kill_switches({})
        
        # Should trigger kill switch
        self.assertTrue(triggered)
        self.assertTrue(self.risk_service.kill_switch_active)
        self.assertIn("latency", self.risk_service.kill_switch_reason.lower())
    
    def test_price_divergence_trigger(self):
        """Test that price divergence triggers kill switch."""
        # Set price divergence (>50 bps)
        self.risk_service.risk_state.price_divergence_bps = 60.0
        
        # Check kill switches
        triggered = self.risk_service.check_kill_switches({})
        
        # Should trigger kill switch
        self.assertTrue(triggered)
        self.assertTrue(self.risk_service.kill_switch_active)
        self.assertIn("divergence", self.risk_service.kill_switch_reason.lower())
    
    def test_equity_drop_trigger(self):
        """Test that equity drop triggers kill switch."""
        # Set equity drop (>5% in single bar)
        market_data = {"equity_drop_pct": 0.06}  # 6% drop
        
        # Check kill switches
        triggered = self.risk_service.check_kill_switches(market_data)
        
        # Should trigger kill switch
        self.assertTrue(triggered)
        self.assertTrue(self.risk_service.kill_switch_active)
        self.assertIn("equity", self.risk_service.kill_switch_reason.lower())
    
    @patch('src.risk_client.requests.Session.post')
    def test_risk_client_kill_switch_rejection(self, mock_post):
        """Test that risk client rejects orders when kill switch is active."""
        # Mock risk service response with kill switch
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "kill_switch",
            "approved": False,
            "reason": "Kill switch active",
            "details": {"kill_switch": True}
        }
        mock_post.return_value = mock_response
        
        # Try to validate order
        result = self.risk_client.validate_order(
            strategy_id="test",
            symbol="BTC/USDT",
            side="buy",
            quantity=0.1,
            price=50000.0,
            leverage=1.0,
            current_nav=10000.0,
            position_value=5000.0
        )
        
        # Should be rejected
        self.assertFalse(result.approved)
        self.assertEqual(result.status, "kill_switch")
        self.assertIn("kill switch", result.reason.lower())


if __name__ == '__main__':
    unittest.main()

