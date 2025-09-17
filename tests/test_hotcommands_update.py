#!/usr/bin/env python3
"""
Test script to verify Hot Commands update functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json

def test_hot_commands_update():
    """Test the Hot Commands update API endpoint."""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Hot Commands Update API")
    print("=" * 50)
    
    # Step 1: Get existing hot commands
    print("\n1. Fetching existing hot commands...")
    try:
        response = requests.get(f"{base_url}/api/hot-commands/my")
        if response.status_code != 200:
            print(f"❌ Failed to fetch hot commands: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        commands = response.json()
        if not commands:
            print("ℹ️  No hot commands found. Create one first through the cache explorer.")
            return True
        
        test_command = commands[0]
        print(f"✅ Found {len(commands)} hot commands")
        print(f"   Testing with command: {test_command['command_name']} (ID: {test_command['id']})")
        
    except Exception as e:
        print(f"❌ Error fetching hot commands: {e}")
        return False
    
    # Step 2: Test updating the command
    print(f"\n2. Testing update on command ID {test_command['id']}...")
    
    # Prepare update data (matching what the frontend sends)
    update_data = {
        "command_name": test_command['command_name'],  # Keep same name
        "display_name": f"Updated Test - {test_command.get('display_name', 'Test')}",
        "description": f"Updated description - {test_command.get('description', 'Test description')}",
        "domain": test_command.get('domain', 'Analytics'),
        "category": test_command.get('category', 'Performance'),
        "tags": test_command.get('tags', []) + ["test_update"],
        "is_public": test_command.get('is_public', False)
    }
    
    print(f"   Update data: {json.dumps(update_data, indent=2)}")
    
    try:
        response = requests.put(
            f"{base_url}/api/hot-commands/{test_command['id']}", 
            json=update_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            updated_command = response.json()
            print("✅ Update successful!")
            print(f"   Updated display_name: {updated_command.get('display_name')}")
            print(f"   Updated description: {updated_command.get('description')}")
            print(f"   Updated tags: {updated_command.get('tags')}")
            
            # Step 3: Verify the update persisted
            print(f"\n3. Verifying update persisted...")
            verify_response = requests.get(f"{base_url}/api/hot-commands/{test_command['id']}")
            if verify_response.status_code == 200:
                verified_command = verify_response.json()
                if verified_command['display_name'] == update_data['display_name']:
                    print("✅ Update verification successful!")
                    return True
                else:
                    print("❌ Update did not persist correctly")
                    return False
            else:
                print(f"❌ Failed to verify update: {verify_response.status_code}")
                return False
        
        else:
            print(f"❌ Update failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            
            # Check if it's a foreign key error
            if "foreign key" in response.text.lower() or "text2sql_cache" in response.text.lower():
                print("\n🔧 This appears to be the foreign key constraint issue!")
                print("   Run the fix script: python fix_hotcommands_fk.py")
            
            return False
            
    except Exception as e:
        print(f"❌ Error during update: {e}")
        return False

def test_backend_connectivity():
    """Test basic backend connectivity."""
    
    base_url = "http://localhost:8000"
    
    try:
        response = requests.get(f"{base_url}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is accessible")
            return True
        else:
            print(f"❌ Backend returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        print("   Make sure the backend is running: python run_server.py")
        return False

if __name__ == "__main__":
    print("🔧 Hot Commands Update Test")
    print("=" * 50)
    
    # Test backend connectivity
    print("Checking backend connectivity...")
    if not test_backend_connectivity():
        sys.exit(1)
    
    # Test hot commands update
    if test_hot_commands_update():
        print("\n🎉 All tests passed! Hot Commands update is working correctly.")
    else:
        print("\n❌ Tests failed. Check the output above for details.")
        sys.exit(1)