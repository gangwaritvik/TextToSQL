"""
Database Routes Main Router
Combines all database-related endpoints
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import inspect, text
from typing import List, Dict, Any
import re
from pydantic import BaseModel

from backend.db import get_engine
from backend.utils.db_registry import register_created_database

# Create main router with /databases prefix
router = APIRouter(
    prefix="/databases",
    tags=["databases"],
    responses={404: {"description": "Not found"}},
)


class CreateDatabaseRequest(BaseModel):
    """Request body for creating a new database."""
    name: str


def _sanitize_db_name(raw_name: str) -> str:
    """Turn a user-supplied name into a safe lowercase PostgreSQL identifier.

    Any character that is not a letter, digit or underscore is replaced with an
    underscore so the name can be used unquoted. Names that would start with a
    digit are prefixed with ``db_``. Raises ValueError if nothing usable remains.
    """
    name = re.sub(r'[^0-9a-zA-Z]+', '_', (raw_name or "").strip().lower()).strip('_')
    if not name:
        raise ValueError("Database name must contain at least one letter or digit.")
    if name[0].isdigit():
        name = f"db_{name}"
    # PostgreSQL identifiers are limited to 63 bytes
    return name[:63]


@router.post("")
def create_database(request: CreateDatabaseRequest) -> Dict[str, Any]:
    """Create a new PostgreSQL database.

    The supplied name is sanitized into a safe lowercase identifier. Returns the
    final database name that was created.
    """
    try:
        db_name = _sanitize_db_name(request.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        engine = get_engine()  # connect to the default database

        # Reject if a database with this name already exists
        with engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name},
            ).scalar()

        if exists:
            engine.dispose()
            raise HTTPException(
                status_code=400,
                detail=f"Database '{db_name}' already exists.",
            )

        # CREATE DATABASE cannot run inside a transaction block, so use AUTOCOMMIT.
        # db_name is sanitized to [a-z0-9_] only, so quoting it is safe.
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text(f'CREATE DATABASE "{db_name}"'))

        engine.dispose()

        # Record it as a temporary database so it is cleaned up on next startup
        register_created_database(db_name)

        return {"success": True, "database": db_name, "message": f"Database '{db_name}' created."}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create database: {str(e)}",
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
