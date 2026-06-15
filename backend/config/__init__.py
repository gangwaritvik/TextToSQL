"""
Backend Configuration
Centralized configuration for LLM and Azure services
"""

from .azure_client import get_azure_client, get_embedding_model

__all__ = ["get_azure_client", "get_embedding_model"]
