#!/usr/bin/env python3
"""
Wrapper service integration example.
Demonstrates how to integrate with external services for tool resolution.
"""

import asyncio
import json
from pathlib import Path

from notebook_sandbox import (
    PythonNotebookGenerator,
    NotebookExecutor,
    WrapperClient,
    MCPClient,
    ResourceConfig
)
from notebook_sandbox.generators.base_generator import GenerationRequest, NotebookMetadata

async def wrapper_client_example():
    """Example using generic wrapper client."""
    
    print("🔌 Wrapper Client Integration Example")
    print("=" * 50)
    
    # Initialize wrapper client
    wrapper_service_url = "http://localhost:8080"  # Your wrapper service URL
    
    try:
        async with WrapperClient(wrapper_service_url) as wrapper:
            print(f"   ✓ Connected to wrapper service: {wrapper_service_url}")
            
            # Check service health
            health = await wrapper.health_check()
            print(f"   ✓ Service health: {health.get('status', 'unknown')}")
            
            # List available tools
            print("\n📋 Available tools:")
            tools = await wrapper.list_tools(limit=5)
            
            for tool in tools:
                print(f"   - {tool.name} ({tool.tool_type}): {tool.description[:60]}...")
            
            # Resolve tools for a specific task
            print("\n🔍 Resolving tools for 'query database for user information':")
            
            search_result = await wrapper.resolve_tools(
                "query database for user information",
                tool_type="sql",
                limit=3,
                threshold=0.3
            )
            
            print(f"   ✓ Found {len(search_result.tools)} matching tools:")
            for tool in search_result.tools:
                print(f"      - {tool.name} (confidence: {tool.confidence_score:.2f})")
            
            # Generate notebook with wrapper-resolved tools
            print("\n📓 Generating notebook with wrapper tools:")
            
            generator = PythonNotebookGenerator(tool_resolver=wrapper)
            
            workflow_content = {
                "description": "Analyze user database and generate insights",
                "steps": [
                    {
                        "id": "step_1",
                        "name": "Query User Data",
                        "description": "Query database for user information and statistics",
                        "type": "sql"
                    },
                    {
                        "id": "step_2",
                        "name": "API Integration",
                        "description": "Fetch additional data from external API",
                        "type": "api"
                    }
                ]
            }
            
            request = GenerationRequest(
                content=workflow_content,
                workflow_name="user_analysis_wrapper",
                metadata=NotebookMetadata(
                    title="User Analysis with Wrapper Tools",
                    description="Generated using wrapper service for tool resolution"
                )
            )
            
            result = await generator.generate(request)
            
            if result.success:
                print(f"   ✓ Notebook generated with {result.cell_count} cells")
                print(f"   ✓ Used wrapper service for tool resolution")
                
                # Save the notebook
                output_dir = Path("/tmp/notebook-sandbox-wrapper")
                output_dir.mkdir(parents=True, exist_ok=True)
                
                notebook_path = output_dir / "user_analysis_wrapper.ipynb"
                with open(notebook_path, 'w', encoding='utf-8') as f:
                    f.write(result.notebook_content)
                
                print(f"   ✓ Saved to: {notebook_path}")
            else:
                print(f"   ❌ Generation failed: {result.error}")
    
    except Exception as e:
        print(f"   ❌ Wrapper client error: {str(e)}")
        print("   ℹ️ Make sure wrapper service is running at the configured URL")

async def mcp_client_example():
    """Example using MCP client."""
    
    print("\n🔗 MCP Client Integration Example")
    print("=" * 50)
    
    # Initialize MCP client
    mcp_server_url = "http://localhost:8000"  # Your MCP server URL
    
    try:
        async with MCPClient(mcp_server_url) as mcp:
            print(f"   ✓ Connected to MCP server: {mcp_server_url}")
            
            # Check MCP health
            health = await mcp.health_check()
            print(f"   ✓ MCP health: {health.get('status', 'unknown')}")
            
            # List MCP tools
            print("\n🛠️ Available MCP tools:")
            tools = await mcp.list_tools(limit=5)
            
            for tool in tools:
                print(f"   - {tool.name} ({tool.tool_type}): {tool.description[:60]}...")
            
            # Resolve tools using MCP
            print("\n🔍 MCP tool resolution for 'execute SQL query':")
            
            search_result = await mcp.resolve_tools(
                "execute SQL query",
                threshold=0.2
            )
            
            print(f"   ✓ Found {len(search_result.tools)} MCP tools:")
            for tool in search_result.tools:
                print(f"      - {tool.name} (confidence: {tool.confidence_score:.2f})")
            
            # Test tool execution
            if search_result.tools:
                tool = search_result.tools[0]
                print(f"\n⚙️ Testing execution of: {tool.name}")
                
                # Example tool execution (adjust parameters as needed)
                try:
                    execution_result = await mcp.execute_tool(
                        tool.id,
                        {"query": "SELECT COUNT(*) FROM users"}
                    )
                    
                    if execution_result.get("success"):
                        print(f"   ✓ Tool executed successfully")
                        print(f"   ✓ Result preview: {str(execution_result.get('result', {}))[:100]}...")
                    else:
                        print(f"   ❌ Tool execution failed: {execution_result.get('error')}")
                        
                except Exception as e:
                    print(f"   ⚠️ Tool execution error: {str(e)}")
            
            # Generate notebook with MCP tools
            print("\n📓 Generating notebook with MCP tools:")
            
            generator = PythonNotebookGenerator(tool_resolver=mcp)
            
            workflow_content = {
                "recipe_text": """
                1. Connect to the database and retrieve user statistics
                2. Execute data quality checks on user records
                3. Generate summary report with key metrics
                """
            }
            
            request = GenerationRequest(
                content=workflow_content,
                workflow_name="mcp_database_analysis",
                metadata=NotebookMetadata(
                    title="Database Analysis via MCP",
                    description="Generated using MCP tools for database operations"
                )
            )
            
            result = await generator.generate(request)
            
            if result.success:
                print(f"   ✓ MCP notebook generated with {result.cell_count} cells")
                
                # Save the notebook
                output_dir = Path("/tmp/notebook-sandbox-mcp")
                output_dir.mkdir(parents=True, exist_ok=True)
                
                notebook_path = output_dir / "mcp_database_analysis.ipynb"
                with open(notebook_path, 'w', encoding='utf-8') as f:
                    f.write(result.notebook_content)
                
                print(f"   ✓ Saved to: {notebook_path}")
            else:
                print(f"   ❌ MCP generation failed: {result.error}")
    
    except Exception as e:
        print(f"   ❌ MCP client error: {str(e)}")
        print("   ℹ️ Make sure MCP server is running at the configured URL")

