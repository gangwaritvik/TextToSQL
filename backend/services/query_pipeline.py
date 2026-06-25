"""
Query Pipeline Service

Orchestrates the end-to-end natural-language-to-SQL flow:

    1. Embed the question and find relevant tables (semantic search)
    2. Collect metadata for those tables (+ any uploaded tables)
    3. Load the database join graph
    4. Generate SQL with the LLM (with danger assessment)
    5. Validate and execute the SQL
    6. Summarize the results and assemble the response

This module holds the business logic so the ``/query`` route stays thin.
"""

from typing import Any
import time
import asyncio
import logging

from fastapi import HTTPException

from backend.db import QueryRequest, QueryResponse
from backend.core.embedder import get_embedder
from backend.core.sql_generator import get_sql_generator
from backend.core.query_executor import get_query_executor
from backend.core.file_handler import FileUploadHandler
from backend.utils.state import get_metadata, get_join_graphs
from backend.utils.join_graph_builder import extract_join_path_from_sql
from backend.utils.logger import log_query

logger = logging.getLogger(__name__)


def calculate_complexity(sql_query: str) -> str:
    """Rate a SQL query's complexity from its structure (joins, subqueries, etc.)."""
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


async def run_query_pipeline(request: QueryRequest) -> QueryResponse:
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

    logger.info("="*80)
    logger.info("🔍 NEW QUERY RECEIVED")
    logger.info("="*80)
    logger.info(f"Query: {request.query}")
    logger.info(f"Database: {request.database}")

    try:
        embedder = get_embedder()
        sql_generator = get_sql_generator()
        query_executor = get_query_executor()
        database = request.database
        query_text = request.query

        # Uploaded tables take part in the SAME semantic search as schema tables.
        # Reconcile them into the vector index first (embed new uploads, drop
        # deleted ones) so that relevance — not special-casing — decides which
        # tables reach the LLM.
        uploaded_tables = FileUploadHandler.get_uploaded_tables(database)
        await embedder.reconcile_uploaded_tables(database, uploaded_tables)

        # Step 1 & 2: Search for relevant tables using async embedding (much faster!)
        logger.info("📍 Step 1: Searching for relevant tables using embeddings...")
        search_start = time.time()

        relevant_tables = await embedder.search_similar_tables(
            database_name=database,
            query_text=query_text,
            k=5,  # Get up to 5 relevant tables
            similarity_threshold=2.5  # Filter tables by similarity (L2 distance <= 2.5)
        )

        table_names = [table["table"] for table in relevant_tables]
        search_time = time.time() - search_start
        if relevant_tables:
            distances_info = " | ".join([f"{t['table']}(dist={t['distance']:.2f})" for t in relevant_tables])
            logger.info(f"✅ Found {len(table_names)} relevant tables in {search_time:.2f}s: {distances_info}")
        else:
            logger.info(f"✅ Found {len(table_names)} relevant tables in {search_time:.2f}s (no tables met similarity threshold)")

        # Step 2: Get FULL metadata for all tables in database
        logger.info("📍 Step 2: Fetching database metadata...")

        all_metadata = get_metadata()
        all_database_tables = []

        for db_meta in all_metadata:
            if db_meta.get("db_name") == database:
                all_database_tables = db_meta.get("tables", [])
                break

        # FILTER: Only include metadata for relevant tables retrieved in Step 1.
        # Each relevant table is either a schema table or an uploaded table — both
        # came from the same semantic search above. Build the list in ranked
        # (most-relevant-first) order so the prompt leads with the best match.
        uploaded_by_name = {t["name"]: t for t in uploaded_tables}
        schema_by_name = {t["name"]: t for t in all_database_tables}

        database_metadata = []
        for name in table_names:
            if name in uploaded_by_name:
                ut = uploaded_by_name[name]
                database_metadata.append({
                    "name": ut["name"],
                    "columns": ut.get("columns", []),
                    "rows": ut.get("rows", 0),
                    "uploaded": True,
                    "filename": ut.get("filename", ""),
                })
            elif name in schema_by_name:
                database_metadata.append(schema_by_name[name])

        uploaded_count = sum(1 for t in database_metadata if t.get("uploaded"))
        logger.info(f"✅ Fetched metadata for {len(database_metadata)} tables ({uploaded_count} uploaded, {len(database_metadata)-uploaded_count} from schema)")
        if uploaded_tables:
            logger.info(f"   Uploaded tables available: {[t['name'] for t in uploaded_tables]}")
        logger.info(f"   Tables selected by relevance: {table_names}")

        # Log full metadata for debugging
        logger.info(f"📊 DEBUG: database_metadata contains {len(database_metadata)} tables:")
        for table in database_metadata:
            logger.info(f"   - {table['name']} (uploaded={table.get('uploaded', False)})")

        # Step 2.5: Fetch a few sample rows per table so the LLM sees real data
        # (helps it pick the right column when names are similar/ambiguous)
        logger.info("📍 Step 2.5: Fetching sample rows for tables...")
        sample_start = time.time()

        async def _attach_sample_rows(table_meta: dict) -> None:
            rows = await asyncio.to_thread(
                query_executor.get_sample_rows, table_meta["name"], database, 3
            )
            table_meta["sample_rows"] = rows

        await asyncio.gather(*[_attach_sample_rows(tm) for tm in database_metadata])
        total_samples = sum(len(tm.get("sample_rows", [])) for tm in database_metadata)
        logger.info(
            f"✅ Fetched sample rows for {len(database_metadata)} tables "
            f"({total_samples} rows total) in {time.time() - sample_start:.2f}s"
        )

        # Step 3: Get join graph for the database
        logger.info("📍 Step 3: Fetching join graph...")

        all_join_graphs = get_join_graphs()
        database_join_graph = {}

        for join_graph in all_join_graphs:
            if join_graph.get("db_name") == database:
                database_join_graph = join_graph
                break

        if not database_join_graph:
            database_join_graph = {"db_name": database, "joins": []}

        join_count = len(database_join_graph.get("joins", []))
        logger.info(f"✅ Fetched join graph with {join_count} relationships")

        # Step 4: Generate SQL using LLM with full context (run in thread pool)
        logger.info("📍 Step 4: Generating SQL using Azure OpenAI...")
        sql_start = time.time()

        generated_sql, sql_tokens, is_operation_dangerous, danger_reason = await asyncio.to_thread(
            sql_generator.generate_sql,
            query_text,
            table_names,
            database_metadata,
            database_join_graph,
            database
        )

        sql_time = time.time() - sql_start
        logger.info(f"✅ SQL Generated in {sql_time:.2f}s ({sql_tokens} tokens)")
        logger.info(f"   SQL: {generated_sql[:200]}..." if len(generated_sql) > 200 else f"   SQL: {generated_sql}")

        if is_operation_dangerous:
            logger.warning(f"⚠️ DANGEROUS OPERATION DETECTED: {danger_reason}")

        # Step 5: Execute the generated SQL
        logger.info("📍 Step 5: Executing generated SQL...")
        exec_start = time.time()

        query_results = []
        execution_error = ""

        if generated_sql:
            # Check if LLM flagged this as dangerous operation
            if is_operation_dangerous:
                logger.error(f"❌ DANGEROUS OPERATION BLOCKED: {danger_reason}")
                execution_error = f"⚠️ DANGEROUS OPERATION DETECTED: {danger_reason}\n\nThe system detected this operation may modify or destroy data.\n\nFor safety, this operation is displayed but NOT EXECUTED.\n\nIf you need to modify data, please do it directly in your database."
            else:
                # Validate and execute query
                logger.info("   Validating query...")
                is_valid, validation_error = query_executor.validate_query(generated_sql)

                if is_valid:
                    logger.info("   Query is valid. Executing...")
                    query_results, execution_error = query_executor.execute_query(
                        sql_query=generated_sql,
                        database_name=database,
                        limit=100
                    )
                    exec_time = time.time() - exec_start
                    logger.info(f"✅ Query executed in {exec_time:.2f}s. Returned {len(query_results)} rows")
                else:
                    logger.error(f"❌ Query validation failed: {validation_error}")
                    execution_error = validation_error
        else:
            logger.error("❌ Failed to generate SQL query")
            execution_error = "Failed to generate SQL query"

        # Step 6: Generate AI summary (second LLM call in thread pool) or show error
        logger.info("📍 Step 6: Generating AI summary or showing error...")
        summary_start = time.time()

        # If operation was blocked, use execution error as summary
        if execution_error:
            summary = execution_error
            tokens_used = sql_tokens
            logger.info(f"Using execution error as summary: {execution_error[:80]}...")
        else:
            total_rows = len(query_results)
            all_rows = query_results if query_results else 'No results'
            summary_prompt = f"""Based on the following SQL query and its FULL result set, write a summary  of what the data shows. You may note key trends, outliers, or interesting patterns. Be concise.

Query: {request.query}
SQL: {generated_sql}
Total rows returned: {total_rows}
Full results ({total_rows} row(s)): {all_rows}

Base any counts on the actual data above. Provide only the short summary, no additional text."""

            logger.info("📤 SUMMARY PROMPT:")
            logger.info("=" * 80)
            logger.info(summary_prompt)
            logger.info("=" * 80)

            try:
                logger.info("⏳ Waiting for summary response...")
                summary_response = await asyncio.to_thread(
                    sql_generator.model.invoke,
                    summary_prompt
                )
                summary = summary_response.content.strip()

                logger.info("📥 SUMMARY RESPONSE:")
                logger.info("=" * 80)
                logger.info(summary)
                logger.info("=" * 80)
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

                logger.info(f"💰 Summary tokens used: {summary_tokens}")

                # Combine tokens from SQL generation and summary
                try:
                    total_tokens = int(sql_tokens) + int(summary_tokens)
                    tokens_used = str(total_tokens)
                except:
                    tokens_used = sql_tokens if sql_tokens != "0" else summary_tokens

                summary_time = time.time() - summary_start
                logger.info(f"✅ Summary generated in {summary_time:.2f}s ({summary_tokens} tokens)")
                logger.info(f"   Summary: {summary[:100]}...")
            except Exception as e:
                logger.warning(f"⚠️  Failed to generate summary: {str(e)}")
                summary = f"Found {len(table_names)} relevant tables. Query returned {len(query_results)} rows."
                tokens_used = sql_tokens

        # Calculate query complexity based on SQL
        complexity = calculate_complexity(generated_sql)

        # Build final summary
        if execution_error:
            summary = f"Found {len(database_metadata)} tables. SQL generated but execution failed: {execution_error}"
        else:
            summary = summary

        # Get the actual table names that were sent to the LLM (includes uploaded tables)
        actual_tables_sent = [table["name"] for table in database_metadata]

        # Build join path from the joins ACTUALLY used in the generated SQL
        # (not the entire database's foreign-key graph). Single-table queries
        # therefore correctly show no join path.
        join_path = extract_join_path_from_sql(generated_sql)

        # Calculate total execution time
        execution_time = f"{int((time.time() - start_time) * 1000)}ms"

        response = QueryResponse(
            id=int(time.time() * 1000),
            query=request.query,
            database=request.database,
            tables=actual_tables_sent,
            joinPath=join_path,
            confidence=1.0 - relevant_tables[0]["distance"] if relevant_tables else 0.0,
            sql=generated_sql,
            results=query_results,
            summary=summary,
            executionTime=execution_time,
            tokensUsed=tokens_used,
            complexity=complexity,
            executionError=execution_error if execution_error else None
        )

        # Final logging
        total_time = time.time() - start_time
        uploaded_table_names = [t["name"] for t in uploaded_tables]
        tables_used_uploaded = [t for t in table_names if t in uploaded_table_names]

        logger.info("="*80)
        logger.info("✅ QUERY COMPLETED SUCCESSFULLY")
        logger.info("="*80)
        logger.info(f"Total Time: {total_time:.2f}s ({execution_time})")
        logger.info(f"Tables Used: {len(table_names)} - {table_names}")
        if tables_used_uploaded:
            logger.info(f"   📤 Uploaded tables used: {tables_used_uploaded}")
        logger.info(f"Results: {len(query_results)} rows")
        logger.info(f"Complexity: {complexity}")
        logger.info(f"Tokens Used: {tokens_used}")
        logger.info("="*80 + "\n")

        # Save query to log file
        log_query(
            query_text=request.query,
            database=request.database,
            tables=actual_tables_sent,
            sql=generated_sql,
            status="success" if not execution_error else "error"
        )

        return response

    except Exception as e:
        logger.error("="*80)
        logger.error(f"❌ ERROR PROCESSING QUERY")
        logger.error("="*80)
        logger.error(f"Error: {str(e)}", exc_info=True)
        logger.error("="*80 + "\n")

        # Log the failed query
        log_query(
            query_text=request.query,
            database=request.database,
            tables=[],
            sql="",
            status="failed"
        )

        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )
