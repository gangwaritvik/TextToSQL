"""
Query Processing Endpoints

POST /query               - Process a natural language query and return results
GET  /query/search-tables - Search for similar tables using embeddings

These handlers stay thin: the end-to-end query logic lives in
``backend.services.query_pipeline``.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
import logging

from backend.db import QueryRequest, QueryResponse
from backend.core.embedder import get_embedder
from backend.services.query_pipeline import run_query_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/query",
    tags=["query"],
    responses={404: {"description": "Not found"}},
)


@router.post("", response_model=QueryResponse)
async def process_query(request: QueryRequest) -> QueryResponse:
    """Process a natural language query and return SQL, results and a summary."""
    return await run_query_pipeline(request)


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
