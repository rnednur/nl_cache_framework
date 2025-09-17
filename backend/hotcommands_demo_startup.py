#!/usr/bin/env python3
"""
Hot Commands Demo Startup Script
Initializes the database with demo data and tests the integration
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_database():
    """Initialize the database with Hot Commands schema and demo data."""
    try:
        logger.info("Setting up Hot Commands database...")
        
        # Import and run the database initialization
        from dbscripts.init_hotcommands_schema import init_hotcommands_database, create_demo_data
        
        # Initialize database
        engine = init_hotcommands_database()
        
        # Create demo data
        create_demo_data(engine)
        
        logger.info("Database setup completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        return False

def test_api_integration():
    """Test that the API endpoints are properly integrated."""
    try:
        logger.info("Testing API integration...")
        
        # Import the main app
        from app import app
        
        # Check that our routes are registered
        routes = [route.path for route in app.routes]
        expected_routes = [
            "/api/hot-commands/my",
            "/api/hot-commands/public", 
            "/api/hot-commands",
            "/api/execute-command",
            "/api/spaces/my",
            "/api/analytics/dashboard"
        ]
        
        missing_routes = []
        for route in expected_routes:
            if route not in routes:
                missing_routes.append(route)
        
        if missing_routes:
            logger.error(f"Missing API routes: {missing_routes}")
            return False
        
        logger.info("All API routes successfully registered!")
        
        # Test controller integration
        from database import SessionLocal
        from hotcommands_api import get_hotcommands_controller
        
        db = SessionLocal()
        try:
            controller = get_hotcommands_controller(db)
            logger.info("Hot Commands controller integration successful!")
        finally:
            db.close()
        
        return True
        
    except Exception as e:
        logger.error(f"API integration test failed: {e}")
        return False

def print_startup_info():
    """Print information about how to access the system."""
    print("\n" + "="*60)
    print("🚀 HOT COMMANDS + THINKFORGE INTEGRATION READY!")
    print("="*60)
    print()
    print("📍 API Server: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    print("🖥️  Frontend: http://localhost:3000 (run separately)")
    print()
    print("🔥 Hot Commands API Endpoints:")
    print("   GET  /api/hot-commands/my          - Get user's commands")
    print("   POST /api/hot-commands             - Create new command")
    print("   GET  /api/hot-commands/public      - Get public commands")
    print("   POST /api/execute-command          - Execute any command")
    print("   GET  /api/command-suggestions      - Get command suggestions")
    print("   GET  /api/spaces/my                - Get user's spaces")
    print("   GET  /api/analytics/dashboard      - Get dashboard stats")
    print()
    print("📊 Demo Data Available:")
    print("   - User: demo (ID: 1)")
    print("   - 4 sample hot commands")
    print("   - Mock analytics data")
    print()
    print("🎯 Key Features Enabled:")
    print("   ✅ Semantic command matching via ThinkForge")
    print("   ✅ Intelligent caching and similarity search")
    print("   ✅ Parameter substitution and entity extraction")
    print("   ✅ Usage analytics and performance tracking")
    print("   ✅ Command suggestions and autocomplete")
    print()
    print("To start the server: uvicorn app:app --host 0.0.0.0 --port 8000 --reload")
    print("="*60)

def main():
    """Main startup function."""
    print("🔧 Initializing Hot Commands + ThinkForge Integration...")
    
    # Setup database
    if not setup_database():
        print("❌ Database setup failed. Exiting.")
        sys.exit(1)
    
    # Test API integration
    if not test_api_integration():
        print("❌ API integration test failed. Exiting.")
        sys.exit(1)
    
    # Print success info
    print_startup_info()
    
    print("\n✅ Initialization complete! System is ready to use.")

if __name__ == "__main__":
    main()