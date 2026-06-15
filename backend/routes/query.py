"""
Query Processing Endpoint
POST /query - Process natural language query and return results
GET /query/search-tables - Search for similar tables using embeddings
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List
import sys
from pathlib import Path
import time
import asyncio

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.db import QueryRequest, QueryResponse
from backend.core.embedder import get_embedder
from backend.core.sql_generator import get_sql_generator
from backend.core.query_executor import get_query_executor
from backend.utils.state import get_metadata, get_join_graphs

router = APIRouter(
    prefix="/query",
    tags=["query"],
    responses={404: {"description": "Not found"}},
)


@router.post("", response_model=QueryResponse)
async def process_query(request: QueryRequest) -> Dict[str, Any]:
    """
    Process a natural language query asynchronously.
    
    1. Create embedding of the query (ASYNC)
    2. Find relevant tables using semantic search (ASYNC)
    3. Get metadata and join graph for relevant tables
    4. Generate SQL using Azure OpenAI with full context
    5. Execute generated SQL
    6. Return generated SQL, results, and query info
    """
    start_time = time.time()
    
    try:
        embedder = get_embedder()
        sql_generator = get_sql_generator()
        query_executor = get_query_executor()
        database = request.database
        query_text = request.query
        
        # Step 1 & 2: Search for relevant tables using async embedding (much faster!)
        relevant_tables = await embedder.search_similar_tables(
            database_name=database,
            query_text=query_text,
            k=5  # Get top 5 relevant tables
        )
        
        table_names = [table["table"] for table in relevant_tables]
        
        # Step 2: Get FULL metadata for all tables in database
        all_metadata = get_metadata()
        database_metadata = []
        
        for db_meta in all_metadata:
            if db_meta.get("db_name") == database:
                database_metadata = db_meta.get("tables", [])
                break
        
        if not database_metadata:
            database_metadata = []
        
        # Step 3: Get join graph for the database
        all_join_graphs = get_join_graphs()
        database_join_graph = {}
        
        for join_graph in all_join_graphs:
            if join_graph.get("db_name") == database:
                database_join_graph = join_graph
                break
        
        if not database_join_graph:
            database_join_graph = {"db_name": database, "joins": []}
        
        # Step 4: Generate SQL using LLM with full context (run in thread pool)
        generated_sql, sql_tokens = await asyncio.to_thread(
            sql_generator.generate_sql,
            query_text,
            table_names,
            database_metadata,
            database_join_graph,
            database
        )
        
        # Step 5: Execute the generated SQL
        query_results = []
        execution_error = ""
        
        if generated_sql:
            # Validate and execute query
            is_valid, validation_error = query_executor.validate_query(generated_sql)
            if is_valid:
                query_results, execution_error = query_executor.execute_query(
                    sql_query=generated_sql,
                    database_name=database,
                    limit=100
                )
            else:
                execution_error = validation_error
        else:
            execution_error = "Failed to generate SQL query"
        
        # Step 6: Generate AI summary (second LLM call in thread pool)
        summary_prompt = f"""Based on the following SQL query and results, provide a brief 2-3 sentence summary of what the data shows.

Query: {request.query}
SQL: {generated_sql}
Results: {query_results[:3] if query_results else 'No results'}

Provide only the summary, no additional text."""
        
        try:
            summary_response = await asyncio.to_thread(
                sql_generator.model.invoke,
                summary_prompt
            )
            summary = summary_response.content.strip()
            # Try to extract token usage if available
            summary_tokens = "0"
            try:
                if hasattr(summary_response, 'usage_metadata') and summary_response.usage_metadata:
                    summary_tokens = str(summary_response.usage_metadata.get('total_tokens', '0'))
                elif hasattr(summary_response, 'response_metadata') and summary_response.response_metadata:
                    token_usage = summary_response.response_metadata.get('token_usage', {})
                    summary_tokens = str(token_usage.get('total_tokens', '0'))
            except:
                summary_tokens = "0"
            
            # Combine tokens from SQL generation and summary
            try:
                total_tokens = int(sql_tokens) + int(summary_tokens)
                tokens_used = str(total_tokens)
            except:
                tokens_used = sql_tokens if sql_tokens != "0" else summary_tokens
        except:
            summary = f"Found {len(table_names)} relevant tables. Query returned {len(query_results)} rows."
            tokens_used = sql_tokens
        
        # Calculate query complexity based on SQL
        def calculate_complexity(sql_query: str) -> str:
            """Calculate query complexity based on SQL features"""
            sql_lower = sql_query.lower()
            
            complexity_score = 0
            
            # Count joins
            complexity_score += sql_lower.count(" join ")
            
            # Check for subqueries
            complexity_score += sql_lower.count("(select")
            
            # Check for aggregations
            if any(agg in sql_lower for agg in ["group by", "having", "sum(", "count(", "avg(", "max(", "min("]):
                complexity_score += 1
            
            # Check for unions
            complexity_score += sql_lower.count("union")
            
            # Check for window functions
            complexity_score += sql_lower.count("over (")
            
            if complexity_score == 0:
                return "Simple"
            elif complexity_score <= 2:
                return "Moderate"
            elif complexity_score <= 4:
                return "Complex"
            else:
                return "Very Complex"
        
        complexity = calculate_complexity(generated_sql)
        
        # Build final summary
        if execution_error:
            summary = f"Found {len(table_names)} tables. SQL generated but execution failed: {execution_error}"
        else:
            summary = summary
        
        # Build join path string from database_join_graph
        join_path = ""
        if database_join_graph.get("joins"):
            join_path = " → ".join([f"{join['source_table']}.{join.get('source_column', 'id')} = {join['target_table']}.{join.get('target_column', 'id')}" for join in database_join_graph["joins"]])
        
        # Calculate total execution time
        execution_time = f"{int((time.time() - start_time) * 1000)}ms"
        
        response = QueryResponse(
            id=int(time.time() * 1000),
            query=request.query,
            database=request.database,
            tables=table_names,
            joinPath=join_path,
            confidence=1.0 - relevant_tables[0]["distance"] if relevant_tables else 0.0,
            sql=generated_sql,
            results=query_results,
            summary=summary,
            executionTime=execution_time,
            tokensUsed=tokens_used,
            complexity=complexity
        )
        
        return response
    
    except Exception as e:
        print(f"❌ Error processing query: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )


@router.get("/search-tables")
def search_similar_tables(
    query: str = Query(..., description="Search query text"),
    database: str = Query(..., description="Database to search in"),
    k: int = Query(5, description="Number of results to return")
) -> Dict[str, Any]:
    """
    Search for tables similar to the query using embeddings.
    
    Uses semantic search to find the most relevant tables based on your query.
    """
    try:
        embedder = get_embedder()
        results = embedder.search_similar_tables_sync(database, query, k)
        
        return {
            "status": "success",
            "query": query,
            "database": database,
            "results_count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching tables: {str(e)}"
        )
