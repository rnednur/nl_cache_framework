"""
Database configuration and session management for the MCP server.

Sets up the SQLAlchemy engine and session factory based on the DATABASE_URL environment variable.
Provides a dependency (`get_db`) for FastAPI endpoints to obtain a database session.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import logging
import urllib.parse

load_dotenv() # Load environment variables from .env file

logger = logging.getLogger(__name__)

# --- Database URL Configuration ---
# Prioritize DATABASE_URL if set, otherwise construct from PG variables
# Example construction (adjust variable names as needed):
DB_USER = os.environ.get("POSTGRES_USER", "user")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "password")
DB_PASSWORD_encoded = urllib.parse.quote_plus(DB_PASSWORD)
DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")
DB_PORT = os.environ.get("POSTGRES_PORT", "5432")
DB_NAME = os.environ.get("POSTGRES_DB", "mcp_cache_db")

# Construct the PostgreSQL URL
SQLALCHEMY_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD_encoded}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

logger.info(f"Database URL: {SQLALCHEMY_DATABASE_URL}")

# --- Engine and Session Setup ---
try:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()

    # Test connection (optional but recommended)
    with engine.connect() as connection:
        logger.info("Database connection successful.")

except Exception as e:
    logger.error(f"Failed to connect to database or create session: {e}", exc_info=True)
    # Depending on requirements, might want to exit or handle differently
    raise RuntimeError(f"Database connection failed: {e}") from e

# --- Dependency for FastAPI ---
def get_db():
    """
    Get a database session.
    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
