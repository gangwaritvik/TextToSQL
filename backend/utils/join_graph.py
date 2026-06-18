"""
Join Graph Builder - Creates adjacency lists from database foreign keys
Helps with understanding table relationships for query processing
"""

from sqlalchemy import inspect
from typing import Dict, List, Any, Tuple
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from backend.db.db import get_engine


def build_join_graph_for_database(database_name: str) -> Dict[str, Any]:
    """
    Build a join graph for a specific database.
    
    Returns a single database object (one element of the list):
    {
        "db_name": "database_name",
        "joins": [
            {
                "source_table": "table1",
                "target_table": "table2",
                "target_column": "id",
                "source_column": "table2_id",
                "constraint_name": "fk_..."
            },
            ...
        ]
    }
    
    This function is called by build_all_join_graphs() which returns a list of these objects.
    """
    try:
        db_engine = get_engine(database_name)
        inspector = inspect(db_engine)
        
        all_joins = []
        table_names = inspector.get_table_names()
        
        for table_name in table_names:
            # Get foreign keys (relationships)
            foreign_keys = inspector.get_foreign_keys(table_name)
            
            for fk in foreign_keys:
                join_info = {
                    "source_table": table_name,
                    "target_table": fk["referred_table"],
                    "target_column": fk["referred_columns"][0] if fk["referred_columns"] else None,
                    "source_column": fk["constrained_columns"][0] if fk["constrained_columns"] else None,
                    "constraint_name": fk.get("name", ""),
                    "all_target_columns": fk["referred_columns"],
                    "all_source_columns": fk["constrained_columns"]
                }
                all_joins.append(join_info)
        
        db_engine.dispose()
        
        return {
            "db_name": database_name,
            "joins": all_joins
        }
    
    except Exception as e:
        print(f"❌ Error building join graph for {database_name}: {str(e)}")
        return {
            "db_name": database_name,
            "joins": [],
            "error": str(e)
        }


def build_all_join_graphs(database_list: List[str]) -> List[Dict[str, Any]]:
    """
    Build join graphs for all databases.
    
    Args:
        database_list: List of database names
    
    Returns:
        [
            {
                "db_name": "database1",
                "joins": [...]
            },
            {
                "db_name": "database2",
                "joins": [...]
            },
            ...
        ]
    """
    all_graphs = []
    
    for db_name in database_list:
        print(f"🔗 Building join graph for database: {db_name}")
        graph = build_join_graph_for_database(db_name)
        all_graphs.append(graph)
        joins_count = len(graph.get("joins", []))
        print(f"✅ Join graph built for {db_name}: {joins_count} relationships")
    
    return all_graphs


def get_join_path(join_graph: Dict[str, Any], source_table: str, target_table: str, visited: set = None) -> List[Dict[str, Any]]:
    """
    Find a join path between two tables using BFS.
    
    join_graph format: {
        "db_name": "database_name",
        "joins": [...]
    }
    
    Returns:
        List of join dictionaries forming a path from source_table to target_table
    """
    if visited is None:
        visited = set()
    
    if source_table == target_table:
        return []
    
    if source_table in visited:
        return None
    
    visited.add(source_table)
    
    joins = join_graph.get("joins", [])
    
    # Check direct joins from source_table
    for join in joins:
        if join["source_table"] == source_table and join["target_table"] == target_table:
            return [join]
    
    # BFS for indirect paths
    for join in joins:
        if join["source_table"] == source_table:
            next_table = join["target_table"]
            if next_table not in visited:
                path = get_join_path(join_graph, next_table, target_table, visited.copy())
                if path is not None:
                    return [join] + path
    
    return None


def print_join_graph(join_graph: Dict[str, Any]) -> None:
    """Pretty print join graph for debugging"""
    print(f"\n{'='*60}")
    print(f"📊 Join Graph for Database: {join_graph['db_name']}")
    print(f"{'='*60}")
    
    joins = join_graph.get("joins", [])
    
    if not joins:
        print("   No relationships found")
    else:
        print(f"   Total relationships: {len(joins)}\n")
        for idx, join in enumerate(joins, 1):
            print(f"   {idx}. {join['source_table']}.{join['source_column']} → {join['target_table']}.{join['target_column']}")
            if join.get("constraint_name"):
                print(f"      (FK: {join['constraint_name']})")
    
    print("="*60)


def extract_join_path_from_sql(sql_query: str) -> str:
    """
    Build the join path from the JOIN ... ON clauses actually present in a
    generated SQL statement.

    Unlike the full database join graph (which lists every foreign-key
    relationship in the database), this reflects only the joins the query
    really uses, so single-table queries correctly produce an empty join path.

    Returns:
        A string of "left = right" conditions joined by ' → ', or '' when the
        query performs no joins.
    """
    if not sql_query:
        return ""

    # Capture the condition following each ON, up to the next SQL clause keyword.
    pattern = re.compile(
        r"\bON\b\s+(.+?)"
        r"(?=\s+(?:INNER\s+|LEFT\s+|RIGHT\s+|FULL\s+|CROSS\s+|OUTER\s+)*JOIN\b"
        r"|\s+WHERE\b|\s+GROUP\s+BY\b|\s+ORDER\s+BY\b|\s+HAVING\b"
        r"|\s+LIMIT\b|\s+OFFSET\b|\s+UNION\b|\s*\)|\s*;|\s*$)",
        re.IGNORECASE | re.DOTALL,
    )

    conditions = []
    for match in pattern.finditer(sql_query):
        condition = re.sub(r"\s+", " ", match.group(1).strip())
        if condition:
            conditions.append(condition)

    return " → ".join(conditions)