#!/usr/bin/env python3
"""
Standalone Workflow Runner for ThinkForge

This module provides a command-line interface for executing workflows
directly from cache entries, supporting both interactive and batch execution modes.

Usage:
    python workflow_runner.py --workflow-id 123 --input '{"key": "value"}'
    python workflow_runner.py --workflow-name "My Workflow" --interactive
    python workflow_runner.py --list-workflows
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import database and ThinkForge components
from database import SessionLocal
from thinkforge.execution_engine import WorkflowExecutor, ExecutionStatus
from thinkforge.tool_invoker import ToolInvoker
from thinkforge.models import Text2SQLCache

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkflowRunner:
    """Standalone workflow runner with CLI interface."""

    def __init__(self, db_session=None):
        """Initialize the workflow runner."""
        self.db_session = db_session or SessionLocal()
        self.tool_invoker = ToolInvoker(self.db_session)
        self.executor = WorkflowExecutor(self.db_session, self.tool_invoker)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.tool_invoker.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.tool_invoker.__aexit__(exc_type, exc_val, exc_tb)
        if hasattr(self, 'db_session'):
            self.db_session.close()

    def list_workflows(self) -> None:
        """List all available workflows."""
        try:
            workflows = self.db_session.query(Text2SQLCache).filter(
                Text2SQLCache.template_type.in_(['workflow', 'recipe', 'recipe_template']),
                Text2SQLCache.status == 'active'
            ).all()

            if not workflows:
                print("No workflows found.")
                return

            print(f"\n{'ID':<6} {'Type':<15} {'Name':<50} {'Created':<12}")
            print("-" * 85)

            for workflow in workflows:
                created_date = workflow.created_at.strftime('%Y-%m-%d') if workflow.created_at else 'Unknown'
                name = workflow.nl_query[:47] + "..." if len(workflow.nl_query) > 50 else workflow.nl_query
                print(f"{workflow.id:<6} {workflow.template_type:<15} {name:<50} {created_date:<12}")

            print(f"\nTotal: {len(workflows)} workflows")

        except Exception as e:
            logger.error(f"Error listing workflows: {e}")
            sys.exit(1)

    def get_workflow_by_id(self, workflow_id: int) -> Optional[Text2SQLCache]:
        """Get workflow by ID."""
        try:
            workflow = self.db_session.query(Text2SQLCache).filter_by(id=workflow_id).first()
            if not workflow:
                logger.error(f"Workflow with ID {workflow_id} not found")
                return None

            if workflow.template_type not in ['workflow', 'recipe', 'recipe_template']:
                logger.error(f"Cache entry {workflow_id} is not a workflow (type: {workflow.template_type})")
                return None

            return workflow
        except Exception as e:
            logger.error(f"Error getting workflow {workflow_id}: {e}")
            return None

    def get_workflow_by_name(self, workflow_name: str) -> Optional[Text2SQLCache]:
        """Get workflow by name (nl_query field)."""
        try:
            workflow = self.db_session.query(Text2SQLCache).filter(
                Text2SQLCache.nl_query.ilike(f"%{workflow_name}%"),
                Text2SQLCache.template_type.in_(['workflow', 'recipe', 'recipe_template']),
                Text2SQLCache.status == 'active'
            ).first()

            if not workflow:
                logger.error(f"Workflow with name containing '{workflow_name}' not found")
                return None

            return workflow
        except Exception as e:
            logger.error(f"Error getting workflow by name '{workflow_name}': {e}")
            return None

    async def run_workflow(
        self,
        workflow_id: int,
        input_variables: Optional[Dict[str, Any]] = None,
        interactive: bool = False
    ) -> None:
        """Run a workflow with optional input variables."""
        try:
            # Get workflow
            workflow = self.get_workflow_by_id(workflow_id)
            if not workflow:
                return

            print(f"\n{'='*60}")
            print(f"Executing Workflow: {workflow.nl_query}")
            print(f"ID: {workflow.id}")
            print(f"Type: {workflow.template_type}")
            print(f"{'='*60}")

            # Interactive input collection
            if interactive:
                input_variables = self.collect_interactive_input(workflow, input_variables)

            # Display input variables
            if input_variables:
                print(f"\nInput Variables:")
                for key, value in input_variables.items():
                    print(f"  {key}: {value}")

            # Set up progress callback
            async def progress_callback(status_dict: Dict[str, Any]):
                await self.display_progress(status_dict)

            print(f"\nStarting execution at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 60)

            # Execute workflow
            context = await self.executor.execute_workflow(
                workflow_id=workflow_id,
                input_variables=input_variables or {},
                progress_callback=progress_callback
            )

            # Display final results
            await self.display_final_results(context)

        except KeyboardInterrupt:
            print("\n\nExecution interrupted by user.")
            logger.info("Workflow execution interrupted")
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            print(f"\nExecution failed: {e}")

    def collect_interactive_input(
        self,
        workflow: Text2SQLCache,
        initial_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Collect input variables interactively from the user."""
        input_variables = initial_input or {}

        print(f"\nInteractive Input Collection")
        print("Enter input variables for the workflow.")
        print("Press Enter with empty value to finish.\n")

        while True:
            try:
                key = input("Variable name: ").strip()
                if not key:
                    break

                value = input(f"Value for '{key}': ").strip()
                if not value:
                    continue

                # Try to parse as JSON, fallback to string
                try:
                    parsed_value = json.loads(value)
                    input_variables[key] = parsed_value
                except json.JSONDecodeError:
                    input_variables[key] = value

                print(f"Added: {key} = {input_variables[key]}\n")

            except KeyboardInterrupt:
                print("\nInput collection interrupted.")
                break

        return input_variables

    async def display_progress(self, status_dict: Dict[str, Any]) -> None:
        """Display workflow execution progress."""
        status = status_dict.get("status", "unknown")
        current_step = status_dict.get("current_step")
        progress = status_dict.get("progress", {})
        
        completed = progress.get("completed", 0)
        total = progress.get("total", 0)
        percentage = progress.get("percentage", 0)

        # Display progress bar
        bar_length = 40
        filled_length = int(bar_length * percentage / 100) if percentage > 0 else 0
        bar = "█" * filled_length + "░" * (bar_length - filled_length)

        status_line = f"[{bar}] {percentage:.1f}% ({completed}/{total})"
        
        if current_step:
            status_line += f" - Current: {current_step}"
        
        # Use carriage return to overwrite the same line
        print(f"\r{status_line}", end="", flush=True)
        
        # Print newline on completion or error
        if status in ['completed', 'failed', 'cancelled']:
            print()

    async def display_final_results(self, context) -> None:
        """Display final execution results."""
        print(f"\n{'='*60}")
        print("EXECUTION RESULTS")
        print(f"{'='*60}")

        print(f"Status: {context.status.value.upper()}")
        print(f"Run ID: {context.run_id}")
        
        if context.started_at:
            print(f"Started: {context.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if context.completed_at:
            print(f"Completed: {context.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if context.started_at:
                duration = context.completed_at - context.started_at
                print(f"Duration: {duration.total_seconds():.2f} seconds")

        if context.error_message:
            print(f"Error: {context.error_message}")

        # Display step results
        print(f"\nSTEP RESULTS:")
        print("-" * 40)

        for step_id, result in context.step_results.items():
            status_icon = {
                'completed': '✓',
                'failed': '✗',
                'running': '⟳',
                'pending': '○',
                'skipped': '⊝'
            }.get(result.status.value, '?')

            print(f"{status_icon} {step_id}: {result.status.value}")
            
            if result.duration_ms:
                print(f"    Duration: {result.duration_ms}ms")
            
            if result.error:
                print(f"    Error: {result.error}")
            elif result.output and isinstance(result.output, dict):
                # Display key information from output
                if 'status' in result.output:
                    print(f"    Status: {result.output['status']}")
                if 'message' in result.output:
                    print(f"    Message: {result.output['message']}")

        # Display step outputs if any
        if context.step_outputs:
            print(f"\nSTEP OUTPUTS:")
            print("-" * 40)
            for key, value in context.step_outputs.items():
                if isinstance(value, (dict, list)):
                    print(f"{key}: {type(value).__name__} ({len(value)} items)")
                else:
                    value_str = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                    print(f"{key}: {value_str}")


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ThinkForge Workflow Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python workflow_runner.py --list
  python workflow_runner.py --workflow-id 123
  python workflow_runner.py --workflow-id 123 --input '{"param": "value"}'
  python workflow_runner.py --workflow-name "Data Processing" --interactive
        """
    )

    # Add arguments
    parser.add_argument(
        "--list", "--list-workflows",
        action="store_true",
        help="List all available workflows"
    )
    parser.add_argument(
        "--workflow-id", "-i",
        type=int,
        help="ID of the workflow to execute"
    )
    parser.add_argument(
        "--workflow-name", "-n",
        type=str,
        help="Name (or partial name) of the workflow to execute"
    )
    parser.add_argument(
        "--input", "-p",
        type=str,
        help="JSON string of input variables for the workflow"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Collect input variables interactively"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create runner
    async with WorkflowRunner() as runner:
        # List workflows
        if args.list:
            runner.list_workflows()
            return

        # Determine workflow to execute
        workflow_id = args.workflow_id
        if args.workflow_name and not workflow_id:
            workflow = runner.get_workflow_by_name(args.workflow_name)
            if workflow:
                workflow_id = workflow.id

        if not workflow_id:
            if not args.list:
                print("Error: Must specify either --workflow-id or --workflow-name")
                print("Use --list to see available workflows")
            return

        # Parse input variables
        input_variables = None
        if args.input:
            try:
                input_variables = json.loads(args.input)
                if not isinstance(input_variables, dict):
                    print("Error: Input must be a JSON object")
                    return
            except json.JSONDecodeError as e:
                print(f"Error parsing input JSON: {e}")
                return

        # Execute workflow
        await runner.run_workflow(
            workflow_id=workflow_id,
            input_variables=input_variables,
            interactive=args.interactive
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)