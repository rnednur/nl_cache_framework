#!/usr/bin/env python3
"""
Test the hot commands metadata endpoint
"""

import requests
import json

def test_metadata_endpoint():
    """Test the metadata endpoint."""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Hot Commands Metadata Endpoint")
    print("=" * 50)
    
    try:
        # Test the metadata endpoint
        print(f"\n📡 GET {base_url}/api/hot-commands/metadata")
        response = requests.get(f"{base_url}/api/hot-commands/metadata")
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Success! Metadata received:")
            print(json.dumps(data, indent=2))
            
            # Validate structure
            expected_keys = ["domains", "categories", "tags", "query_types", "template_types"]
            missing_keys = [key for key in expected_keys if key not in data]
            
            if missing_keys:
                print(f"⚠️  Missing keys: {missing_keys}")
            else:
                print("✅ All expected keys present")
                
                # Show counts
                print(f"\n📊 Data Summary:")
                print(f"   • Domains: {len(data['domains'])} ({', '.join(data['domains'])})")
                print(f"   • Categories: {len(data['categories'])} ({', '.join(data['categories'])})")
                print(f"   • Tags: {len(data['tags'])} ({', '.join(data['tags'][:5])}{'...' if len(data['tags']) > 5 else ''})")
                print(f"   • Query Types: {len(data['query_types'])} ({', '.join(data['query_types'])})")
                print(f"   • Template Types: {len(data['template_types'])} ({', '.join(data['template_types'])})")
                
                if not data['domains'] and not data['categories']:
                    print("\n💡 No domains/categories found. Run 'python setup_sample_data.py' to populate database.")
            
            return True
            
        else:
            print(f"❌ Failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Make sure it's running:")
        print("   python run_server.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_route_conflict():
    """Test that the route conflict is resolved."""
    
    base_url = "http://localhost:8000"
    
    print(f"\n🔍 Testing Route Conflict Resolution")
    print("-" * 40)
    
    # Test that /metadata doesn't conflict with /{command_id}
    endpoints_to_test = [
        ("/api/hot-commands/metadata", "Should return metadata"),
        ("/api/hot-commands/my", "Should return user's commands"),
        ("/api/hot-commands/public", "Should return public commands"),
    ]
    
    for endpoint, description in endpoints_to_test:
        try:
            response = requests.get(f"{base_url}{endpoint}")
            if response.status_code < 400:
                print(f"✅ {endpoint} - Working ({response.status_code})")
            else:
                print(f"❌ {endpoint} - Error ({response.status_code})")
        except Exception as e:
            print(f"❌ {endpoint} - Exception: {e}")

if __name__ == "__main__":
    if test_metadata_endpoint():
        print("\n🎉 Metadata endpoint is working correctly!")
        test_route_conflict()
    else:
        print("\n❌ Metadata endpoint test failed!")
        exit(1)