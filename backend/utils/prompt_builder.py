"""
Prompt Builder - Constructs LLM prompts from database metadata and join graphs
"""

from typing import List, Dict, Any


def _format_sample_value(value: Any, max_len: int = 40) -> str:
    """Render a single cell value compactly for the prompt."""
    if value is None:
        return "NULL"
    text = str(value)
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def build_sample_data_context(sample_rows: List[Dict[str, Any]]) -> str:
    """Build a compact text table of sample rows for a single table."""
    if not sample_rows:
        return ""

    headers = list(sample_rows[0].keys())
    lines = [f"\nSample rows (up to {len(sample_rows)}):"]
    lines.append("  " + " | ".join(headers))
    for row in sample_rows:
        lines.append("  " + " | ".join(_format_sample_value(row.get(h)) for h in headers))

    return "\n".join(lines)


def build_table_metadata_context(table_metadata: Dict[str, Any]) -> str:
    """Build readable context for a single table."""
    table_name = table_metadata["name"]
    columns = table_metadata.get("columns", [])
    relationships = table_metadata.get("relationships", [])
    sample_rows = table_metadata.get("sample_rows", [])
    
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
    
    sample_context = build_sample_data_context(sample_rows)
    if sample_context:
        context += "\n" + sample_context
    
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
1. Analyze if this request is asking for a DANGEROUS operation (DELETE, DROP, UPDATE, INSERT, etc.)
2. Generate a valid SQL SELECT query to answer the question
3. BEFORE writing the SQL, you MUST inspect the "Sample rows" of the target table and
   reason about the actual VALUES (not just column names) in the ANALYSIS step:
   - For each thing the user asked for, look at the sample VALUES to decide whether that
     value lives entirely in ONE column or is split across MULTIPLE columns.
   - A column whose name matches the request is NOT automatically the complete answer.
     Example: a column literally named "name" may hold only the first name while another
     column holds the rest — judge by the sample values, not the column name.
   - If the requested value is split across multiple columns (each column holds a PART of
     the SAME item), concatenate those columns into one labeled result with string
     concatenation and AS — do not return only one part.
   - The PARTS may live in DIFFERENT tables. If one table holds part of the value and
     another table holds the rest for the SAME entity, JOIN the tables on the column whose
     sample VALUES match across them (e.g. the same id appears in both), then concatenate
     the parts. Example: first name in one table and last name in another, both keyed by
     the same user id — JOIN on that id and combine into the full name.
   - Do NOT merge columns that hold independent values (e.g. two different phone numbers,
     separate emails, unrelated fields) — keep those separate.
   - If one column already holds the complete value, select it as-is.
   - If the user asks for "all", then use SELECT *.
4. Include necessary JOINs if multiple tables are required
5. Prefer the fewest tables needed. JOIN tables when the answer requires combining their
   columns for the same rows (matched by a shared key found in the sample values). Do NOT
   UNION / stack rows from separate tables unless the question explicitly asks to merge
   multiple datasets — two similar tables are NOT a reason to UNION them.
6. Use appropriate WHERE clauses to filter the data
7. Ensure the query is valid PostgreSQL syntax
8. Limit the decimal precision to 2 places for numeric columns.

Return your response in EXACTLY this format:
DANGEROUS: [YES/NO]
REASON: [Brief reason if dangerous, or "Safe to execute" if not]
ANALYSIS: [One line. Look at the target table's sample values and state, for each requested item, whether it is in one column or split across several columns, and which column(s) you will use]
SQL: [The SQL query in single line]

Examples:
DANGEROUS: NO
REASON: Safe to execute
ANALYSIS: User asked for product names and prices; sample values show product_name and price each hold the full value in a single column
SQL: SELECT product_name, price FROM products WHERE price > 1000

DANGEROUS: NO
REASON: Safe to execute
ANALYSIS: User asked for names; sample values show first_name holds only the first part (e.g. "Sheryl") and last_name holds the rest (e.g. "Baxter"), so the full name is split and must be combined
SQL: SELECT first_name || ' ' || last_name AS full_name FROM people

DANGEROUS: NO
REASON: Safe to execute
ANALYSIS: User asked for full name; first_name lives in table a and last_name in table b, and sample values show the same user_id in both, so JOIN on user_id and combine the parts
SQL: SELECT b.first_name || ' ' || a.last_name AS full_name FROM a JOIN b ON a.user_id = b.user_id

DANGEROUS: YES
REASON: User asked to delete customer records
ANALYSIS: Request is a destructive DELETE, not a SELECT
SQL: DELETE FROM customers WHERE id = 1"""

    return prompt
