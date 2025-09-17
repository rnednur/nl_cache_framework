#!/usr/bin/env python3
"""
Sample Workflow Creation Script for ThinkForge

This script creates sample workflows in the database to demonstrate
the workflow execution capabilities. These can be used for testing
the execution engine and CLI runner.
"""

import json
import sys
import os
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from thinkforge.models import Text2SQLCache, TemplateType, Status
from thinkforge.controller import Text2SQLController


def create_sample_workflows():
    """Create sample workflows for testing and demonstration."""
    db = SessionLocal()
    controller = Text2SQLController(db)
    
    workflows = []
    
    try:
        # 1. Simple API Data Fetch Workflow
        api_workflow = {
            "name": "API Data Fetch Workflow",
            "type": "fullflow",
            "version": "1.0",
            "steps": {
                "step_1": {
                    "id": "step_1",
                    "templateType": "api",
                    "inputs": {
                        "template": json.dumps({
                            "url": "https://api.github.com/users/{username}",
                            "method": "GET",
                            "headers": {"Accept": "application/json"}
                        })
                    },
                    "dependencies": [],
                    "outputKey": "user_data"
                },
                "step_2": {
                    "id": "step_2", 
                    "templateType": "function",
                    "inputs": {
                        "template": '''
def execute(inputs):
    user_data = inputs.get("user_data", {})
    if isinstance(user_data, dict) and "data" in user_data:
        data = user_data["data"]
        return {
            "name": data.get("name", "Unknown"),
            "public_repos": data.get("public_repos", 0),
            "followers": data.get("followers", 0),
            "formatted": f"User: {data.get('name', 'Unknown')} ({data.get('public_repos', 0)} repos, {data.get('followers', 0)} followers)"
        }
    return {"error": "Invalid user data format"}
'''
                    },
                    "dependencies": ["step_1"],
                    "outputKey": "formatted_data"
                }
            },
            "executionPlan": [
                {"mode": "sequential", "steps": ["step_1"]},
                {"mode": "sequential", "steps": ["step_2"]}
            ]
        }
        
        workflow_id_1 = controller.add_query(
            nl_query="Fetch GitHub user data and format it",
            template=json.dumps(api_workflow),
            template_type=TemplateType.WORKFLOW,
            reasoning_trace="This workflow fetches user data from GitHub API and formats it for display",
            is_template=False,
            catalog_type="demo",
            catalog_subtype="api_workflow",
            catalog_name="github_user_fetch",
            status="active"
        )
        
        workflows.append({
            "id": workflow_id_1["id"],
            "name": "GitHub User Data Fetch",
            "description": "Fetches and formats GitHub user data",
            "type": "API + Processing"
        })
        
        # 2. Database Query and Processing Workflow
        db_workflow = {
            "name": "Database Query Workflow", 
            "type": "fullflow",
            "version": "1.0",
            "steps": {
                "step_1": {
                    "id": "step_1",
                    "templateType": "sql",
                    "inputs": {
                        "template": "SELECT id, nl_query, template_type, created_at FROM text2sql_cache WHERE template_type = 'api' LIMIT {limit}"
                    },
                    "dependencies": [],
                    "outputKey": "query_results"
                },
                "step_2": {
                    "id": "step_2",
                    "templateType": "function", 
                    "inputs": {
                        "template": '''
def execute(inputs):
    query_results = inputs.get("query_results", {})
    if isinstance(query_results, dict) and "rows" in query_results:
        rows = query_results["rows"]
        summary = {
            "total_entries": len(rows),
            "entries": [{"id": row["id"], "query": row["nl_query"][:50] + "..." if len(row["nl_query"]) > 50 else row["nl_query"]} for row in rows],
            "message": f"Processed {len(rows)} database entries"
        }
        return summary
    return {"error": "Invalid query results format"}
'''
                    },
                    "dependencies": ["step_1"],
                    "outputKey": "processed_results"
                }
            },
            "executionPlan": [
                {"mode": "sequential", "steps": ["step_1"]},
                {"mode": "sequential", "steps": ["step_2"]}
            ]
        }
        
        workflow_id_2 = controller.add_query(
            nl_query="Query database and process results",
            template=json.dumps(db_workflow),
            template_type=TemplateType.WORKFLOW,
            reasoning_trace="This workflow queries the database for API entries and processes the results",
            is_template=False,
            catalog_type="demo",
            catalog_subtype="db_workflow",
            catalog_name="db_query_process",
            status="active"
        )
        
        workflows.append({
            "id": workflow_id_2["id"],
            "name": "Database Query & Process",
            "description": "Queries database and processes results",
            "type": "SQL + Processing"
        })
        
        # 3. Multi-step Data Pipeline
        pipeline_workflow = {
            "name": "Data Pipeline Workflow",
            "type": "fullflow", 
            "version": "1.0",
            "steps": {
                "step_1": {
                    "id": "step_1",
                    "templateType": "function",
                    "inputs": {
                        "template": '''
def execute(inputs):
    # Simulate data generation
    import datetime
    data = []
    for i in range(5):
        data.append({
            "id": i + 1,
            "name": f"Item {i + 1}",
            "value": (i + 1) * 10,
            "timestamp": datetime.datetime.now().isoformat()
        })
    return {"generated_data": data, "count": len(data)}
'''
                    },
                    "dependencies": [],
                    "outputKey": "raw_data"
                },
                "step_2": {
                    "id": "step_2",
                    "templateType": "function",
                    "inputs": {
                        "template": '''
def execute(inputs):
    raw_data = inputs.get("raw_data", {})
    if "generated_data" in raw_data:
        data = raw_data["generated_data"]
        # Filter and transform data
        filtered_data = [item for item in data if item["value"] > 20]
        for item in filtered_data:
            item["processed"] = True
            item["category"] = "high" if item["value"] > 30 else "medium"
        return {"filtered_data": filtered_data, "original_count": len(data), "filtered_count": len(filtered_data)}
    return {"error": "No data to filter"}
'''
                    },
                    "dependencies": ["step_1"],
                    "outputKey": "filtered_data"
                },
                "step_3": {
                    "id": "step_3",
                    "templateType": "function",
                    "inputs": {
                        "template": '''
def execute(inputs):
    filtered_data = inputs.get("filtered_data", {})
    if "filtered_data" in filtered_data:
        data = filtered_data["filtered_data"]
        # Generate summary statistics
        total_value = sum(item["value"] for item in data)
        avg_value = total_value / len(data) if data else 0
        categories = {}
        for item in data:
            cat = item.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
        
        summary = {
            "total_items": len(data),
            "total_value": total_value,
            "average_value": round(avg_value, 2),
            "categories": categories,
            "summary": f"Processed {len(data)} items with total value {total_value} (avg: {avg_value:.2f})"
        }
        return summary
    return {"error": "No filtered data available"}
'''
                    },
                    "dependencies": ["step_2"],
                    "outputKey": "summary_stats"
                }
            },
            "executionPlan": [
                {"mode": "sequential", "steps": ["step_1"]},
                {"mode": "sequential", "steps": ["step_2"]}, 
                {"mode": "sequential", "steps": ["step_3"]}
            ]
        }
        
        workflow_id_3 = controller.add_query(
            nl_query="Generate, filter, and summarize data in a pipeline",
            template=json.dumps(pipeline_workflow),
            template_type=TemplateType.WORKFLOW,
            reasoning_trace="This workflow demonstrates a multi-step data pipeline with generation, filtering, and summarization",
            is_template=False,
            catalog_type="demo",
            catalog_subtype="pipeline_workflow", 
            catalog_name="data_pipeline",
            status="active"
        )
        
        workflows.append({
            "id": workflow_id_3["id"],
            "name": "Data Pipeline Demo",
            "description": "Multi-step data generation, filtering, and analysis",
            "type": "Data Pipeline"
        })
        
        # 4. Parallel Processing Workflow
        parallel_workflow = {
            "name": "Parallel Processing Workflow",
            "type": "fullflow",
            "version": "1.0", 
            "steps": {
                "step_1": {
                    "id": "step_1",
                    "templateType": "function",
                    "inputs": {
                        "template": '''
def execute(inputs):
    import time
    time.sleep(1)  # Simulate processing time
    return {"task": "A", "result": "Task A completed", "duration": 1}
'''
                    },
                    "dependencies": [],
                    "outputKey": "task_a_result"
                },
                "step_2": {
                    "id": "step_2",
                    "templateType": "function",
                    "inputs": {
                        "template": '''
def execute(inputs):
    import time
    time.sleep(1)  # Simulate processing time
    return {"task": "B", "result": "Task B completed", "duration": 1}
'''
                    },
                    "dependencies": [],
                    "outputKey": "task_b_result"
                },
                "step_3": {
                    "id": "step_3",
                    "templateType": "function",
                    "inputs": {
                        "template": '''
def execute(inputs):
    task_a = inputs.get("task_a_result", {})
    task_b = inputs.get("task_b_result", {})
    
    results = []
    if task_a:
        results.append(task_a)
    if task_b:
        results.append(task_b)
    
    return {
        "combined_results": results,
        "summary": f"Combined {len(results)} parallel task results",
        "tasks_completed": [r.get("task", "unknown") for r in results]
    }
'''
                    },
                    "dependencies": ["step_1", "step_2"],
                    "outputKey": "combined_results"
                }
            },
            "executionPlan": [
                {"mode": "parallel", "steps": ["step_1", "step_2"]},
                {"mode": "sequential", "steps": ["step_3"]}
            ]
        }
        
        workflow_id_4 = controller.add_query(
            nl_query="Execute tasks in parallel and combine results",
            template=json.dumps(parallel_workflow),
            template_type=TemplateType.WORKFLOW,
            reasoning_trace="This workflow demonstrates parallel task execution followed by result combination",
            is_template=False,
            catalog_type="demo",
            catalog_subtype="parallel_workflow",
            catalog_name="parallel_tasks",
            status="active"
        )
        
        workflows.append({
            "id": workflow_id_4["id"],
            "name": "Parallel Tasks Demo", 
            "description": "Demonstrates parallel task execution",
            "type": "Parallel Processing"
        })
        
        print("✅ Sample workflows created successfully!")
        print(f"\nCreated {len(workflows)} workflows:")
        print("-" * 60)
        
        for wf in workflows:
            print(f"ID: {wf['id']:<6} | {wf['name']:<25} | {wf['type']}")
            print(f"       Description: {wf['description']}")
            print()
        
        print("You can now test these workflows using:")
        print("  python workflow_runner.py --list")
        print("  python workflow_runner.py --workflow-id <ID>")
        print("  python workflow_runner.py --workflow-id <ID> --interactive")
        
        db.commit()
        return workflows
        
    except Exception as e:
        print(f"❌ Error creating sample workflows: {e}")
        db.rollback()
        return []
    finally:
        db.close()


if __name__ == "__main__":
    print("Creating sample workflows for ThinkForge...")
    print("=" * 50)
    
    workflows = create_sample_workflows()
    
    if workflows:
        print(f"\n🎉 Successfully created {len(workflows)} sample workflows!")
        print("\nNext steps:")
        print("1. List workflows: python workflow_runner.py --list")
        print("2. Run a workflow: python workflow_runner.py --workflow-id <ID>")
        print("3. Use the API endpoints to execute workflows programmatically")
    else:
        print("\n❌ Failed to create sample workflows.")
        sys.exit(1)