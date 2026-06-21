"""
Metadata Builder - Builds comprehensive database metadata at startup
Includes database structure, tables, columns, and relationships
"""

from sqlalchemy import inspect
from typing import Dict, List, Any
import sys
from pathlib import Path

# Add parent directory to path to import db module
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from backend.db.db import get_engine


def _format_columns(columns: List[Any], primary_keys: List[str]) -> List[Dict[str, Any]]:
    """Format column information with types and constraints."""
    return [
        {
            "name": col["name"],
            "type": str(col["type"]),
            "nullable": col["nullable"],
            "primary_key": col["name"] in primary_keys,
            "default": col["default"]
        }
        for col in columns
    ]


def _format_relationships(table_name: str, foreign_keys: List[Dict]) -> List[Dict[str, Any]]:
    """Format foreign key relationships."""
    return [
        {
            "source_table": table_name,
            "target_table": fk["referred_table"],
            "source_column": fk["constrained_columns"][0] if fk["constrained_columns"] else None,
            "target_column": fk["referred_columns"][0] if fk["referred_columns"] else None,
            "constraint_name": fk.get("name", "")
        }
        for fk in foreign_keys
    ]


def _format_constraints(inspector: Any, table_name: str, primary_keys: List[str], foreign_keys: List[Dict]) -> Dict[str, Any]:
    """Format all table constraints."""
    return {
        "primary_key": primary_keys if primary_keys else [],
        "unique": inspector.get_unique_constraints(table_name) if inspector.get_unique_constraints(table_name) else [],
        "check": inspector.get_check_constraints(table_name) if inspector.get_check_constraints(table_name) else [],
        "foreign_keys": foreign_keys if foreign_keys else []
    }


def _extract_table_metadata(inspector: Any, table_name: str) -> Dict[str, Any]:
    """Extract complete metadata for a single table."""
    columns = inspector.get_columns(table_name)
    pk_constraint = inspector.get_pk_constraint(table_name)
    primary_keys = pk_constraint["constrained_columns"] if pk_constraint else []
    foreign_keys = inspector.get_foreign_keys(table_name)
    
    return {
        "name": table_name,
        "columns": _format_columns(columns, primary_keys),
        "relationships": _format_relationships(table_name, foreign_keys),
        "constraints": _format_constraints(inspector, table_name, primary_keys, foreign_keys)
    }


def build_metadata_for_database(database_name: str) -> Dict[str, Any]:
    """Build complete metadata for a specific database."""
    try:
        db_engine = get_engine(database_name)
        inspector = inspect(db_engine)
        
        tables_metadata = [
            _extract_table_metadata(inspector, table_name)
            for table_name in inspector.get_table_names()
        ]
        
        db_engine.dispose()
        return {"db_name": database_name, "tables": tables_metadata}
    
    except Exception as e:
        print(f"❌ Error building metadata for {database_name}: {str(e)}")
        return {"db_name": database_name, "tables": [], "error": str(e)}


def build_all_metadata(database_list: List[str]) -> List[Dict[str, Any]]:
    """Build complete metadata for all databases."""
    all_metadata = []
    
    for db_name in database_list:
        print(f"📋 Building metadata for database: {db_name}")
        metadata = build_metadata_for_database(db_name)
        all_metadata.append(metadata)
        tables_count = len(metadata.get("tables", []))
        print(f"✅ Metadata built for {db_name}: {tables_count} tables")
    
    return all_metadata
