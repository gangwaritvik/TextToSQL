"""
File Upload Routes
POST /upload - Upload one or more CSV/Excel files
GET /uploaded-tables - Get list of uploaded tables
DELETE /uploaded-tables/{table_name} - Delete uploaded table
"""

from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import List, Dict, Any

from backend.core.file_handler import get_file_upload_handler

router = APIRouter(
    prefix="/upload",
    tags=["upload"],
    responses={404: {"description": "Not found"}},
)


@router.post("")
async def upload_files(
    files: List[UploadFile] = File(...),
    database: str = Query("fastapi_db")
) -> Dict[str, Any]:
    """
    Upload one or more CSV/Excel files and create a temporary table for each.

    - **files**: One or more CSV or Excel files to upload
    - **database**: Target database name (default: fastapi_db)

    Each file is processed independently so one bad file does not abort the
    others. Returns the tables created plus per-file errors.

    Returns: ``{ success, uploaded: [...], failed: [...], total, succeeded }``
    """
    valid_extensions = {'.csv', '.xlsx', '.xls'}
    handler = get_file_upload_handler()

    uploaded: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []

    for file in files:
        try:
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in valid_extensions:
                failed.append({
                    "filename": file.filename,
                    "error": f"Invalid file type. Supported: {sorted(valid_extensions)}"
                })
                continue

            content = await file.read()
            if not content:
                failed.append({"filename": file.filename, "error": "File is empty"})
                continue

            result = handler.upload_file(content, file.filename, database)
            if not result.get("success"):
                failed.append({
                    "filename": file.filename,
                    "error": result.get("error", "Upload failed")
                })
                continue

            uploaded.append({
                "table_name": result["table_name"],
                "filename": result["filename"],
                "rows": result["rows"],
                "columns": result["columns"],
            })
        except Exception as e:
            failed.append({"filename": file.filename, "error": str(e)})

    # Only fail the whole request when nothing could be uploaded.
    if not uploaded:
        detail = "; ".join(f"{f['filename']}: {f['error']}" for f in failed) or "Upload failed"
        raise HTTPException(status_code=400, detail=detail)

    return {
        "success": True,
        "uploaded": uploaded,
        "failed": failed,
        "total": len(files),
        "succeeded": len(uploaded),
    }


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
