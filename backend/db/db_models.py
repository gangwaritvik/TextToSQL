"""
Database Models
Pydantic models for API request/response validation
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class QueryRequest(BaseModel):
    """Request model for query endpoint"""
    query: str = Field(..., description="Natural language query")
    database: str = Field(..., description="Database name to query")


class QueryResponse(BaseModel):
    """Response model for query endpoint"""
    id: int = Field(..., description="Result ID")
    query: str = Field(..., description="Original query")
    database: str = Field(..., description="Database used")
    tables: List[str] = Field(..., description="Tables involved")
    joinPath: str = Field(..., description="Join path if multiple tables")
    confidence: float = Field(..., description="Confidence score")
    sql: str = Field(..., description="Generated SQL")
    results: List[Dict[str, Any]] = Field(..., description="Query results")
    summary: str = Field(..., description="Result summary")
    executionTime: str = Field(..., description="Execution time")
    tokensUsed: str = Field(..., description="Tokens used")
    complexity: str = Field(..., description="Query complexity")
    executionError: Optional[str] = Field(None, description="Error message if operation was blocked")


class ColumnInfo(BaseModel):
    """Column information"""
    name: str
    type: str
    nullable: bool
    primary_key: bool
    default: Optional[str] = None


class TableInfo(BaseModel):
    """Table information"""
    name: str
    schema_name: str
    rows: int


class TableSchema(BaseModel):
    """Detailed table schema"""
    table_name: str
    database: str
    columns: List[ColumnInfo]
    primary_keys: List[str]
    foreign_keys: List[Dict[str, Any]]
    column_count: int


class TableData(BaseModel):
    """Table data with metadata"""
    table_name: str
    database: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    total_count: int
    limit: int
