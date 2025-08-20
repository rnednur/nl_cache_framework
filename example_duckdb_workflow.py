#!/usr/bin/env python3
"""
Example: DuckDB-Powered Data Analytics Workflow

This example demonstrates the powerful data analytics capabilities enabled by
DuckDB integration in ThinkForge workflows. It shows:

1. Customer data extraction and processing
2. Sales analytics with SQL transformations
3. LLM-powered insights generation
4. Cross-step data persistence and querying
5. Complex analytical workflows with multiple data sources

Run with: python example_duckdb_workflow.py
"""

import asyncio
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any

# Sample data for demonstration
SAMPLE_CUSTOMERS = [
    {"customer_id": 1, "name": "Acme Corp", "tier": "enterprise", "region": "north", "signup_date": "2023-01-15"},
    {"customer_id": 2, "name": "TechStart Inc", "tier": "startup", "region": "west", "signup_date": "2023-03-22"},
    {"customer_id": 3, "name": "Global Solutions", "tier": "enterprise", "region": "east", "signup_date": "2022-11-08"},
    {"customer_id": 4, "name": "Local Business", "tier": "small", "region": "south", "signup_date": "2023-05-10"},
    {"customer_id": 5, "name": "MidSize Co", "tier": "medium", "region": "west", "signup_date": "2023-02-28"}
]

SAMPLE_SALES = [
    {"sale_id": 1, "customer_id": 1, "amount": 25000, "product": "Enterprise Plan", "date": "2023-06-01"},
    {"sale_id": 2, "customer_id": 1, "amount": 15000, "product": "Add-on Services", "date": "2023-06-15"},
    {"sale_id": 3, "customer_id": 2, "amount": 5000, "product": "Startup Plan", "date": "2023-06-02"},
    {"sale_id": 4, "customer_id": 3, "amount": 35000, "product": "Enterprise Plan", "date": "2023-06-03"},
    {"sale_id": 5, "customer_id": 3, "amount": 8000, "product": "Professional Services", "date": "2023-06-10"},
    {"sale_id": 6, "customer_id": 4, "amount": 2000, "product": "Basic Plan", "date": "2023-06-05"},
    {"sale_id": 7, "customer_id": 5, "amount": 12000, "product": "Growth Plan", "date": "2023-06-07"},
    {"sale_id": 8, "customer_id": 2, "amount": 3000, "product": "Support Package", "date": "2023-06-20"}
]

SAMPLE_SUPPORT_TICKETS = [
    {"ticket_id": 1, "customer_id": 1, "priority": "high", "category": "technical", "status": "resolved", "created": "2023-06-01"},
    {"ticket_id": 2, "customer_id": 2, "priority": "medium", "category": "billing", "status": "open", "created": "2023-06-05"},
    {"ticket_id": 3, "customer_id": 3, "priority": "low", "category": "feature_request", "status": "closed", "created": "2023-06-03"},
    {"ticket_id": 4, "customer_id": 1, "priority": "critical", "category": "technical", "status": "open", "created": "2023-06-10"},
    {"ticket_id": 5, "customer_id": 4, "priority": "medium", "category": "account", "status": "resolved", "created": "2023-06-08"}
]

