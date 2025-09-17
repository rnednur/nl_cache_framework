#!/usr/bin/env python3
"""
Test script to start ThinkForge server with Hot Commands integration
"""

import subprocess
import time
import requests
import sys

def test_endpoints():
    """Test that Hot Commands endpoints are working"""
    base_url = "http://localhost:8000"
    
    endpoints_to_test = [
        "/api/hot-commands/my",
        "/api/hot-commands/public", 
        "/api/analytics/dashboard",
        "/docs"  # FastAPI auto-generated docs
    ]
    
    print("🧪 Testing Hot Commands API endpoints...")
    
    for endpoint in endpoints_to_test:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            status = "✅" if response.status_code < 500 else "❌"
            print(f"{status} {endpoint} -> {response.status_code}")
        except requests.RequestException as e:
            print(f"❌ {endpoint} -> Error: {e}")
    
    print(f"\n🌐 API Documentation: {base_url}/docs")
    print(f"🔥 Hot Commands UI: http://localhost:3000/hot-commands")

if __name__ == "__main__":
    print("🚀 Starting ThinkForge + Hot Commands integration test...")
    print("Server should be running on: http://localhost:8000")
    print("Make sure to start with: uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload")
    print("\nWaiting 3 seconds for server to be ready...")
    time.sleep(3)
    
    test_endpoints()