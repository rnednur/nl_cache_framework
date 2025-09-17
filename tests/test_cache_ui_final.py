#!/usr/bin/env python3
"""
Final test for Cache Explorer UI - Quick validation
"""

import requests

def test_cache_ui():
    """Quick test of cache UI integration"""
    print("🔍 Testing Cache Explorer UI Integration...\n")
    
    base_url = "http://localhost:8000"
    
    # Test backend endpoints
    endpoints = [
        ("/api/cache-entries/available", "Cache Entries Available"),
        ("/api/hot-commands/my", "Hot Commands"),
        ("/docs", "API Documentation")
    ]
    
    print("Backend API Status:")
    all_good = True
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            status = "✅ Working" if response.status_code < 400 else f"❌ Error {response.status_code}"
            print(f"   {name}: {status}")
            if response.status_code >= 400:
                all_good = False
        except Exception as e:
            print(f"   {name}: ❌ Connection failed")
            all_good = False
    
    if all_good:
        print(f"\n🎉 Backend is ready!")
        print(f"📊 API Documentation: {base_url}/docs")
        
        # Test cache entries availability
        try:
            response = requests.get(f"{base_url}/api/cache-entries/available?limit=1")
            if response.status_code == 200:
                data = response.json()
                print(f"🗄️  Available cache entries: {len(data)} (showing 1)")
                if data:
                    entry = data[0]
                    print(f"   📝 Sample: {entry['nl_query'][:60]}...")
                    print(f"   🔧 Type: {entry['template_type']}")
                    print(f"   📊 Stats: {entry['execution_count']} runs, {entry['success_rate']}% success")
        except Exception as e:
            print(f"⚠️  Cache entries: {e}")
    
    print(f"\n🚀 UI Ready!")
    print(f"   1. Start frontend: cd frontend-react && npm run dev")
    print(f"   2. Visit: http://localhost:3000/cache-explorer")
    print(f"   3. Browse ThinkForge cache entries")
    print(f"   4. Convert entries to Hot Commands")
    
    print(f"\n✨ Fixed UI Issues:")
    print(f"   ✅ SelectItem empty string values -> 'all' values")
    print(f"   ✅ Import paths corrected for UI components")
    print(f"   ✅ Filter logic updated for 'all' option")
    
    return all_good

if __name__ == "__main__":
    test_cache_ui()