# Comprehensive workflow configuration with DuckDB SQL steps
CUSTOMER_ANALYTICS_WORKFLOW = {
    "name": "Customer Analytics with DuckDB",
    "description": "Comprehensive customer analytics workflow using DuckDB for data transformations",
    "steps": {
        "load_customers": {
            "id": "load_customers",
            "templateType": "function",
            "inputs": {
                "template": "return SAMPLE_CUSTOMERS",
                "code": """
def load_customer_data():
    # In real scenario, this would load from database/API
    return SAMPLE_CUSTOMERS
                """,
                "language": "python"
            },
            "dependencies": [],
            "outputKey": "customers_data",
            "metadata": {
                "label": "Load Customer Data",
                "description": "Load customer information from data source"
            }
        },
        "load_sales": {
            "id": "load_sales",
            "templateType": "function",
            "inputs": {
                "template": "return SAMPLE_SALES",
                "code": """
def load_sales_data():
    # In real scenario, this would load from database/API
    return SAMPLE_SALES
                """,
                "language": "python"
            },
            "dependencies": [],
            "outputKey": "sales_data",
            "metadata": {
                "label": "Load Sales Data",
                "description": "Load sales transaction data"
            }
        },
        "load_support": {
            "id": "load_support",
            "templateType": "function",
            "inputs": {
                "template": "return SAMPLE_SUPPORT_TICKETS",
                "code": """
def load_support_data():
    # In real scenario, this would load from database/API
    return SAMPLE_SUPPORT_TICKETS
                """,
                "language": "python"
            },
            "dependencies": [],
            "outputKey": "support_data",
            "metadata": {
                "label": "Load Support Data",
                "description": "Load customer support ticket data"
            }
        },
        "customer_sales_analysis": {
            "id": "customer_sales_analysis",
            "templateType": "duckdb_sql",
            "inputs": {
                "query": """
                    SELECT 
                        c.customer_id,
                        c.name as customer_name,
                        c.tier,
                        c.region,
                        c.signup_date,
                        COUNT(s.sale_id) as total_sales,
                        SUM(s.amount) as total_revenue,
                        AVG(s.amount) as avg_sale_amount,
                        MAX(s.amount) as max_sale_amount,
                        MIN(s.date) as first_sale_date,
                        MAX(s.date) as last_sale_date
                    FROM {table:load_customers} c
                    LEFT JOIN {table:load_sales} s ON c.customer_id = s.customer_id
                    GROUP BY c.customer_id, c.name, c.tier, c.region, c.signup_date
                    ORDER BY total_revenue DESC NULLS LAST
                """,
                "validation": {
                    "row_count_min": 1,
                    "required_columns": ["customer_id", "customer_name", "total_revenue"]
                }
            },
            "dependencies": ["load_customers", "load_sales"],
            "outputKey": "customer_sales_summary",
            "metadata": {
                "label": "Customer Sales Analysis",
                "description": "Analyze sales performance by customer with SQL"
            }
        },
        "regional_performance": {
            "id": "regional_performance",
            "templateType": "duckdb_sql",
            "inputs": {
                "query": """
                    SELECT 
                        region,
                        COUNT(DISTINCT customer_id) as customer_count,
                        SUM(total_revenue) as region_revenue,
                        AVG(total_revenue) as avg_customer_revenue,
                        COUNT(CASE WHEN tier = 'enterprise' THEN 1 END) as enterprise_customers,
                        COUNT(CASE WHEN tier = 'startup' THEN 1 END) as startup_customers,
                        COUNT(CASE WHEN tier = 'medium' THEN 1 END) as medium_customers,
                        COUNT(CASE WHEN tier = 'small' THEN 1 END) as small_customers
                    FROM {table:customer_sales_analysis}
                    GROUP BY region
                    ORDER BY region_revenue DESC
                """,
                "validation": {
                    "row_count_min": 1,
                    "required_columns": ["region", "region_revenue"]
                }
            },
            "dependencies": ["customer_sales_analysis"],
            "outputKey": "regional_analysis",
            "metadata": {
                "label": "Regional Performance Analysis",
                "description": "Analyze performance by geographic region"
            }
        },
        "support_metrics": {
            "id": "support_metrics",
            "templateType": "duckdb_sql",
            "inputs": {
                "query": """
                    SELECT 
                        c.customer_id,
                        c.customer_name,
                        c.tier,
                        c.total_revenue,
                        COUNT(t.ticket_id) as ticket_count,
                        COUNT(CASE WHEN t.priority = 'critical' THEN 1 END) as critical_tickets,
                        COUNT(CASE WHEN t.priority = 'high' THEN 1 END) as high_tickets,
                        COUNT(CASE WHEN t.status = 'open' THEN 1 END) as open_tickets,
                        ROUND(c.total_revenue / NULLIF(COUNT(t.ticket_id), 0), 2) as revenue_per_ticket
                    FROM {table:customer_sales_analysis} c
                    LEFT JOIN {table:load_support} t ON c.customer_id = t.customer_id
                    GROUP BY c.customer_id, c.customer_name, c.tier, c.total_revenue
                    ORDER BY ticket_count DESC NULLS LAST
                """,
                "validation": {
                    "row_count_min": 1,
                    "required_columns": ["customer_id", "ticket_count"]
                }
            },
            "dependencies": ["customer_sales_analysis", "load_support"],
            "outputKey": "support_analysis",
            "metadata": {
                "label": "Support Metrics Analysis",
                "description": "Analyze customer support patterns and metrics"
            }
        },
        "tier_comparison": {
            "id": "tier_comparison",
            "templateType": "duckdb_sql",
            "inputs": {
                "query": """
                    SELECT 
                        tier,
                        COUNT(*) as customer_count,
                        SUM(total_revenue) as tier_revenue,
                        AVG(total_revenue) as avg_revenue_per_customer,
                        MEDIAN(total_revenue) as median_revenue,
                        SUM(total_sales) as total_transactions,
                        AVG(avg_sale_amount) as avg_transaction_size,
                        ROUND(SUM(total_revenue) * 100.0 / SUM(SUM(total_revenue)) OVER (), 2) as revenue_percentage
                    FROM {table:customer_sales_analysis}
                    WHERE total_revenue > 0
                    GROUP BY tier
                    ORDER BY tier_revenue DESC
                """,
                "validation": {
                    "row_count_min": 1,
                    "required_columns": ["tier", "tier_revenue"]
                }
            },
            "dependencies": ["customer_sales_analysis"],
            "outputKey": "tier_analysis",
            "metadata": {
                "label": "Customer Tier Comparison",
                "description": "Compare performance across customer tiers"
            }
        },
        "generate_insights": {
            "id": "generate_insights",
            "templateType": "llm_step",
            "inputs": {
                "prompt_template": """Analyze this customer analytics data and provide strategic insights:

REGIONAL PERFORMANCE:
{regional_data}

CUSTOMER TIER ANALYSIS:
{tier_data}

SUPPORT METRICS SUMMARY:
{support_data}

Provide a comprehensive analysis including:
1. Key performance trends
2. Regional opportunities
3. Customer tier insights
4. Support quality indicators
5. Strategic recommendations

Format as JSON with sections: trends, opportunities, insights, recommendations""",
                "input_parameters": ["regional_data", "tier_data", "support_data"],
                "output_format": "json",
                "expected_output": {
                    "trends": "string",
                    "opportunities": "string", 
                    "insights": "string",
                    "recommendations": "string"
                },
                "model": "google/gemini-pro",
                "temperature": 0.3,
                "max_tokens": 1000,
                "system_prompt": "You are a senior business analyst specializing in customer analytics and strategic insights."
            },
            "dependencies": ["regional_performance", "tier_comparison", "support_metrics"],
            "outputKey": "strategic_insights",
            "metadata": {
                "label": "Generate Strategic Insights",
                "description": "Use AI to generate strategic insights from analytics data"
            }
        },
        "executive_summary": {
            "id": "executive_summary",
            "templateType": "duckdb_sql",
            "inputs": {
                "query": """
                    SELECT 
                        'Executive Summary' as report_section,
                        COUNT(DISTINCT customer_id) as total_customers,
                        SUM(total_revenue) as total_revenue,
                        AVG(total_revenue) as avg_customer_value,
                        COUNT(DISTINCT region) as regions_served,
                        SUM(total_sales) as total_transactions,
                        ROUND(SUM(total_revenue) / SUM(total_sales), 2) as avg_transaction_size,
                        MAX(total_revenue) as top_customer_revenue,
                        COUNT(CASE WHEN tier = 'enterprise' THEN 1 END) as enterprise_count
                    FROM {table:customer_sales_analysis}
                    WHERE total_revenue > 0
                """,
                "validation": {
                    "row_count_min": 1,
                    "required_columns": ["total_customers", "total_revenue"]
                }
            },
            "dependencies": ["customer_sales_analysis"],
            "outputKey": "executive_summary",
            "metadata": {
                "label": "Executive Summary",
                "description": "Generate high-level executive summary metrics"
            }
        }
    },
    "executionPlan": [
        {
            "mode": "parallel",
            "steps": ["load_customers", "load_sales", "load_support"]
        },
        {
            "mode": "sequential",
            "steps": ["customer_sales_analysis"]
        },
        {
            "mode": "parallel",
            "steps": ["regional_performance", "support_metrics", "tier_comparison", "executive_summary"]
        },
        {
            "mode": "sequential",
            "steps": ["generate_insights"]
        }
    ]
}

