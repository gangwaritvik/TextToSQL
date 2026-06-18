"""
Azure OpenAI Client Configuration
Initializes and provides Azure OpenAI client for embeddings and LLM operations
"""

import os
from dotenv import load_dotenv
from openai import AzureOpenAI, AsyncAzureOpenAI

# Load environment variables
load_dotenv(".env.local")

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# Initialize Azure OpenAI client (synchronous)
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT
)

# Initialize Azure OpenAI client (asynchronous) for concurrent I/O such as
# parallel embedding requests. Shares the same configuration as the sync client.
async_client = AsyncAzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT
)


def get_azure_client() -> AzureOpenAI:
    """Get the synchronous Azure OpenAI client instance"""
    return client


def get_async_azure_client() -> AsyncAzureOpenAI:
    """Get the asynchronous Azure OpenAI client instance"""
    return async_client


def get_embedding_model() -> str:
    """Get the embedding model name"""
    return EMBEDDING_MODEL
