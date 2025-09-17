#!/usr/bin/env python3
"""
Setup sample data for Hot Commands and Cache Entries
This script populates the database with sample records instead of using hardcoded fallbacks
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import sessionmaker
from thinkforge.database import get_engine
from thinkforge.hotcommands_models import HotCommand, User
from thinkforge.models import Text2SQLCache
import datetime

def create_sample_user(db):
    """Create a sample user if none exists."""
    
    user = db.query(User).filter(User.username == 'sample_user').first()
    if user:
        print("✅ Sample user already exists")
        return user
    
    user = User(
        username='sample_user',
        email='sample@example.com',
        display_name='Sample User',
        hashed_password='dummy_hash',  # In real app, this would be properly hashed
        is_active=True,
        domains=['Analytics', 'RAN', 'CustomerExperience', 'Operations'],
        permissions=['read', 'write'],
        roles=['user'],
        preferences={'theme': 'dark'},
        command_count=0,
        favorite_commands=[]
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    print("✅ Created sample user")
    return user

def create_sample_cache_entries(db):
    """Create sample cache entries with various catalog types."""
    
    sample_entries = [
        {
            'nl_query': 'Show me the top 10 customers by revenue',
            'template': 'SELECT customer_name, SUM(revenue) as total_revenue FROM sales_data GROUP BY customer_name ORDER BY total_revenue DESC LIMIT 10',
            'template_type': 'sql',
            'reasoning_trace': 'This query aggregates revenue by customer and returns top performers',
            'is_template': True,
            'catalog_type': 'sales',
            'catalog_subtype': 'revenue',
            'catalog_name': 'customer_analysis',
            'status': 'active',
            'tags': {'type': ['analytics', 'sales'], 'difficulty': ['beginner']}
        },
        {
            'nl_query': 'Generate weekly performance report for network cells',
            'template': 'SELECT cell_id, AVG(signal_strength) as avg_signal, COUNT(drops) as total_drops FROM ran_performance WHERE week = {week} GROUP BY cell_id',
            'template_type': 'sql',
            'reasoning_trace': 'Aggregates RAN performance metrics by cell for weekly reporting',
            'is_template': True,
            'catalog_type': 'analytics',
            'catalog_subtype': 'performance',
            'catalog_name': 'ran_monitoring',
            'status': 'active',
            'tags': {'type': ['ran', 'monitoring'], 'difficulty': ['intermediate']}
        },
        {
            'nl_query': 'Create customer satisfaction workflow',
            'template': '{"workflow": {"steps": [{"collect_feedback": {}}, {"analyze_sentiment": {}}, {"generate_report": {}}]}}',
            'template_type': 'workflow',
            'reasoning_trace': 'Multi-step workflow for processing customer satisfaction data',
            'is_template': True,
            'catalog_type': 'finance',
            'catalog_subtype': 'reporting',
            'catalog_name': 'customer_experience',
            'status': 'active',
            'tags': {'type': ['workflow', 'customer'], 'difficulty': ['advanced']}
        },
        {
            'nl_query': 'Get operational metrics dashboard data',
            'template': 'SELECT metric_name, current_value, target_value, status FROM operations_metrics WHERE date = CURRENT_DATE',
            'template_type': 'sql',
            'reasoning_trace': 'Retrieves current operational KPIs for dashboard display',
            'is_template': True,
            'catalog_type': 'operations',
            'catalog_subtype': 'kpi',
            'catalog_name': 'dashboard',
            'status': 'active',
            'tags': {'type': ['operations', 'dashboard'], 'difficulty': ['beginner']}
        },
        {
            'nl_query': 'Process API integration recipe',
            'template': '{"recipe": {"api_endpoint": "/v1/data", "method": "POST", "auth": "bearer"}}',
            'template_type': 'recipe',
            'reasoning_trace': 'Recipe for integrating with external data APIs',
            'is_template': True,
            'catalog_type': 'analytics',
            'catalog_subtype': 'integration',
            'catalog_name': 'api_recipes',
            'status': 'active',
            'tags': {'type': ['api', 'integration'], 'difficulty': ['intermediate']}
        }
    ]
    
    created_count = 0
    
    for entry_data in sample_entries:
        # Check if entry already exists
        existing = db.query(Text2SQLCache).filter(
            Text2SQLCache.nl_query == entry_data['nl_query']
        ).first()
        
        if existing:
            continue
        
        entry = Text2SQLCache(
            nl_query=entry_data['nl_query'],
            template=entry_data['template'],
            template_type=entry_data['template_type'],
            reasoning_trace=entry_data['reasoning_trace'],
            is_template=entry_data['is_template'],
            catalog_type=entry_data['catalog_type'],
            catalog_subtype=entry_data['catalog_subtype'],
            catalog_name=entry_data['catalog_name'],
            status=entry_data['status'],
            tags=entry_data['tags']
        )
        
        db.add(entry)
        created_count += 1
    
    if created_count > 0:
        db.commit()
        print(f"✅ Created {created_count} sample cache entries")
    else:
        print("✅ Sample cache entries already exist")

def create_sample_hot_commands(db, user):
    """Create sample hot commands with various domains and categories."""
    
    sample_commands = [
        {
            'command_name': 'top_customers',
            'display_name': 'Top Customers Report',
            'description': 'Generate a report of top customers by revenue',
            'query_text': 'Show me the top 10 customers by revenue this quarter',
            'query_type': 'nl2sql',
            'domain': 'Analytics',
            'category': 'Capacity',
            'tags': ['sales', 'reporting'],
            'is_public': True
        },
        {
            'command_name': 'ran_performance',
            'display_name': 'RAN Performance Analysis',
            'description': 'Analyze RAN network performance metrics',
            'query_text': 'Generate weekly performance report for network cells',
            'query_type': 'nl2sql',
            'domain': 'RAN',
            'category': 'RF',
            'tags': ['network', 'performance'],
            'is_public': True
        },
        {
            'command_name': 'customer_workflow',
            'display_name': 'Customer Satisfaction Workflow',
            'description': 'Execute customer satisfaction analysis workflow',
            'query_text': 'Run customer satisfaction analysis with sentiment scoring',
            'query_type': 'workflow',
            'domain': 'CustomerExperience',
            'category': 'Analytics',
            'tags': ['customer', 'satisfaction'],
            'is_public': False
        },
        {
            'command_name': 'ops_dashboard',
            'display_name': 'Operations Dashboard',
            'description': 'Display operational KPIs and metrics',
            'query_text': 'Get operational metrics dashboard data for today',
            'query_type': 'nl2sql',
            'domain': 'Operations',
            'category': 'Performance',
            'tags': ['operations', 'kpi'],
            'is_public': True
        },
        {
            'command_name': 'quality_metrics',
            'display_name': 'Quality Metrics Report',
            'description': 'Generate quality assurance metrics report',
            'query_text': 'Show quality metrics for the last 30 days',
            'query_type': 'nl2sql',
            'domain': 'Operations',
            'category': 'Quality',
            'tags': ['quality', 'reporting'],
            'is_public': True
        }
    ]
    
    created_count = 0
    
    for cmd_data in sample_commands:
        # Check if command already exists
        existing = db.query(HotCommand).filter(
            HotCommand.command_name == cmd_data['command_name'],
            HotCommand.user_id == user.id
        ).first()
        
        if existing:
            continue
        
        command = HotCommand(
            user_id=user.id,
            command_name=cmd_data['command_name'],
            display_name=cmd_data['display_name'],
            description=cmd_data['description'],
            query_text=cmd_data['query_text'],
            query_type=cmd_data['query_type'],
            domain=cmd_data['domain'],
            category=cmd_data['category'],
            tags=cmd_data['tags'],
            is_public=cmd_data['is_public'],
            status='active',
            usage_count=0,
            success_rate=1.0,
            rating=4.5,
            rating_count=10
        )
        
        db.add(command)
        created_count += 1
    
    if created_count > 0:
        db.commit()
        print(f"✅ Created {created_count} sample hot commands")
    else:
        print("✅ Sample hot commands already exist")

def main():
    """Setup all sample data."""
    
    print("🚀 Setting up sample data for Hot Commands system")
    print("=" * 60)
    
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    
    try:
        with SessionLocal() as db:
            print("\n1. Creating sample user...")
            user = create_sample_user(db)
            
            print("\n2. Creating sample cache entries...")
            create_sample_cache_entries(db)
            
            print("\n3. Creating sample hot commands...")
            create_sample_hot_commands(db, user)
            
            print("\n🎉 Sample data setup complete!")
            print("\n📊 Summary:")
            print(f"   • Sample domains: Analytics, RAN, CustomerExperience, Operations")
            print(f"   • Sample categories: Capacity, RF, Analytics, Performance, Quality")
            print(f"   • Sample catalog types: sales, analytics, finance, operations")
            print(f"   • Template types: sql, workflow, recipe")
            
            print("\n💡 Frontend dropdowns will now be populated with this data.")
            print("   Add more commands through the UI to expand the available options.")
            
    except Exception as e:
        print(f"❌ Error setting up sample data: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if main():
        print("\n✅ Setup completed successfully!")
    else:
        print("\n❌ Setup failed!")
        sys.exit(1)