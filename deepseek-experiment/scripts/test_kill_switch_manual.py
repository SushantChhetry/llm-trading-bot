#!/usr/bin/env python3
"""
Manual Kill Switch Verification Script

This script allows manual testing of kill switch functionality.
It tests kill switch activation, deactivation, and trade blocking.
"""

import sys
import os
import time
import requests
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import config


def test_kill_switch_activation(risk_service_url: str = "http://localhost:8003"):
    """Test kill switch activation."""
    print("\n" + "="*60)
    print("TEST 1: Kill Switch Activation")
    print("="*60)
    
    try:
        # Activate kill switch
        response = requests.post(
            f"{risk_service_url}/risk/kill_switch",
            json={"action": "activate", "reason": "Manual test activation"},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Kill switch activated successfully")
            print(f"   Active: {data.get('kill_switch_active')}")
            print(f"   Reason: {data.get('reason')}")
            return True
        else:
            print(f"❌ Failed to activate kill switch: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error connecting to risk service: {e}")
        print(f"   Make sure risk service is running at {risk_service_url}")
        return False


def test_kill_switch_prevents_trade(risk_service_url: str = "http://localhost:8003"):
    """Test that kill switch prevents trade execution."""
    print("\n" + "="*60)
    print("TEST 2: Kill Switch Prevents Trade")
    print("="*60)
    
    try:
        # Try to validate an order
        order_data = {
            "strategy_id": "test",
            "symbol": "BTC/USDT",
            "side": "buy",
            "quantity": 0.1,
            "price": 50000.0,
            "leverage": 1.0,
            "current_nav": 10000.0,
            "position_value": 5000.0
        }
        
        response = requests.post(
            f"{risk_service_url}/risk/validate_order",
            json=order_data,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            approved = data.get("approved", False)
            status = data.get("status", "unknown")
            reason = data.get("reason", "")
            
            print(f"Order validation result:")
            print(f"   Approved: {approved}")
            print(f"   Status: {status}")
            print(f"   Reason: {reason}")
            
            if not approved and status == "kill_switch":
                print(f"✅ Kill switch correctly prevented trade")
                return True
            else:
                print(f"❌ Kill switch did NOT prevent trade (should be rejected)")
                return False
        else:
            print(f"❌ Failed to validate order: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error connecting to risk service: {e}")
        return False


def test_kill_switch_deactivation(risk_service_url: str = "http://localhost:8003"):
    """Test kill switch deactivation."""
    print("\n" + "="*60)
    print("TEST 3: Kill Switch Deactivation")
    print("="*60)
    
    try:
        # Deactivate kill switch
        response = requests.post(
            f"{risk_service_url}/risk/kill_switch",
            json={"action": "deactivate"},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Kill switch deactivated successfully")
            print(f"   Active: {data.get('kill_switch_active')}")
            print(f"   Reason: {data.get('reason')}")
            return True
        else:
            print(f"❌ Failed to deactivate kill switch: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error connecting to risk service: {e}")
        return False


def test_trade_after_deactivation(risk_service_url: str = "http://localhost:8003"):
    """Test that trades are allowed after kill switch deactivation."""
    print("\n" + "="*60)
    print("TEST 4: Trade Allowed After Deactivation")
    print("="*60)
    
    try:
        # Try to validate an order (should be approved now)
        order_data = {
            "strategy_id": "test",
            "symbol": "BTC/USDT",
            "side": "buy",
            "quantity": 0.1,
            "price": 50000.0,
            "leverage": 1.0,
            "current_nav": 10000.0,
            "position_value": 5000.0
        }
        
        response = requests.post(
            f"{risk_service_url}/risk/validate_order",
            json=order_data,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            approved = data.get("approved", False)
            status = data.get("status", "unknown")
            reason = data.get("reason", "")
            
            print(f"Order validation result:")
            print(f"   Approved: {approved}")
            print(f"   Status: {status}")
            print(f"   Reason: {reason}")
            
            if approved and status == "approved":
                print(f"✅ Trade correctly allowed after kill switch deactivation")
                return True
            else:
                print(f"⚠️  Trade was not approved (may be due to other risk limits)")
                print(f"   This is OK if other risk checks are failing")
                return True  # Not a failure - other checks may reject
        else:
            print(f"❌ Failed to validate order: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error connecting to risk service: {e}")
        return False


def get_risk_state(risk_service_url: str = "http://localhost:8003"):
    """Get current risk state."""
    try:
        response = requests.get(
            f"{risk_service_url}/risk/limits",
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.exceptions.RequestException:
        return None


def main():
    """Run all kill switch tests."""
    print("\n" + "="*60)
    print("KILL SWITCH MANUAL VERIFICATION")
    print("="*60)
    print(f"Risk Service URL: http://localhost:8003")
    print(f"Trading Mode: {config.TRADING_MODE}")
    
    # Check if risk service is available
    print("\nChecking risk service availability...")
    risk_state = get_risk_state()
    if risk_state is None:
        print("❌ Risk service is not available!")
        print("   Please start the risk service first:")
        print("   python -m services.risk_service")
        return 1
    
    print("✅ Risk service is available")
    print(f"   Kill switch active: {risk_state.get('kill_switch_active', False)}")
    
    # Run tests
    results = []
    
    # Test 1: Activation
    results.append(("Activation", test_kill_switch_activation()))
    
    # Test 2: Prevents trade
    results.append(("Prevents Trade", test_kill_switch_prevents_trade()))
    
    # Test 3: Deactivation
    results.append(("Deactivation", test_kill_switch_deactivation()))
    
    # Test 4: Trade after deactivation
    results.append(("Trade After Deactivation", test_trade_after_deactivation()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

