"""
Join Graph Routes
GET /join-graphs - Get all join graphs
GET /join-graphs/{database_name} - Get join graph for specific database
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from backend.utils.state import get_join_graphs

router = APIRouter(
    prefix="/join-graphs",
    tags=["join-graphs"],
    responses={404: {"description": "Not found"}},
)


@router.get("")
def get_all_join_graphs() -> Dict[str, Any]:
    """Get join graphs for all databases"""
    JOIN_GRAPHS = get_join_graphs()
    
    if not JOIN_GRAPHS:
        raise HTTPException(
            status_code=503,
            detail="Join graphs not yet initialized. Please try again in a moment."
        )
    
    return {
        "status": "success",
        "databases_count": len(JOIN_GRAPHS),
        "databases": [g["db_name"] for g in JOIN_GRAPHS],
        "graphs": JOIN_GRAPHS
    }


@router.get("/{database_name}")
def get_join_graph(database_name: str) -> Dict[str, Any]:
    """Get join graph for a specific database"""
    JOIN_GRAPHS = get_join_graphs()
    
    if not JOIN_GRAPHS:
        raise HTTPException(
            status_code=503,
            detail="Join graphs not yet initialized."
        )
    
    # Find the graph for this database
    graph = None
    for g in JOIN_GRAPHS:
        if g["db_name"] == database_name:
            graph = g
            break
    
    if graph is None:
        raise HTTPException(
            status_code=404,
            detail=f"Join graph not found for database: {database_name}"
        )
    
    return {
        "status": "success",
        "database": database_name,
        "joins_count": len(graph.get("joins", [])),
        "graph": graph
    }
