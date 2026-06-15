"""
Database Routes Main Router
Combines all database-related endpoints
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import inspect, text
from typing import List, Dict, Any
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.db import get_engine

# Create main router with /databases prefix
router = APIRouter(
    prefix="/databases",
    tags=["databases"],
    responses={404: {"description": "Not found"}},
)


@router.get("")
def get_all_databases() -> List[str]:
    """Fetch all databases from PostgreSQL server"""
    try:
        engine = get_engine()
        with engine.connect() as connection:
            query = text(
                """
                SELECT datname FROM pg_database
                WHERE datistemplate = false AND datallowconn = true
                ORDER BY datname
                """
            )
            result = connection.execute(query)
            databases = [row[0] for row in result.fetchall()]
        
        engine.dispose()
        return databases
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection error: {str(e)}"
        )


@router.get("/{database_name}/tables")
def get_tables_in_database(database_name: str) -> List[Dict[str, Any]]:
    """Fetch all tables in a specific database"""
    try:
        db_engine = get_engine(database_name)
        inspector = inspect(db_engine)
        
        tables = []
        table_names = inspector.get_table_names()
        
        for table_name in table_names:
            table_info = {
                "name": table_name,
                "schema": "public",
                "rows": 0
            }
            
            # Get row count
            try:
                with db_engine.connect() as connection:
                    query = text(f'SELECT COUNT(*) FROM "{table_name}"')
                    result = connection.execute(query)
                    table_info["rows"] = result.scalar()
            except:
                table_info["rows"] = 0
            
            tables.append(table_info)
        
        db_engine.dispose()
        return sorted(tables, key=lambda x: x["name"])
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching tables from {database_name}: {str(e)}"
        )


@router.get("/{database_name}/tables/{table_name}/schema")
def get_table_schema(database_name: str, table_name: str) -> Dict[str, Any]:
    """Fetch schema/columns for a specific table"""
    try:
        db_engine = get_engine(database_name)
        inspector = inspect(db_engine)
        
        # Get columns
        columns = inspector.get_columns(table_name)
        
        # Get primary keys
        pk_constraint = inspector.get_pk_constraint(table_name)
        primary_keys = pk_constraint["constrained_columns"] if pk_constraint else []
        
        # Get foreign keys
        foreign_keys = inspector.get_foreign_keys(table_name)
        
        # Format columns
        formatted_columns = []
        for col in columns:
            formatted_columns.append({
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col["nullable"],
                "primary_key": col["name"] in primary_keys,
                "default": col["default"]
            })
        
        schema = {
            "table_name": table_name,
            "database": database_name,
            "columns": formatted_columns,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys,
            "column_count": len(formatted_columns)
        }
        
        db_engine.dispose()
        return schema
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching schema for {table_name}: {str(e)}"
        )


@router.get("/{database_name}/tables/{table_name}/data")
def get_table_data(database_name: str, table_name: str, limit: int = 100) -> Dict[str, Any]:
    """Fetch actual data rows from a table"""
    try:
        db_engine = get_engine(database_name)
        
        with db_engine.connect() as connection:
            query = text(f'SELECT * FROM "{table_name}" LIMIT :limit')
            result = connection.execute(query, {"limit": limit})
            
            columns = [col for col in result.keys()]
            rows = []
            for row in result.fetchall():
                rows.append(dict(zip(columns, row)))
            
            count_query = text(f'SELECT COUNT(*) FROM "{table_name}"')
            total_count = connection.execute(count_query).scalar()
        
        data = {
            "table_name": table_name,
            "database": database_name,
            "columns": columns,
            "rows": rows,
            "total_count": total_count,
            "limit": limit,
            "returned_count": len(rows)
        }
        
        db_engine.dispose()
        return data
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching data from {table_name}: {str(e)}"
        )