async def thinkforge_integration_example():
    """Example showing integration with ThinkForge backend."""
    
    print("\n🧠 ThinkForge Integration Example")
    print("=" * 50)
    
    # This would connect to your ThinkForge backend
    thinkforge_url = "http://localhost:8000"
    
    try:
        async with WrapperClient(
            thinkforge_url,
            auth_token="your-auth-token"  # If authentication is required
        ) as thinkforge:
            
            print(f"   ✓ Connected to ThinkForge: {thinkforge_url}")
            
            # Example DSL workflow from ThinkForge
            dsl_workflow = {
                "nodes": [
                    {
                        "id": "node_1",
                        "type": "data_source",
                        "data": {
                            "label": "User Database",
                            "query": "SELECT * FROM users WHERE active = true"
                        }
                    },
                    {
                        "id": "node_2", 
                        "type": "transform",
                        "data": {
                            "label": "Data Processing",
                            "operation": "group_by_department"
                        }
                    },
                    {
                        "id": "node_3",
                        "type": "visualization",
                        "data": {
                            "label": "Generate Charts",
                            "chart_type": "bar_chart"
                        }
                    }
                ],
                "edges": [
                    {"source": "node_1", "target": "node_2"},
                    {"source": "node_2", "target": "node_3"}
                ]
            }
            
            # Generate notebook from ThinkForge DSL
            generator = PythonNotebookGenerator(tool_resolver=thinkforge)
            
            request = GenerationRequest(
                content=dsl_workflow,
                workflow_name="thinkforge_user_analysis",
                metadata=NotebookMetadata(
                    title="ThinkForge User Analysis",
                    description="Generated from ThinkForge DSL workflow",
                    tags=["thinkforge", "dsl", "analysis"]
                )
            )
            
            result = await generator.generate(request)
            
            if result.success:
                print(f"   ✓ ThinkForge notebook generated with {result.cell_count} cells")
                
                # Execute the notebook in sandbox
                output_dir = Path("/tmp/notebook-sandbox-thinkforge")
                output_dir.mkdir(parents=True, exist_ok=True)
                
                notebook_path = output_dir / "thinkforge_user_analysis.ipynb"
                with open(notebook_path, 'w', encoding='utf-8') as f:
                    f.write(result.notebook_content)
                
                print(f"   ✓ Saved to: {notebook_path}")
                
                # Optional: Execute in sandbox
                executor = NotebookExecutor(
                    notebook_dir=output_dir,
                    output_dir=output_dir / "output",
                    resource_config=ResourceConfig(max_memory_mb=1024)
                )
                
                print(f"   📋 Executing ThinkForge-generated notebook...")
                execution_result = executor.execute_notebook("thinkforge_user_analysis.ipynb")
                
                if execution_result.success:
                    print(f"   ✅ Execution completed in {execution_result.execution_time:.2f}s")
                else:
                    print(f"   ❌ Execution failed: {execution_result.error}")
            
            else:
                print(f"   ❌ ThinkForge generation failed: {result.error}")
    
    except Exception as e:
        print(f"   ❌ ThinkForge integration error: {str(e)}")
        print("   ℹ️ Make sure ThinkForge backend is running with sandbox API enabled")

async def main():
    """Run all wrapper integration examples."""
    
    print("🌐 Notebook Sandbox - Wrapper Service Integration Examples")
    print("=" * 60)
    print("This example demonstrates integration with various wrapper services.")
    print("Note: Services must be running at the configured URLs.")
    print()
    
    # Run examples
    await wrapper_client_example()
    await mcp_client_example()
    await thinkforge_integration_example()
    
    print("\n" + "=" * 60)
    print("✅ Wrapper integration examples completed!")
    print("\nKey takeaways:")
    print("• Use WrapperClient for generic REST API integration")
    print("• Use MCPClient for Model Context Protocol servers")
    print("• Tool resolvers are pluggable - easy to switch between services")
    print("• Generated notebooks include tool-specific code templates")
    print("• All examples work with the same notebook execution engine")

if __name__ == "__main__":
    asyncio.run(main())