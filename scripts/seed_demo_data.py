#!/usr/bin/env python3
"""
Demo Data Seeding Script for ThinkForge

This script creates sample data for demonstrating ThinkForge capabilities,
including tools, recipes, and API templates.
"""

import os
import sys
import logging
from datetime import datetime, timedelta

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from thinkforge.models import Text2SQLCache, UsageLog, Base
    from thinkforge.controller import Text2SQLController
    from database import SessionLocal, engine
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    print("Make sure you're running this from the project root and have installed dependencies")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Sample tools data
SAMPLE_TOOLS = [
    {
        'nl_query': 'PostgreSQL database query tool',
        'template': '''import psycopg2
import pandas as pd

def execute_query(connection_string, query):
    """Execute PostgreSQL query and return results"""
    conn = psycopg2.connect(connection_string)
    try:
        result = pd.read_sql_query(query, conn)
        return result
    finally:
        conn.close()''',
        'template_type': 'mcp_tool',
        'catalog_type': 'database',
        'catalog_subtype': 'postgresql',
        'catalog_name': 'pg_query_tool',
        'tool_capabilities': ['database_query', 'data_retrieval', 'sql_execution'],
        'health_status': 'healthy'
    },
    {
        'nl_query': 'JSON data transformation function',
        'template': '''import json
from typing import Dict, Any

def transform_json(data: dict, mapping: Dict[str, str]) -> dict:
    """Transform JSON data using field mapping"""
    transformed = {}
    for old_key, new_key in mapping.items():
        if old_key in data:
            transformed[new_key] = data[old_key]
    return transformed''',
        'template_type': 'function',
        'catalog_type': 'data_processing',
        'catalog_subtype': 'transformation',
        'catalog_name': 'json_transformer',
        'tool_capabilities': ['json_processing', 'data_transformation', 'field_mapping'],
        'health_status': 'healthy'
    },
    {
        'nl_query': 'REST API client for user management',
        'template': '''GET /api/v1/users/{user_id}
Host: api.example.com
Authorization: Bearer {token}
Content-Type: application/json''',
        'template_type': 'api',
        'catalog_type': 'web_service',
        'catalog_subtype': 'rest_api',
        'catalog_name': 'user_management_api',
        'tool_capabilities': ['user_retrieval', 'api_client', 'authentication'],
        'health_status': 'healthy'
    },
    {
        'nl_query': 'Data validation AI agent',
        'template': '''You are a data validation agent. Your task is to:
1. Check data completeness
2. Validate data types
3. Identify anomalies
4. Suggest corrections

When given a dataset, analyze it and provide:
- Validation report
- Error summary
- Recommendations for data cleaning''',
        'template_type': 'agent',
        'catalog_type': 'ai_service',
        'catalog_subtype': 'validation',
        'catalog_name': 'data_validator_agent',
        'tool_capabilities': ['data_validation', 'anomaly_detection', 'quality_assurance'],
        'health_status': 'healthy'
    },
    {
        'nl_query': 'Email notification service',
        'template': '''import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(smtp_server, port, sender_email, sender_password, recipient_email, subject, body):
    """Send email notification"""
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))
    
    server = smtplib.SMTP(smtp_server, port)
    server.starttls()
    server.login(sender_email, sender_password)
    text = msg.as_string()
    server.sendmail(sender_email, recipient_email, text)
    server.quit()''',
        'template_type': 'function',
        'catalog_type': 'communication',
        'catalog_subtype': 'email',
        'catalog_name': 'email_notifier',
        'tool_capabilities': ['email_sending', 'notification', 'smtp_client'],
        'health_status': 'healthy'
    }
]

# Sample recipes data
SAMPLE_RECIPES = [
    {
        'nl_query': 'Customer data processing workflow',
        'template': '''A complete workflow for processing customer data:
1. Extract customer information from database
2. Validate data integrity and completeness
3. Transform data to standard format
4. Send notification when processing is complete''',
        'template_type': 'recipe',
        'catalog_type': 'data_processing',
        'catalog_subtype': 'customer_management',
        'catalog_name': 'customer_data_workflow',
        'recipe_steps': [
            {
                'id': 'step_1',
                'name': 'Extract customer data',
                'type': 'integration',
                'tool_id': 1,
                'depends_on': []
            },
            {
                'id': 'step_2', 
                'name': 'Validate data',
                'type': 'validation',
                'tool_id': 4,
                'depends_on': ['step_1']
            },
            {
                'id': 'step_3',
                'name': 'Transform to JSON',
                'type': 'transform', 
                'tool_id': 2,
                'depends_on': ['step_2']
            },
            {
                'id': 'step_4',
                'name': 'Send completion email',
                'type': 'notification',
                'tool_id': 5,
                'depends_on': ['step_3']
            }
        ],
        'required_tools': [1, 2, 4, 5],
        'execution_time_estimate': 15,
        'complexity_level': 'intermediate'
    },
    {
        'nl_query': 'User onboarding automation recipe',
        'template': '''Automated user onboarding process:
1. Create user account via API
2. Send welcome email
3. Set up user preferences
4. Log onboarding completion''',
        'template_type': 'recipe',
        'catalog_type': 'user_management',
        'catalog_subtype': 'onboarding',
        'catalog_name': 'user_onboarding_recipe',
        'recipe_steps': [
            {
                'id': 'step_1',
                'name': 'Create user account',
                'type': 'integration',
                'tool_id': 3,
                'depends_on': []
            },
            {
                'id': 'step_2',
                'name': 'Send welcome email',
                'type': 'notification',
                'tool_id': 5,
                'depends_on': ['step_1']
            }
        ],
        'required_tools': [3, 5],
        'execution_time_estimate': 5,
        'complexity_level': 'beginner'
    }
]

