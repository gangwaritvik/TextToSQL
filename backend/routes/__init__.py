"""
API Routes for Text-to-SQL Backend
Aggregates all route modules
"""

from .query import router as query_router
from .database.main import router as databases_router
from .join_graphs import router as join_graphs_router
from .metadata import router as metadata_router
from .upload import router as upload_router

__all__ = ["query_router", "databases_router", "join_graphs_router", "metadata_router", "upload_router"]
