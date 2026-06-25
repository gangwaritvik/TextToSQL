"""
Metadata Routes
GET /metadata - Get all metadata
GET /metadata/{database_name} - Get metadata for specific database
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from backend.utils.state import get_metadata

router = APIRouter(
    prefix="/metadata",
    tags=["metadata"],
    responses={404: {"description": "Not found"}},
)


@router.get("")
def get_all_metadata() -> Dict[str, Any]:
    """Get metadata for all databases"""
    METADATA = get_metadata()
    
    if not METADATA:
        raise HTTPException(
            status_code=503,
            detail="Metadata not yet initialized. Please try again in a moment."
        )
    
    return {
        "status": "success",
        "databases_count": len(METADATA),
        "databases": [m["database"] for m in METADATA],
        "metadata": METADATA
    }


@router.get("/{database_name}")
def get_database_metadata(database_name: str) -> Dict[str, Any]:
    """Get metadata for a specific database"""
    METADATA = get_metadata()
    
    if not METADATA:
        raise HTTPException(
            status_code=503,
            detail="Metadata not yet initialized."
        )
    
    # Find the metadata for this database
    metadata = None
    for m in METADATA:
        if m["database"] == database_name:
            metadata = m
            break
    
    if metadata is None:
        raise HTTPException(
            status_code=404,
            detail=f"Metadata not found for database: {database_name}"
        )
    
    return {
        "status": "success",
        "database": database_name,
        "tables_count": len(metadata.get("tables", [])),
        "tables": metadata.get("tables", []),
        "metadata": metadata
    }
