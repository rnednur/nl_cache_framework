#!/usr/bin/env python3
"""
Test script for cache entry integration with Hot Commands
"""

import requests
import json

def test_cache_integration():
    """Test the new cache entry integration endpoints"""
    base_url = "http://localhost:8000"
    
    print("🔍 Testing Cache Entry Integration endpoints...\n")
    
    # Test getting available cache entries
    print("1. Testing /api/cache-entries/available")
    try:
        response = requests.get(f"{base_url}/api/cache-entries/available", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {len(data)} cache entries")
            if data:
                print(f"   First entry: {data[0]['id']} - {data[0]['nl_query'][:50]}...")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    print()
    
    # Test getting cache entry details (using entry ID 1 as example)
    print("2. Testing /api/cache-entries/1/details")
    try:
        response = requests.get(f"{base_url}/api/cache-entries/1/details", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Entry: {data['nl_query'][:50]}...")
            print(f"   Template type: {data['template_type']}")
            print(f"   Has hot command: {data['has_hot_command']}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    print()
    
    # Test original endpoints to see if they still work
    print("3. Testing original /api/hot-commands/my")
    try:
        response = requests.get(f"{base_url}/api/hot-commands/my", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")

if __name__ == "__main__":
    test_cache_integration()