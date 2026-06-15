"""
Global Application State
Manages shared state like JOIN_GRAPHS and METADATA that needs to be accessible
across different route modules
"""

from typing import List, Dict, Any

# Global variable to store join graphs for all databases
_JOIN_GRAPHS: List[Dict[str, Any]] = []

# Global variable to store metadata for all databases
_METADATA: List[Dict[str, Any]] = []


def set_join_graphs(graphs: List[Dict[str, Any]]) -> None:
    """Set the join graphs for all databases"""
    global _JOIN_GRAPHS
    _JOIN_GRAPHS = graphs


def get_join_graphs() -> List[Dict[str, Any]]:
    """Get the join graphs for all databases"""
    return _JOIN_GRAPHS


def clear_join_graphs() -> None:
    """Clear the join graphs"""
    global _JOIN_GRAPHS
    _JOIN_GRAPHS = []


def set_metadata(metadata: List[Dict[str, Any]]) -> None:
    """Set the metadata for all databases"""
    global _METADATA
    _METADATA = metadata


def get_metadata() -> List[Dict[str, Any]]:
    """Get the metadata for all databases"""
    return _METADATA


def clear_metadata() -> None:
    """Clear the metadata"""
    global _METADATA
    _METADATA = []
