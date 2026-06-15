"""
Prompt Builder - Constructs LLM prompts from database metadata and join graphs
"""

from typing import List, Dict, Any


def build_table_metadata_context(table_metadata: Dict[str, Any]) -> str:
    """Build readable context for a single table."""
    table_name = table_metadata["name"]
    columns = table_metadata.get("columns", [])
    relationships = table_metadata.get("relationships", [])
    
    # Format columns
    column_lines = []
    for col in columns:
        col_type = col.get("type", "UNKNOWN")
        nullable = "NULL" if col.get("nullable", True) else "NOT NULL"
        pk_marker = " [PRIMARY KEY]" if col.get("primary_key", False) else ""
        column_lines.append(f"  - {col['name']}: {col_type} {nullable}{pk_marker}")
    
    # Format relationships
    relationship_lines = []
    for rel in relationships:
        rel_desc = f"  - {rel['source_table']}.{rel['source_column']} → {rel['target_table']}.{rel['target_column']}"
        relationship_lines.append(rel_desc)
    
    context = f"\nTable: {table_name}\n"
    context += "Columns:\n" + "\n".join(column_lines) if column_lines else "Columns: None\n"
    
    if relationship_lines:
        context += "\n\nRelationships (Foreign Keys):\n" + "\n".join(relationship_lines)
    
    return context


def build_join_graph_context(join_graph: Dict[str, Any], relevant_tables: List[str]) -> str:
    """Build readable context for join paths between relevant tables."""
    joins = join_graph.get("joins", [])
    
    # If no relevant tables specified (empty list from embedder), show all joins
    if not relevant_tables:
        if not joins:
            return "\nNo relationships found in the database."
        lines = ["\nJoin Paths (All available relationships):"]
        for join in joins:
            line = (f"  - {join['source_table']}.{join['source_column']} "
                    f"= {join['target_table']}.{join['target_column']}")
            lines.append(line)
        return "\n".join(lines)
    
    # Filter joins that connect our relevant tables
    relevant_joins = [
        j for j in joins 
        if j["source_table"] in relevant_tables and j["target_table"] in relevant_tables
    ]
    
    if not relevant_joins:
        return "\nNo direct relationships found between selected tables."
    
    lines = ["\nJoin Paths (How to connect the tables):"]
    for join in relevant_joins:
        line = (f"  - {join['source_table']}.{join['source_column']} "
                f"= {join['target_table']}.{join['target_column']}")
        lines.append(line)
    
    return "\n".join(lines)


def build_sql_generation_prompt(
    query_text: str,
    relevant_tables: List[str],
    table_metadata: List[Dict[str, Any]],
    join_graph: Dict[str, Any],
    database_name: str
) -> str:
    """
    Build a comprehensive prompt for SQL generation.
    
    Args:
        query_text: The natural language query from user
        relevant_tables: List of table names identified as relevant
        table_metadata: FULL metadata for all tables in database
        join_graph: Join graph for the database
        database_name: Name of the database
    
    Returns:
        Formatted prompt string for LLM
    """
    
    # Use ALL table metadata provided (full database schema)
    # This gives LLM complete context of the database
    table_contexts = [build_table_metadata_context(t) for t in table_metadata]
    
    # Build join context
    join_context = build_join_graph_context(join_graph, relevant_tables)
    
    prompt = f"""You are a SQL expert. Generate a SQL SELECT query to answer the following question.

Database: {database_name}

Question: {query_text}

Relevant Tables and Schemas:
{"".join(table_contexts)}

{join_context}

Instructions:
1. Generate ONLY a valid SQL SELECT query (no explanation or markdown)
2. Use the table schemas provided above
3. IMPORTANT: Select ONLY the specific columns mentioned in the question
   - If user asks for "names", select the name column (Full_name, name, etc.)
   - If user asks for "all", then use SELECT *
   - Match column names based on semantic meaning
4. Include necessary JOINs if multiple tables are required
5. Use appropriate WHERE clauses to filter the data
6. Return query in single line without formatting
7. Ensure the query is valid PostgreSQL syntax

Return ONLY the SQL query, nothing else."""

    return prompt



def build_query_analysis_prompt(
    query_text: str,
    relevant_tables: List[str],
    table_metadata: List[Dict[str, Any]],
    join_graph: Dict[str, Any],
    database_name: str
) -> str:
    """
    Build a prompt for analyzing query requirements.
    
    Args:
        query_text: The natural language query from user
        relevant_tables: List of table names identified as relevant
        table_metadata: Metadata for all tables in database
        join_graph: Join graph for the database
        database_name: Name of the database
    
    Returns:
        Formatted analysis prompt string for LLM
    """
    
    # Filter metadata to only relevant tables
    relevant_metadata = [
        t for t in table_metadata 
        if t["name"] in relevant_tables
    ]
    
    # Build table details
    table_contexts = [build_table_metadata_context(t) for t in relevant_metadata]
    
    # Build join context
    join_context = build_join_graph_context(join_graph, relevant_tables)
    
    prompt = f"""Analyze the following database query and provide details.

Database: {database_name}

Question: {query_text}

Relevant Tables and Schemas:
{"".join(table_contexts)}

{join_context}

Provide:
1. A brief description of what the query intends to do
2. Which columns should be selected
3. Which tables need to be joined (if any)
4. What WHERE conditions are needed (if any)
5. Any other relevant SQL considerations

Be concise and focus on SQL generation requirements."""

    return prompt
