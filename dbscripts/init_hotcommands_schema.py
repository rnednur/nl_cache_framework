#!/usr/bin/env python3
"""
Initialize Hot Commands schema for ThinkForge database
This script extends the existing ThinkForge database with Hot Commands functionality
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Add parent directories to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../thinkforge")))

from thinkforge.models import Base as ThinkForgeBase, DB_SCHEMA
from thinkforge.hotcommands_models import User, HotCommand, CommandExecution, Space, Feedback

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment variables."""
    # Try different environment variable names
    db_url = (
        os.getenv('DATABASE_URL') or 
        os.getenv('POSTGRES_URL') or
        os.getenv('DB_URL')
    )
    
    if not db_url:
        # Build from components
        user = os.getenv('DB_USER', 'postgres')
        password = os.getenv('DB_PASSWORD', 'postgres')
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        name = os.getenv('DB_NAME', 'thinkforge')
        
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    
    logger.info(f"Using database URL: {db_url.split('@')[0]}@***")
    return db_url

def create_schema_if_not_exists(engine, schema_name):
    """Create schema if it doesn't exist."""
    if schema_name and schema_name != 'public':
        try:
            with engine.connect() as conn:
                # Check if schema exists
                result = conn.execute(text(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"
                ), {"schema": schema_name})
                
                if not result.fetchone():
                    logger.info(f"Creating schema: {schema_name}")
                    conn.execute(text(f'CREATE SCHEMA "{schema_name}"'))
                    conn.commit()
                else:
                    logger.info(f"Schema {schema_name} already exists")
        except SQLAlchemyError as e:
            logger.error(f"Error creating schema: {e}")
            raise

def init_hotcommands_database():
    """Initialize the Hot Commands database schema."""
    try:
        db_url = get_database_url()
        logger.info(f"Connecting to database with schema: {DB_SCHEMA}")
        
        # Create engine with schema-aware connection
        connect_args = {}
        if DB_SCHEMA != 'public':
            connect_args["options"] = f"-csearch_path={DB_SCHEMA}"
            
        engine = create_engine(
            db_url,
            connect_args=connect_args,
            echo=True  # Set to False to reduce output
        )
        
        # Create schema if needed
        create_schema_if_not_exists(engine, DB_SCHEMA if DB_SCHEMA != 'public' else None)
        
        # Create all tables
        logger.info("Creating Hot Commands tables...")
        ThinkForgeBase.metadata.create_all(bind=engine)
        
        logger.info("Hot Commands database schema initialized successfully!")
        
        # Verify tables were created
        with engine.connect() as conn:
            schema_filter = f"AND table_schema = '{DB_SCHEMA}'" if DB_SCHEMA != 'public' else "AND table_schema = 'public'"
            result = conn.execute(text(f"""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_type = 'BASE TABLE'
                {schema_filter}
                AND table_name IN ('users', 'hot_commands', 'command_executions', 'spaces', 'feedback')
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"Created tables: {tables}")
            
        return engine
        
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

def create_demo_data(engine):
    """Create demo data for testing."""
    logger.info("Creating demo data...")
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        # Check if demo user already exists
        existing_user = session.query(User).filter(User.username == 'demo').first()
        if existing_user:
            logger.info("Demo user already exists, skipping demo data creation")
            return existing_user
        
        # Create demo user
        demo_user = User(
            username='demo',
            email='demo@example.com',
            display_name='Demo User',
            hashed_password='$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj2yKHhPR6dq',  # "demo"
            is_active=True,
            is_superuser=False,
            domains=['sales', 'analytics', 'finance'],
            permissions=['read', 'write', 'execute'],
            roles=['analyst', 'user'],
            preferences={'theme': 'light', 'default_format': 'table'},
            command_count=4,
            favorite_commands=['sales_summary', 'user_analytics', 'monthly_report']
        )
        
        session.add(demo_user)
        session.flush()  # Get the user ID
        
        # Create demo hot commands
        demo_commands = [
            HotCommand(
                user_id=demo_user.id,
                command_name='sales_summary',
                display_name='Sales Summary Report',
                description='Generate a summary of sales data for the current period',
                query_text='show me the sales summary for this month',
                query_type='nl2sql',
                domain='sales',
                category='reports',
                tags=['sales', 'monthly', 'summary'],
                parameters={'period': 'month'},
                parameter_schema={'period': {'type': 'string', 'options': ['day', 'week', 'month', 'year']}},
                default_values={'period': 'month'},
                status='active',
                is_public=True,
                usage_count=45,
                success_rate=0.94,
                avg_execution_time=1200.5,
                rating=4.5,
                rating_count=12,
                output_format='table'
            ),
            HotCommand(
                user_id=demo_user.id,
                command_name='user_analytics',
                display_name='User Analytics Dashboard',
                description='Analyze user behavior and engagement metrics',
                query_text='show user analytics and engagement metrics',
                query_type='nl2sql',
                domain='analytics',
                category='user_behavior',
                tags=['users', 'analytics', 'engagement'],
                parameters={'timeframe': '30d'},
                parameter_schema={'timeframe': {'type': 'string', 'options': ['7d', '30d', '90d']}},
                default_values={'timeframe': '30d'},
                status='active',
                is_public=False,
                usage_count=28,
                success_rate=0.89,
                avg_execution_time=2100.3,
                rating=4.2,
                rating_count=8,
                output_format='chart'
            ),
            HotCommand(
                user_id=demo_user.id,
                command_name='monthly_report',
                display_name='Monthly Performance Report',
                description='Comprehensive monthly performance report across all metrics',
                query_text='generate comprehensive monthly performance report',
                query_type='workflow',
                domain='finance',
                category='reports',
                tags=['monthly', 'performance', 'comprehensive'],
                parameters={'month': 'current'},
                parameter_schema={'month': {'type': 'string', 'options': ['current', 'previous', 'custom']}},
                default_values={'month': 'current'},
                status='active',
                is_public=True,
                usage_count=15,
                success_rate=0.93,
                avg_execution_time=5400.7,
                rating=4.8,
                rating_count=6,
                output_format='report'
            ),
            HotCommand(
                user_id=demo_user.id,
                command_name='capacity_alerts',
                display_name='Capacity Alerts Monitor',
                description='Monitor system capacity and generate alerts for high utilization',
                query_text='show capacity alerts for systems over 80% utilization',
                query_type='tool_call',
                domain='operations',
                category='monitoring',
                tags=['capacity', 'alerts', 'monitoring', 'utilization'],
                parameters={'threshold': 0.8},
                parameter_schema={'threshold': {'type': 'number', 'min': 0.5, 'max': 0.95}},
                default_values={'threshold': 0.8},
                status='active',
                is_public=False,
                usage_count=67,
                success_rate=0.96,
                avg_execution_time=800.2,
                rating=4.3,
                rating_count=14,
                output_format='table'
            )
        ]
        
        for command in demo_commands:
            session.add(command)
        
        session.commit()
        logger.info(f"Created demo user: {demo_user.username} (ID: {demo_user.id})")
        logger.info(f"Created {len(demo_commands)} demo hot commands")
        
        return demo_user
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating demo data: {e}")
        raise
    finally:
        session.close()

def main():
    """Main function."""
    try:
        engine = init_hotcommands_database()
        
        # Create demo data if requested
        if '--demo' in sys.argv or os.getenv('CREATE_DEMO_DATA', '').lower() == 'true':
            create_demo_data(engine)
            
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()