def demonstrate_duckdb_integration():
    """Demonstrate DuckDB integration features."""
    print("🚀 DuckDB Workflow Integration Demo")
    print("=" * 50)
    
    try:
        # Import required modules
        from thinkforge.workflow_datastore import WorkflowDataStore, get_workflow_datastore
        from thinkforge.execution_engine import ExecutionContext, ExecutionStatus
        from thinkforge.step_templates import StepTemplateFactory, DuckDBStepTemplate
        from thinkforge.execution_config import ExecutionConfigManager, DuckDBConfig
        
        print("✅ Successfully imported DuckDB integration modules")
        
        # 1. Demonstrate WorkflowDataStore
        print("\n📊 Creating Workflow DataStore...")
        
        with WorkflowDataStore("demo_workflow", "run_001") as datastore:
            print(f"   Database initialized: {datastore._database_path}")
            
            # Store sample data
            print("\n📋 Storing Sample Data...")
            customers_table = datastore.store_step_output(
                step_id="load_customers",
                data=SAMPLE_CUSTOMERS,
                template_type="function",
                metadata={"source": "demo_data"}
            )
            
            sales_table = datastore.store_step_output(
                step_id="load_sales", 
                data=SAMPLE_SALES,
                template_type="function",
                metadata={"source": "demo_data"}
            )
            
            support_table = datastore.store_step_output(
                step_id="load_support",
                data=SAMPLE_SUPPORT_TICKETS, 
                template_type="function",
                metadata={"source": "demo_data"}
            )
            
            print(f"   Customers stored in: {customers_table}")
            print(f"   Sales stored in: {sales_table}")
            print(f"   Support stored in: {support_table}")
            
            # 2. Demonstrate SQL analytics
            print("\n🔍 Executing SQL Analytics...")
            
            # Customer sales analysis
            sales_analysis_query = """
                SELECT 
                    c.customer_id,
                    c.name as customer_name,
                    c.tier,
                    COUNT(s.sale_id) as total_sales,
                    SUM(s.amount) as total_revenue,
                    AVG(s.amount) as avg_sale_amount
                FROM {customers} c
                LEFT JOIN {sales} s ON c.customer_id = s.customer_id
                GROUP BY c.customer_id, c.name, c.tier
                ORDER BY total_revenue DESC NULLS LAST
            """.format(customers=customers_table, sales=sales_table)
            
            analysis_result = datastore.execute_sql(sales_analysis_query)
            print(f"   Customer Analysis: {len(analysis_result)} customers analyzed")
            print(f"   Top customer: {analysis_result.iloc[0]['customer_name']} (${analysis_result.iloc[0]['total_revenue']:,.2f})")
            
            # Regional performance
            regional_query = """
                SELECT 
                    c.region,
                    COUNT(DISTINCT c.customer_id) as customer_count,
                    COALESCE(SUM(s.amount), 0) as region_revenue
                FROM {customers} c
                LEFT JOIN {sales} s ON c.customer_id = s.customer_id
                GROUP BY c.region
                ORDER BY region_revenue DESC
            """.format(customers=customers_table, sales=sales_table)
            
            regional_result = datastore.execute_sql(regional_query)
            print(f"   Regional Analysis: {len(regional_result)} regions")
            top_region = regional_result.iloc[0]
            print(f"   Top region: {top_region['region']} (${top_region['region_revenue']:,.2f})")
            
            # 3. Demonstrate table management
            print("\n📈 Table Management...")
            available_tables = datastore.get_available_tables()
            print(f"   Available tables: {len(available_tables)}")
            
            for table in available_tables:
                print(f"     • {table.name} ({table.step_id}): {table.rows} rows, {len(table.columns)} columns")
            
            # 4. Create analytical views
            print("\n🔧 Creating Analytical Views...")
            datastore.create_view(
                "customer_360",
                f"""
                SELECT 
                    c.*,
                    COALESCE(s_agg.total_sales, 0) as total_sales,
                    COALESCE(s_agg.total_revenue, 0) as total_revenue,
                    COALESCE(t_agg.ticket_count, 0) as support_tickets
                FROM {customers_table} c
                LEFT JOIN (
                    SELECT 
                        customer_id,
                        COUNT(*) as total_sales,
                        SUM(amount) as total_revenue
                    FROM {sales_table}
                    GROUP BY customer_id
                ) s_agg ON c.customer_id = s_agg.customer_id
                LEFT JOIN (
                    SELECT 
                        customer_id,
                        COUNT(*) as ticket_count
                    FROM {support_table}
                    GROUP BY customer_id
                ) t_agg ON c.customer_id = t_agg.customer_id
                """,
                step_id="create_customer_360"
            )
            
            # Query the view
            customer_360 = datastore.execute_sql("SELECT * FROM customer_360 ORDER BY total_revenue DESC")
            print(f"   Customer 360 view: {len(customer_360)} complete customer profiles")
            
            # 5. Export capabilities
            print("\n💾 Data Export Capabilities...")
            import tempfile
            import os
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Export to CSV
                csv_path = os.path.join(temp_dir, "customer_analysis.csv")
                datastore.export_table("load_customers", csv_path, "csv")
                print(f"   Exported customers to CSV: {os.path.getsize(csv_path)} bytes")
                
                # Export analysis to Parquet
                parquet_path = os.path.join(temp_dir, "regional_analysis.parquet")
                regional_result_table = datastore.store_step_output(
                    "regional_analysis",
                    regional_result.to_dict('records'),
                    "duckdb_sql"
                )
                datastore.export_table("regional_analysis", parquet_path, "parquet")
                print(f"   Exported regional analysis to Parquet: {os.path.getsize(parquet_path)} bytes")
        
        print("\n🔧 Configuration Management...")
        config_manager = ExecutionConfigManager()
        
        # Test DuckDB configuration
        duckdb_config = config_manager.get_duckdb_config()
        print(f"   Memory limit: {duckdb_config.memory_limit}")
        print(f"   Threads: {duckdb_config.threads}")
        print(f"   Auto cleanup: {duckdb_config.auto_cleanup}")
        
        # 6. Demonstrate step template
        print("\n🎯 DuckDB Step Template...")
        duckdb_template = StepTemplateFactory.create_template("duckdb_sql")
        print(f"   Template type: {duckdb_template.template_type}")
        print(f"   Template class: {duckdb_template.__class__.__name__}")
        
        print("\n✨ DuckDB Integration Features:")
        print("   ✅ Embedded analytical database for workflow data")
        print("   ✅ SQL-based data transformations between steps")
        print("   ✅ Automatic data persistence and retrieval")
        print("   ✅ Complex analytics with joins, aggregations, window functions")
        print("   ✅ Data export to multiple formats (CSV, Parquet, JSON)")
        print("   ✅ Analytical views for reusable queries")
        print("   ✅ Memory-efficient processing of large datasets")
        print("   ✅ Integration with LLM steps for AI-powered insights")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def demonstrate_workflow_execution():
    """Demonstrate complete workflow execution with DuckDB."""
    print("\n" + "=" * 50)
    print("🔄 Complete Workflow Execution Demo")
    print("=" * 50)
    
    try:
        from thinkforge.execution_engine import ExecutionContext, ExecutionStatus
        from thinkforge.step_templates import execute_duckdb_sql_step
        
        # Create execution context with DuckDB
        context = ExecutionContext(
            workflow_id="customer_analytics_demo",
            run_id="demo_run_001",
            status=ExecutionStatus.RUNNING
        )
        
        print("📊 Execution Context with DuckDB:")
        print(f"   Workflow ID: {context.workflow_id}")
        print(f"   Run ID: {context.run_id}")
        print(f"   DataStore: {context.datastore.__class__.__name__}")
        
        # Store initial data
        print("\n📋 Loading Initial Data...")
        context.store_step_output(
            "customers",
            SAMPLE_CUSTOMERS, 
            "function",
            metadata={"rows": len(SAMPLE_CUSTOMERS)}
        )
        
        context.store_step_output(
            "sales",
            SAMPLE_SALES,
            "function", 
            metadata={"rows": len(SAMPLE_SALES)}
        )
        
        print(f"   Stored {len(SAMPLE_CUSTOMERS)} customers")
        print(f"   Stored {len(SAMPLE_SALES)} sales records")
        
        # Execute SQL transformation
        print("\n🔍 Executing SQL Analytics...")
        
        sql_step_config = {
            "id": "revenue_analysis",
            "inputs": {
                "query": """
                    SELECT 
                        c.tier,
                        COUNT(DISTINCT c.customer_id) as customer_count,
                        COUNT(s.sale_id) as total_sales,
                        SUM(s.amount) as total_revenue,
                        AVG(s.amount) as avg_sale_amount,
                        ROUND(SUM(s.amount) * 100.0 / SUM(SUM(s.amount)) OVER (), 2) as revenue_percentage
                    FROM {table:customers} c
                    LEFT JOIN {table:sales} s ON c.customer_id = s.customer_id
                    GROUP BY c.tier
                    ORDER BY total_revenue DESC
                """
            }
        }
        
        # Execute the SQL step
        sql_result = await execute_duckdb_sql_step(
            sql_step_config,
            entity_values={},
            context=context
        )
        
        if sql_result.success:
            print("   ✅ SQL analysis completed successfully")
            print(f"   Analyzed {sql_result.metadata['row_count']} customer tiers")
            print(f"   Query executed: {sql_result.metadata['sql_query'][:100]}...")
            
            # Show some results
            if sql_result.data:
                print("\n📊 Revenue Analysis by Tier:")
                for row in sql_result.data:
                    tier = row['tier']
                    revenue = row['total_revenue'] or 0
                    customers = row['customer_count']
                    percentage = row['revenue_percentage'] or 0
                    print(f"     {tier.title()}: {customers} customers, ${revenue:,.2f} ({percentage:.1f}%)")
        else:
            print(f"   ❌ SQL analysis failed: {sql_result.error}")
        
        # Query available data
        print("\n📈 Available Data Tables:")
        tables = context.get_available_tables()
        for table in tables:
            print(f"   • {table.step_id}: {table.rows} rows ({table.name})")
        
        # Execute cross-table analytics
        print("\n🔗 Cross-Table Analytics...")
        
        cross_analysis = context.execute_sql("""
            SELECT 
                'Summary' as analysis_type,
                COUNT(DISTINCT c.customer_id) as total_customers,
                COUNT(DISTINCT c.region) as regions,
                COUNT(DISTINCT s.sale_id) as total_sales,
                SUM(s.amount) as total_revenue,
                ROUND(AVG(s.amount), 2) as avg_sale_amount
            FROM {table:customers} c
            LEFT JOIN {table:sales} s ON c.customer_id = s.customer_id
        """.replace("{table:customers}", "step_customers_*").replace("{table:sales}", "step_sales_*"),
            as_dataframe=False
        )
        
        if cross_analysis:
            summary = cross_analysis[0]
            print(f"   Total Customers: {summary['total_customers']}")
            print(f"   Regions: {summary['regions']}") 
            print(f"   Total Sales: {summary['total_sales']}")
            print(f"   Total Revenue: ${summary['total_revenue']:,.2f}")
            print(f"   Average Sale: ${summary['avg_sale_amount']:,.2f}")
        
        # Clean up
        context.close_datastore()
        
        print("\n✅ Workflow execution completed successfully!")
        print("\n🎯 Capabilities Demonstrated:")
        print("   • Embedded DuckDB database per workflow execution")
        print("   • Automatic step output persistence")
        print("   • SQL-based data transformations with table references")
        print("   • Cross-step data analytics and aggregations")
        print("   • Memory-efficient processing of analytical workloads")
        print("   • Complex SQL with joins, window functions, and CTEs")
        
        return True
        
    except Exception as e:
        print(f"❌ Workflow execution demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def demonstrate_use_cases():
    """Demonstrate various DuckDB use cases in workflows."""
    print("\n" + "=" * 50)
    print("🎯 DuckDB Use Cases in ThinkForge Workflows")
    print("=" * 50)
    
    use_cases = {
        "Customer Analytics": {
            "description": "Analyze customer behavior, segmentation, and lifetime value",
            "sql_examples": [
                "Customer cohort analysis with retention metrics",
                "RFM (Recency, Frequency, Monetary) segmentation",
                "Customer lifetime value calculations",
                "Churn prediction feature engineering"
            ],
            "workflow_benefits": [
                "Join customer data across multiple sources",
                "Calculate complex metrics with window functions", 
                "Create analytical views for downstream steps",
                "Generate insights for LLM analysis"
            ]
        },
        "Sales Performance": {
            "description": "Track sales metrics, forecasting, and performance analysis",
            "sql_examples": [
                "Time-series sales trend analysis",
                "Sales rep performance comparisons",
                "Product mix and profitability analysis",
                "Territory and regional performance"
            ],
            "workflow_benefits": [
                "Aggregate sales data across time periods",
                "Calculate growth rates and trends",
                "Identify top performers and opportunities",
                "Prepare data for forecasting models"
            ]
        },
        "Operations Intelligence": {
            "description": "Monitor operations, efficiency, and process optimization",
            "sql_examples": [
                "Process efficiency and bottleneck analysis",
                "Resource utilization optimization",
                "Quality metrics and SLA tracking",
                "Cost center performance analysis"
            ],
            "workflow_benefits": [
                "Real-time operational dashboards",
                "Automated anomaly detection",
                "Process improvement recommendations",
                "Predictive maintenance insights"
            ]
        },
        "Financial Reporting": {
            "description": "Generate financial reports, budgeting, and variance analysis",
            "sql_examples": [
                "P&L statement generation",
                "Budget vs actual variance analysis",
                "Cash flow projections",
                "ROI and profitability analysis"
            ],
            "workflow_benefits": [
                "Automated financial close processes",
                "Real-time financial KPI tracking",
                "Variance analysis and explanations",
                "Regulatory compliance reporting"
            ]
        },
        "Data Science Pipelines": {
            "description": "Feature engineering, model training, and ML workflows",
            "sql_examples": [
                "Feature engineering with statistical functions",
                "Data preprocessing and cleaning",
                "Train/test data splitting",
                "Model performance evaluation"
            ],
            "workflow_benefits": [
                "Efficient data preparation at scale",
                "Feature store capabilities",
                "Model training data versioning",
                "Automated model evaluation pipelines"
            ]
        }
    }
    
    print("🔍 Key Use Cases:")
    for use_case, details in use_cases.items():
        print(f"\n📊 {use_case}")
        print(f"   {details['description']}")
        print("   SQL Capabilities:")
        for sql_example in details['sql_examples']:
            print(f"     • {sql_example}")
        print("   Workflow Benefits:")
        for benefit in details['workflow_benefits']:
            print(f"     ✓ {benefit}")
    
    print(f"\n🚀 Technical Advantages:")
    advantages = [
        "Columnar storage optimized for analytical queries",
        "Vectorized execution for high-performance analytics", 
        "Full SQL support including window functions and CTEs",
        "Zero-copy integration with pandas DataFrames",
        "Automatic query optimization and caching",
        "Memory-efficient processing of large datasets",
        "Built-in statistical and analytical functions",
        "Support for complex data types (JSON, arrays, structs)"
    ]
    
    for advantage in advantages:
        print(f"   ✅ {advantage}")
    
    print(f"\n🔗 Integration Benefits:")
    integration_benefits = [
        "Persistent data between workflow steps",
        "SQL-based transformations complement code-based steps",
        "Prepare structured data for LLM analysis",
        "Enable complex multi-step analytical workflows",
        "Support for both real-time and batch processing",
        "Automatic data lineage and audit trails",
        "Export capabilities for external reporting",
        "Memory efficiency for large-scale workflows"
    ]
    
    for benefit in integration_benefits:
        print(f"   🔄 {benefit}")

def main():
    """Run the complete DuckDB integration demonstration."""
    print("🎯 ThinkForge DuckDB Integration")
    print("Advanced Analytics for Workflow Automation\n")
    
    # Run synchronous demos
    integration_success = demonstrate_duckdb_integration()
    
    # Run async workflow demo
    if integration_success:
        execution_success = asyncio.run(demonstrate_workflow_execution())
    else:
        execution_success = False
    
    # Show use cases
    demonstrate_use_cases()
    
    print("\n" + "=" * 50)
    if integration_success and execution_success:
        print("🎉 DuckDB Integration Demo Completed Successfully!")
        print("\n📚 Next Steps:")
        print("   1. Install DuckDB: pip install duckdb pandas pyarrow")
        print("   2. Create workflows with duckdb_sql step types")
        print("   3. Use SQL transformations between workflow steps")
        print("   4. Combine with LLM steps for AI-powered insights")
        print("   5. Export results for external reporting and analysis")
        print("\n🔧 Configuration:")
        print("   • Set DUCKDB_MEMORY_LIMIT for memory control")
        print("   • Configure DUCKDB_THREADS for parallel processing")
        print("   • Use DUCKDB_TEMP_DIR for custom database locations")
    else:
        print("❌ Demo completed with errors - check logs above")
    
    return integration_success and execution_success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)