#!/usr/bin/env python3
"""
Command-line interface for notebook-sandbox.
"""

import asyncio
import click
import json
from pathlib import Path
from typing import Optional

from .core.executor import NotebookExecutor
from .core.validator import NotebookValidator
from .core.container_manager import ContainerManager
from .generators.python_generator import PythonNotebookGenerator
from .generators.base_generator import GenerationRequest, NotebookMetadata
from .integrations.tool_resolver import MockToolResolver
from .integrations.wrapper_client import WrapperClient
from .integrations.mcp_client import MCPClient
from .config.resources import ResourceConfig
from .config.security import SecurityConfig

@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Notebook Sandbox - Secure notebook execution environment."""
    pass

@cli.command()
@click.option("--notebook", "-n", required=True, help="Notebook file to execute")
@click.option("--validate-only", "-v", is_flag=True, help="Only validate, don't execute")
@click.option("--memory-limit", "-m", default=512, help="Memory limit in MB")
@click.option("--cpu-time", "-c", default=300, help="CPU time limit in seconds")
@click.option("--wall-time", "-w", default=600, help="Wall time limit in seconds")
@click.option("--notebook-dir", default="./notebooks", help="Notebook directory")
@click.option("--output-dir", default="./output", help="Output directory")
def execute(notebook: str, validate_only: bool, memory_limit: int, 
           cpu_time: int, wall_time: int, notebook_dir: str, output_dir: str):
    """Execute a notebook with security validation."""
    
    async def _execute():
        # Setup configuration
        resource_config = ResourceConfig(
            max_memory_mb=memory_limit,
            max_cpu_time=cpu_time,
            max_wall_time=wall_time
        )
        
        # Initialize executor
        executor = NotebookExecutor(
            notebook_dir=Path(notebook_dir),
            output_dir=Path(output_dir),
            resource_config=resource_config
        )
        
        try:
            if validate_only:
                # Only validate
                result = executor.validate_notebook(notebook)
                click.echo(json.dumps(result, indent=2))
                
                if not result["valid"]:
                    click.echo(f"❌ Validation failed with {result['issue_count']} issues", err=True)
                    exit(1)
                else:
                    click.echo("✅ Validation passed")
            else:
                # Execute notebook
                result = executor.execute_notebook(notebook)
                click.echo(json.dumps(result.to_dict(), indent=2))
                
                if not result.success:
                    click.echo(f"❌ Execution failed: {result.error}", err=True)
                    exit(1)
                else:
                    click.echo(f"✅ Execution completed in {result.execution_time:.2f}s")
        
        except FileNotFoundError:
            click.echo(f"❌ Notebook not found: {notebook}", err=True)
            exit(1)
        except Exception as e:
            click.echo(f"❌ Error: {str(e)}", err=True)
            exit(1)
    
    asyncio.run(_execute())

@cli.command()
@click.option("--content", "-c", required=True, help="Content file (JSON) or workflow description")
@click.option("--workflow-name", "-w", required=True, help="Workflow name")
@click.option("--output", "-o", help="Output notebook file")
@click.option("--generator", "-g", default="python", help="Generator type (python)")
@click.option("--resolver-type", default="mock", help="Tool resolver type (mock, wrapper, mcp)")
@click.option("--resolver-url", help="Wrapper service or MCP server URL")
def generate(content: str, workflow_name: str, output: Optional[str], 
           generator: str, resolver_type: str, resolver_url: Optional[str]):
    """Generate a notebook from workflow content."""
    
    async def _generate():
        try:
            # Load content
            if content.endswith('.json'):
                with open(content, 'r') as f:
                    workflow_content = json.load(f)
            else:
                # Treat as description
                workflow_content = {"description": content}
            
            # Setup tool resolver
            if resolver_type == "wrapper" and resolver_url:
                async with WrapperClient(resolver_url) as resolver:
                    await _do_generation(workflow_content, workflow_name, output, resolver)
            elif resolver_type == "mcp" and resolver_url:
                async with MCPClient(resolver_url) as resolver:
                    await _do_generation(workflow_content, workflow_name, output, resolver)
            else:
                # Use mock resolver
                resolver = MockToolResolver()
                await _do_generation(workflow_content, workflow_name, output, resolver)
        
        except FileNotFoundError:
            click.echo(f"❌ Content file not found: {content}", err=True)
            exit(1)
        except json.JSONDecodeError:
            click.echo(f"❌ Invalid JSON in content file: {content}", err=True)
            exit(1)
        except Exception as e:
            click.echo(f"❌ Generation error: {str(e)}", err=True)
            exit(1)
    
    async def _do_generation(workflow_content, workflow_name, output, resolver):
        # Initialize generator
        if generator == "python":
            gen = PythonNotebookGenerator(tool_resolver=resolver)
        else:
            click.echo(f"❌ Unknown generator type: {generator}", err=True)
            exit(1)
        
        # Create generation request
        request = GenerationRequest(
            content=workflow_content,
            workflow_name=workflow_name,
            metadata=NotebookMetadata(
                title=workflow_name.replace("_", " ").title(),
                description=f"Generated notebook for workflow: {workflow_name}"
            )
        )
        
        # Generate notebook
        result = await gen.generate(request)
        
        if not result.success:
            click.echo(f"❌ Generation failed: {result.error}", err=True)
            exit(1)
        
        # Save notebook
        if not output:
            output = f"{workflow_name}.ipynb"
        
        with open(output, 'w', encoding='utf-8') as f:
            f.write(result.notebook_content)
        
        click.echo(f"✅ Notebook generated: {output}")
        click.echo(f"   Cells: {result.cell_count}")
        click.echo(f"   Warnings: {len(result.warnings)}")
        
        if result.warnings:
            for warning in result.warnings:
                click.echo(f"   ⚠️ {warning}")
    
    asyncio.run(_generate())

@cli.command()
@click.option("--notebook", "-n", required=True, help="Notebook file to validate")
@click.option("--strict", is_flag=True, help="Use strict security validation")
@click.option("--allow-network", is_flag=True, help="Allow network access")
@click.option("--allow-filesystem", is_flag=True, help="Allow filesystem access")
def validate(notebook: str, strict: bool, allow_network: bool, allow_filesystem: bool):
    """Validate a notebook for security issues."""
    
    try:
        # Setup security config
        security_config = SecurityConfig(
            strict_mode=strict,
            allow_network_access=allow_network,
            allow_file_system_access=allow_filesystem
        )
        
        # Initialize validator
        validator = NotebookValidator(security_config.get_security_policy())
        
        # Validate notebook
        result = validator.validate_notebook(Path(notebook))
        
        # Display results
        click.echo(json.dumps(result, indent=2))
        
        if result["valid"]:
            click.echo("✅ Validation passed")
        else:
            click.echo(f"❌ Validation failed with {result['issue_count']} issues")
            
            # Show issues by severity
            for severity in ["error", "warning", "info"]:
                count = result["issues_by_severity"].get(severity, 0)
                if count > 0:
                    click.echo(f"   {severity.upper()}: {count} issues")
            
            exit(1)
    
    except FileNotFoundError:
        click.echo(f"❌ Notebook not found: {notebook}", err=True)
        exit(1)
    except Exception as e:
        click.echo(f"❌ Validation error: {str(e)}", err=True)
        exit(1)

@cli.command()
@click.option("--action", "-a", required=True, 
              type=click.Choice(["start", "stop", "restart", "status", "logs"]),
              help="Container action")
@click.option("--service", "-s", default="notebook-sandbox", help="Service name")
@click.option("--tail", default=100, help="Number of log lines to show")
def container(action: str, service: str, tail: int):
    """Manage Docker containers."""
    
    async def _container():
        manager = ContainerManager()
        
        try:
            if action == "start":
                success = await manager.start_container(service)
                if success:
                    click.echo(f"✅ Container '{service}' started successfully")
                else:
                    click.echo(f"❌ Failed to start container '{service}'", err=True)
                    exit(1)
            
            elif action == "stop":
                success = await manager.stop_container(service)
                if success:
                    click.echo(f"✅ Container '{service}' stopped successfully")
                else:
                    click.echo(f"❌ Failed to stop container '{service}'", err=True)
                    exit(1)
            
            elif action == "restart":
                success = await manager.restart_container(service)
                if success:
                    click.echo(f"✅ Container '{service}' restarted successfully")
                else:
                    click.echo(f"❌ Failed to restart container '{service}'", err=True)
                    exit(1)
            
            elif action == "status":
                status = await manager.get_container_status(service)
                click.echo(json.dumps(status, indent=2))
                
                if status.get("running"):
                    click.echo(f"✅ Container '{service}' is running")
                else:
                    click.echo(f"❌ Container '{service}' is not running")
            
            elif action == "logs":
                logs = await manager.get_container_logs(service, tail=tail)
                click.echo(f"📋 Last {tail} lines from '{service}':")
                click.echo("-" * 50)
                click.echo(logs)
        
        except Exception as e:
            click.echo(f"❌ Container operation failed: {str(e)}", err=True)
            exit(1)
    
    asyncio.run(_container())

@cli.command()
@click.option("--resolver-type", "-t", required=True,
              type=click.Choice(["mock", "wrapper", "mcp"]),
              help="Tool resolver type")
@click.option("--url", "-u", help="Service URL (for wrapper/mcp)")
@click.option("--query", "-q", help="Test query for tool resolution")
def test_resolver(resolver_type: str, url: Optional[str], query: Optional[str]):
    """Test tool resolver connectivity and functionality."""
    
    async def _test():
        try:
            # Initialize resolver
            if resolver_type == "mock":
                resolver = MockToolResolver()
            elif resolver_type == "wrapper":
                if not url:
                    click.echo("❌ URL required for wrapper resolver", err=True)
                    exit(1)
                resolver = WrapperClient(url)
            elif resolver_type == "mcp":
                if not url:
                    click.echo("❌ URL required for MCP resolver", err=True)
                    exit(1)
                resolver = MCPClient(url)
            
            # Test health
            click.echo(f"🔍 Testing {resolver_type} resolver...")
            health = await resolver.health_check()
            click.echo(f"Health: {json.dumps(health, indent=2)}")
            
            if health.get("status") != "healthy":
                click.echo(f"❌ Resolver is not healthy", err=True)
                exit(1)
            
            # List tools
            click.echo("\n📋 Available tools:")
            tools = await resolver.list_tools(limit=5)
            
            for tool in tools:
                click.echo(f"   - {tool.name} ({tool.tool_type}): {tool.description[:60]}...")
            
            # Test tool resolution if query provided
            if query:
                click.echo(f"\n🔍 Resolving tools for: '{query}'")
                result = await resolver.resolve_tools(query, limit=3, threshold=0.1)
                
                click.echo(f"Found {len(result.tools)} tools in {result.search_time:.3f}s:")
                for tool in result.tools:
                    click.echo(f"   - {tool.name} (confidence: {tool.confidence_score:.2f})")
            
            click.echo("\n✅ Resolver test completed successfully")
        
        except Exception as e:
            click.echo(f"❌ Resolver test failed: {str(e)}", err=True)
            exit(1)
    
    asyncio.run(_test())

@cli.command()
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=8888, help="Server port")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def server(host: str, port: int, reload: bool):
    """Start the notebook sandbox API server."""
    
    try:
        import uvicorn
        from .core.api_server import app
        
        click.echo(f"🚀 Starting Notebook Sandbox API server on {host}:{port}")
        click.echo(f"📖 API documentation: http://{host}:{port}/docs")
        
        uvicorn.run(
            "notebook_sandbox.core.api_server:app" if reload else app,
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    
    except ImportError:
        click.echo("❌ uvicorn not available. Install with: pip install uvicorn", err=True)
        exit(1)
    except Exception as e:
        click.echo(f"❌ Server startup failed: {str(e)}", err=True)
        exit(1)

def main():
    """Main CLI entry point."""
    cli()

if __name__ == "__main__":
    main()