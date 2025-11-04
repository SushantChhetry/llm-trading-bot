#!/usr/bin/env python3
"""
Test API endpoints after Supabase setup
Tests all endpoints and verifies Supabase connection
"""

import requests
import json
import sys
from typing import Dict, Any

RAILWAY_URL = "https://llm-trading-bot-production-4ede.up.railway.app"

def test_endpoint(name: str, path: str, expected_status: int = 200) -> Dict[str, Any]:
    """Test an API endpoint and return results."""
    url = f"{RAILWAY_URL}{path}"
    try:
        response = requests.get(url, timeout=10)
        status = "✅" if response.status_code == expected_status else "❌"
        print(f"{status} {name}: {response.status_code}")

        if response.status_code == expected_status:
            try:
                data = response.json()
                return {"success": True, "data": data, "status_code": response.status_code}
            except:
                return {"success": True, "data": response.text, "status_code": response.status_code}
        else:
            print(f"   Error: {response.text[:200]}")
            return {"success": False, "error": response.text, "status_code": response.status_code}
    except requests.exceptions.RequestException as e:
        print(f"❌ {name}: Connection error - {e}")
        return {"success": False, "error": str(e)}

def main():
    print("=" * 80)
    print("Testing Trading Bot API Server with Supabase")
    print(f"URL: {RAILWAY_URL}")
    print("=" * 80)
    print()

    results = {}

    # Test basic endpoints
    print("📋 Basic Endpoints:")
    results["health"] = test_endpoint("Health Check", "/health")
    results["root"] = test_endpoint("Root", "/")
    results["live"] = test_endpoint("Liveness", "/live")
    results["ready"] = test_endpoint("Readiness", "/ready")

    print()
    print("📊 API Endpoints:")
    results["status"] = test_endpoint("Bot Status", "/api/status")
    results["portfolio"] = test_endpoint("Portfolio", "/api/portfolio")
    results["trades"] = test_endpoint("Trades", "/api/trades?limit=5")
    results["latest_trade"] = test_endpoint("Latest Trade", "/api/latest-trade")
    results["stats"] = test_endpoint("Statistics", "/api/stats")
    results["behavioral"] = test_endpoint("Behavioral Metrics", "/api/behavioral")

    print()
    print("=" * 80)
    print("Test Summary")
    print("=" * 80)

    # Check root endpoint for database type
    if results.get("root", {}).get("success"):
        db_type = results["root"]["data"].get("database", "Unknown")
        print(f"Database Type: {db_type}")
        if db_type == "Supabase":
            print("✅ Supabase is connected!")
        else:
            print("⚠️  Using JSON file storage (Supabase not connected)")
            print("   To use Supabase:")
            print("   1. Set SUPABASE_URL and SUPABASE_KEY in Railway variables")
            print("   2. Run supabase_schema.sql in Supabase SQL editor")

    print()
    successful = sum(1 for r in results.values() if r.get("success"))
    total = len(results)

    print(f"✅ Successful: {successful}/{total}")
    print(f"❌ Failed: {total - successful}/{total}")

    # Show detailed results for portfolio and stats
    if results.get("portfolio", {}).get("success"):
        print("\n📊 Portfolio Data:")
        portfolio = results["portfolio"]["data"]
        print(f"   Balance: {portfolio.get('balance', 'N/A')}")
        print(f"   Total Value: {portfolio.get('total_value', 'N/A')}")
        print(f"   Total Return: {portfolio.get('total_return_pct', 'N/A')}%")

    if results.get("stats", {}).get("success"):
        print("\n📈 Statistics:")
        stats = results["stats"]["data"]
        print(f"   Total Trades: {stats.get('total_trades', 'N/A')}")
        print(f"   Win Rate: {stats.get('win_rate', 'N/A')}%")
        print(f"   Avg Trade Size: {stats.get('avg_trade_size', 'N/A')}")

    if successful == total:
        print("\n🎉 All endpoints are working correctly!")
        return 0
    else:
        print("\n⚠️  Some endpoints failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
