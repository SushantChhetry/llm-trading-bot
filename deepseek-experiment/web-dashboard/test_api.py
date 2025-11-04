#!/usr/bin/env python3
"""
Test script for the Trading Bot API Server
Tests all available endpoints to verify the API is working correctly.
"""

import requests
import json
import sys
from typing import Dict, Any

# Get Railway URL from command line or use default
RAILWAY_URL = sys.argv[1] if len(sys.argv) > 1 else input("Enter your Railway API URL (e.g., https://your-app.up.railway.app): ").strip()

if not RAILWAY_URL:
    print("❌ No URL provided. Exiting.")
    sys.exit(1)

# Remove trailing slash
RAILWAY_URL = RAILWAY_URL.rstrip('/')

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
    print("Testing Trading Bot API Server")
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

    successful = sum(1 for r in results.values() if r.get("success"))
    total = len(results)

    print(f"✅ Successful: {successful}/{total}")
    print(f"❌ Failed: {total - successful}/{total}")

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