# Sample API templates
SAMPLE_API_TEMPLATES = [
    {
        'nl_query': 'Weather API endpoint',
        'template': '''GET /weather/current
Host: api.openweathermap.org
API-Key: {api_key}
Parameters:
  - q: {city_name}
  - units: metric
  - appid: {api_key}''',
        'template_type': 'api',
        'catalog_type': 'external_service',
        'catalog_subtype': 'weather',
        'catalog_name': 'openweather_api',
        'tool_capabilities': ['weather_data', 'location_based', 'real_time_data'],
        'health_status': 'healthy'
    },
    {
        'nl_query': 'Slack messaging API',
        'template': '''POST /api/chat.postMessage
Host: slack.com
Authorization: Bearer {bot_token}
Content-Type: application/json

{
  "channel": "{channel_id}",
  "text": "{message_text}",
  "username": "ThinkForge Bot"
}''',
        'template_type': 'api',
        'catalog_type': 'communication',
        'catalog_subtype': 'messaging',
        'catalog_name': 'slack_api',
        'tool_capabilities': ['messaging', 'team_communication', 'bot_integration'],
        'health_status': 'healthy'
    }
]

def create_sample_entry(session, controller, entry_data):
    """Create a single sample cache entry."""
    try:
        # Check if entry already exists
        existing = session.query(Text2SQLCache).filter_by(
            nl_query=entry_data['nl_query'],
            template_type=entry_data['template_type']
        ).first()
        
        if existing:
            logger.debug(f"Entry already exists: {entry_data['nl_query'][:50]}...")
            return existing
        
        # Generate embedding
        embedding = None
        try:
            embedding_vector = controller._get_embedding(entry_data['nl_query'])
            if embedding_vector is not None:
                embedding = embedding_vector.tolist()
        except Exception as e:
            logger.warning(f"Failed to generate embedding: {e}")
        
        # Create cache entry
        cache_entry = Text2SQLCache(
            nl_query=entry_data['nl_query'],
            template=entry_data['template'],
            template_type=entry_data['template_type'],
            is_template=entry_data.get('is_template', True),
            catalog_type=entry_data.get('catalog_type'),
            catalog_subtype=entry_data.get('catalog_subtype'),
            catalog_name=entry_data.get('catalog_name'),
            status='active',
            usage_count=0,
            embedding=embedding,
            
            # Tool-specific fields
            tool_capabilities=entry_data.get('tool_capabilities'),
            health_status=entry_data.get('health_status', 'unknown'),
            
            # Recipe-specific fields
            recipe_steps=entry_data.get('recipe_steps'),
            required_tools=entry_data.get('required_tools'),
            execution_time_estimate=entry_data.get('execution_time_estimate'),
            complexity_level=entry_data.get('complexity_level'),
            execution_count=0
        )
        
        session.add(cache_entry)
        session.flush()  # Get the ID
        
        logger.info(f"Created {entry_data['template_type']}: {entry_data['nl_query'][:50]}...")
        return cache_entry
        
    except Exception as e:
        logger.error(f"Failed to create entry {entry_data['nl_query'][:50]}...: {e}")
        session.rollback()
        return None

def create_sample_usage_logs(session, cache_entries):
    """Create sample usage logs for demonstration."""
    logger.info("Creating sample usage logs...")
    
    sample_prompts = [
        "Show me customer data for user ID 12345",
        "Transform this JSON data to CSV format",
        "Send notification email to admin",
        "Validate this dataset for completeness", 
        "Get current weather for New York",
        "Post message to team channel",
        "Create new user account",
        "Process customer onboarding workflow"
    ]
    
    created_count = 0
    base_time = datetime.now() - timedelta(days=7)
    
    for i, prompt in enumerate(sample_prompts):
        try:
            # Pick a random cache entry
            cache_entry = cache_entries[i % len(cache_entries)]
            
            usage_log = UsageLog(
                cache_entry_id=cache_entry.id,
                timestamp=base_time + timedelta(hours=i*3),
                prompt=prompt,
                success_status=True,
                similarity_score=0.85 + (i % 3) * 0.05,
                llm_used=i % 2 == 0,
                response=f"Successfully processed: {prompt}",
                is_confident=True
            )
            
            session.add(usage_log)
            created_count += 1
            
        except Exception as e:
            logger.error(f"Failed to create usage log: {e}")
    
    session.commit()
    logger.info(f"Created {created_count} sample usage logs")
    return created_count

def main():
    """Main seeding function."""
    logger.info("Starting ThinkForge demo data seeding...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Create database session and controller
    session = SessionLocal()
    controller = Text2SQLController(db_session=session)
    
    try:
        created_entries = []
        
        # Create sample tools
        logger.info("Creating sample tools...")
        for tool_data in SAMPLE_TOOLS:
            entry = create_sample_entry(session, controller, tool_data)
            if entry:
                created_entries.append(entry)
        
        # Create sample API templates
        logger.info("Creating sample API templates...")
        for api_data in SAMPLE_API_TEMPLATES:
            entry = create_sample_entry(session, controller, api_data)
            if entry:
                created_entries.append(entry)
        
        # Create sample recipes
        logger.info("Creating sample recipes...")
        for recipe_data in SAMPLE_RECIPES:
            entry = create_sample_entry(session, controller, recipe_data)
            if entry:
                created_entries.append(entry)
        
        session.commit()
        
        # Create sample usage logs
        if created_entries:
            create_sample_usage_logs(session, created_entries)
        
        logger.info(f"Demo data seeding completed successfully!")
        logger.info(f"Created {len(created_entries)} cache entries")
        logger.info("ThinkForge is ready for demonstration!")
        
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        session.rollback()
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    main()