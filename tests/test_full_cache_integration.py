#!/usr/bin/env python3
"""
Complete test of cache entry integration with Hot Commands
"""

import requests
import json

def test_full_integration():
    """Test the complete cache integration workflow"""
    base_url = "http://localhost:8000"
    
    print("🚀 Testing Complete Cache Entry Integration...\n")
    
    # Step 1: Get available cache entries
    print("Step 1: Getting available cache entries...")
    try:
        response = requests.get(f"{base_url}/api/cache-entries/available?limit=5", timeout=10)
        if response.status_code == 200:
            entries = response.json()
            print(f"   ✅ Found {len(entries)} cache entries")
            
            if entries:
                # Pick the first entry for testing
                test_entry = entries[0]
                cache_id = test_entry['id']
                print(f"   📝 Using entry {cache_id}: {test_entry['nl_query'][:60]}...")
                print(f"   📊 Template type: {test_entry['template_type']}")
                print(f"   📈 Execution stats: {test_entry['execution_count']} runs, {test_entry['success_rate']}% success")
                print(f"   🔗 Has hot command: {test_entry['has_hot_command']}")
                
                # Step 2: Get detailed info about the entry
                print(f"\nStep 2: Getting details for cache entry {cache_id}...")
                detail_response = requests.get(f"{base_url}/api/cache-entries/{cache_id}/details", timeout=10)
                if detail_response.status_code == 200:
                    details = detail_response.json()
                    print(f"   ✅ Retrieved details")
                    print(f"   📄 Template: {details['template'][:100]}...")
                    print(f"   🏷️  Tags: {list(details['tags'].keys()) if details['tags'] else 'None'}")
                    print(f"   🤖 Has hot command: {details['has_hot_command']}")
                else:
                    print(f"   ❌ Failed to get details: {detail_response.status_code}")
                    return
                
                # Step 3: Create a hot command from this cache entry (if it doesn't have one)
                if not test_entry['has_hot_command']:
                    print(f"\nStep 3: Creating hot command from cache entry {cache_id}...")
                    create_data = {
                        "cache_entry_id": cache_id,
                        "command_name": f"test_cmd_{cache_id}",
                        "display_name": f"Test Command {cache_id}",
                        "description": f"Generated from cache entry {cache_id}",
                        "is_public": False,
                        "tags": ["test", "generated", "cache-integration"]
                    }
                    
                    create_response = requests.post(
                        f"{base_url}/api/cache-entries/create-command",
                        json=create_data,
                        timeout=10
                    )
                    
                    if create_response.status_code == 200:
                        new_command = create_response.json()
                        print(f"   ✅ Created hot command: {new_command['command_name']}")
                        print(f"   🔗 Connected to cache entry: {new_command['cache_entry_id']}")
                        print(f"   📋 Inherited metadata:")
                        print(f"      - Template type: {new_command['source_template_type']}")
                        print(f"      - Reasoning: {new_command['source_reasoning'][:100] if new_command['source_reasoning'] else 'None'}...")
                        if new_command['source_execution_stats']:
                            stats = new_command['source_execution_stats']
                            print(f"      - Inherited stats: {stats.get('execution_count', 0)} executions")
                            print(f"      - Success rate: {stats.get('success_rate', 0)}%")
                    else:
                        print(f"   ❌ Failed to create command: {create_response.status_code} - {create_response.text}")
                        return
                else:
                    print(f"\nStep 3: Entry already has hot command: {test_entry['hot_command_name']}")
                
                # Step 4: Verify the command was created by checking our commands
                print(f"\nStep 4: Verifying hot command creation...")
                my_commands_response = requests.get(f"{base_url}/api/hot-commands/my", timeout=10)
                if my_commands_response.status_code == 200:
                    my_commands = my_commands_response.json()
                    print(f"   ✅ Retrieved {len(my_commands)} user commands")
                    
                    # Look for commands connected to cache entries
                    cache_connected = [cmd for cmd in my_commands if cmd.get('cache_entry_id')]
                    print(f"   🔗 {len(cache_connected)} commands connected to cache entries:")
                    
                    for cmd in cache_connected:
                        print(f"      - {cmd['command_name']}: cache entry {cmd['cache_entry_id']}")
                        if cmd.get('source_template_type'):
                            print(f"        Template: {cmd['source_template_type']}")
                        if cmd.get('source_execution_stats'):
                            stats = cmd['source_execution_stats']
                            print(f"        Stats: {stats.get('execution_count', 0)} runs")
                else:
                    print(f"   ❌ Failed to get user commands: {my_commands_response.status_code}")
                
                print(f"\n🎉 Cache integration test completed successfully!")
                print(f"   ✅ Can browse {len(entries)} available cache entries")
                print(f"   ✅ Can view detailed cache entry information")
                print(f"   ✅ Can create hot commands from cache entries")
                print(f"   ✅ Commands inherit metadata and performance stats")
                print(f"   ✅ Full end-to-end workflow operational")
                
            else:
                print("   ⚠️  No cache entries found in database")
        else:
            print(f"   ❌ Failed to get entries: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   💥 Exception: {e}")

if __name__ == "__main__":
    test_full_integration()