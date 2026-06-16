"""
Database Connection and Configuration
Manages PostgreSQL connection and SQLAlchemy engine setup
"""

from sqlalchemy import create_engine, text
from typing import Optional
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv(".env.local")  # Load environment variables from .env.local

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Connection pool settings
POOL_SIZE = 10
MAX_OVERFLOW = 20
POOL_RECYCLE = 3600
POOL_PRE_PING = True


def get_engine(database_name: Optional[str] = None):
    """
    Get SQLAlchemy engine for a specific database.
    
    Args:
        database_name: Optional database name. If not provided, uses default database.
    
    Returns:
        SQLAlchemy Engine instance
    
    Example:
        engine = get_engine("Sample")  # Connect to Sample database
        engine = get_engine()          # Connect to default postgres database
    """
    db_name = database_name or os.getenv("DB_NAME", "postgres")
    
    # URL encode password to handle special characters
    encoded_password = quote_plus(DB_PASSWORD) if DB_PASSWORD else ""
    
    # PostgreSQL connection string
    if encoded_password:
        connection_string = (
            f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{db_name}"
        )
    else:
        connection_string = (
            f"postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{db_name}"
        )
    
    # Create engine with connection pooling
    engine = create_engine(
        connection_string,
        poolclass=None,  # Uses NullPool for simplicity, change to QueuePool for production
        connect_args={
            "connect_timeout": 10,
            "options": "-c statement_timeout=30000"  # 30 second timeout
        }
    )
    
    return engine


def test_connection(database_name: Optional[str] = None) -> bool:
    """Test database connection."""
    try:
        engine = get_engine(database_name)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Test connection when run directly
    print("Testing database connection...")
    if test_connection():
        print("✅ Connection successful!")
    else:
        print("❌ Connection failed!")
    