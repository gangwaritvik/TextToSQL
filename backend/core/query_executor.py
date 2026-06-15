"""
Query Executor - Executes generated SQL against the database
"""

from typing import List, Dict, Any
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.db.db import get_engine


class QueryExecutor:
    """Execute SQL queries against PostgreSQL database."""
    
    def __init__(self):
        """Initialize query executor."""
        pass
    
    def execute_query(
        self,
        sql_query: str,
        database_name: str,
        limit: int = 100
    ) -> tuple[List[Dict[str, Any]], str]:
        """
        Execute SQL query against database.
        
        Args:
            sql_query: SQL query to execute
            database_name: Database name
            limit: Maximum number of rows to return
        
        Returns:
            Tuple of (results list, error message if any)
        """
        try:
            if not sql_query or not sql_query.strip():
                return [], "No SQL query provided"
            
            print(f"📊 Executing query against {database_name}...")
            
            engine = get_engine(database_name)
            
            # Add LIMIT clause if not present
            query_upper = sql_query.upper()
            if "LIMIT" not in query_upper:
                sql_query = f"{sql_query.rstrip(';')} LIMIT {limit};"
            
            with engine.connect() as connection:
                result = connection.execute(__import__('sqlalchemy').text(sql_query))
                
                # Get column names
                columns = [col for col in result.keys()]
                
                # Get all rows
                rows = result.fetchall()
                
                # Convert to list of dicts
                results = [dict(zip(columns, row)) for row in rows]
                
                print(f"✅ Query executed successfully: {len(results)} rows returned")
                
                return results, ""
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error executing query: {error_msg}")
            return [], error_msg
    
    def validate_query(self, sql_query: str) -> tuple[bool, str]:
        """
        Validate SQL query syntax (basic check).
        
        Args:
            sql_query: SQL query to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not sql_query or not sql_query.strip():
                return False, "Empty query"
            
            # Check for dangerous keywords
            dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE"]
            query_upper = sql_query.upper().strip()
            
            for keyword in dangerous_keywords:
                if query_upper.startswith(keyword):
                    return False, f"Dangerous operation not allowed: {keyword}"
            
            # Check if it's a SELECT query
            if not query_upper.startswith("SELECT"):
                return False, "Only SELECT queries are supported"
            
            return True, ""
            
        except Exception as e:
            return False, str(e)


# Singleton instance
_query_executor: QueryExecutor = None


def get_query_executor() -> QueryExecutor:
    """Get or create singleton query executor instance."""
    global _query_executor
    if _query_executor is None:
        _query_executor = QueryExecutor()
    return _query_executor
