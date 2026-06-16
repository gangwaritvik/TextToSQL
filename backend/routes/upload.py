"""
File Upload Routes
POST /upload - Upload CSV/Excel files
GET /uploaded-tables - Get list of uploaded tables
DELETE /uploaded-tables/{table_name} - Delete uploaded table
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import List, Dict, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.file_handler import get_file_upload_handler

router = APIRouter(
    prefix="/upload",
    tags=["upload"],
    responses={404: {"description": "Not found"}},
)


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    database: str = Query("fastapi_db")
) -> Dict[str, Any]:
    """
    Upload CSV or Excel file and create a temporary table.
    
    - **file**: CSV or Excel file to upload
    - **database**: Target database name (default: fastapi_db)
    
    Returns: Table metadata with name, columns, row count
    """
    try:
        # Validate file type
        valid_extensions = {'.csv', '.xlsx', '.xls'}
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in valid_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Supported: {valid_extensions}"
            )
        
        # Read file content
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Upload and create table
        handler = get_file_upload_handler()
        result = handler.upload_file(content, file.filename, database)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables")
async def get_uploaded_tables(database: str = Query("fastapi_db")) -> List[Dict[str, Any]]:
    """
    Get all uploaded tables for a specific database.
    
    - **database**: Database name (default: fastapi_db)
    
    Returns: List of uploaded table metadata
    """
    try:
        handler = get_file_upload_handler()
        tables = handler.get_uploaded_tables(database)
        return tables
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tables/{table_name}")
async def delete_uploaded_table(
    table_name: str,
    database: str = Query("fastapi_db")
) -> Dict[str, Any]:
    """
    Delete an uploaded table.
    
    - **table_name**: Name of the table to delete
    - **database**: Database name (default: fastapi_db)
    
    Returns: Confirmation message
    """
    try:
        handler = get_file_upload_handler()
        result = handler.delete_table(table_name, database)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
