"""
Utility modules for Text-to-SQL application
- Database metadata extraction
- Join graph construction
- Prompt building
- Query logging
- Application state management
"""

from .metadata_builder import build_metadata_for_database, build_all_metadata
from .join_graph_builder import build_join_graph_for_database, build_all_join_graphs
from .prompt_builder import build_sql_generation_prompt
from .logger import get_query_logger, log_query, cleanup_logs
from .state import (
    get_join_graphs,
    set_join_graphs,
    get_metadata,
    set_metadata,
    clear_join_graphs,
    clear_metadata,
)

__all__ = [
    "build_metadata_for_database",
    "build_all_metadata",
    "build_join_graph_for_database",
    "build_all_join_graphs",
    "build_sql_generation_prompt",
    "get_query_logger",
    "log_query",
    "cleanup_logs",
    "get_join_graphs",
    "set_join_graphs",
    "get_metadata",
    "set_metadata",
    "clear_join_graphs",
    "clear_metadata",
]
