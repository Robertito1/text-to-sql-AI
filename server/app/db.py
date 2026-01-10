import os
from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# Singleton instance
_db_instance: SQLDatabase | None = None

def init_database() -> SQLDatabase:
    """Initialize database connection with pooling at application startup."""
    global _db_instance
    
    if _db_instance is not None:
        return _db_instance
    
    # Support both PostgreSQL (DATABASE_URL) and SQL Server (ODBC_STR)
    database_url = os.getenv("DATABASE_URL")
    odbc_str = os.getenv("ODBC_STR")
    
    if database_url:
        # PostgreSQL (Supabase)
        db_uri = database_url
    elif odbc_str:
        # SQL Server (legacy)
        from urllib.parse import quote_plus
        db_uri = "mssql+pyodbc:///?odbc_connect=" + quote_plus(odbc_str)
    else:
        raise RuntimeError("DATABASE_URL or ODBC_STR must be set in environment variables")
    
    # Create engine with connection pooling
    engine = create_engine(
        db_uri,
        poolclass=QueuePool,
        pool_size=5,           # Max 5 connections in pool
        max_overflow=10,       # Allow 10 additional connections if pool is full
        pool_pre_ping=True,    # Verify connections before using
        pool_recycle=3600,     # Recycle connections after 1 hour
        echo=False             # Set to True for SQL debugging
    )
    
    _db_instance = SQLDatabase(engine)
    return _db_instance

def get_sql_database() -> SQLDatabase:
    """Get the database instance (must call init_database first)."""
    if _db_instance is None:
        # Fallback: initialize if not done yet
        return init_database()
    return _db_instance

def close_database():
    """Close database connections (call on shutdown)."""
    global _db_instance
    if _db_instance is not None:
        _db_instance._engine.dispose()
        _db_instance = None