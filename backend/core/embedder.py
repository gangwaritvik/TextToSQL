"""
Database Table Embedder with Azure OpenAI
Embeds table schemas for semantic search using Azure OpenAI embeddings
"""

import asyncio
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import sys

# Database utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from backend.db.db import get_engine
from backend.utils.state import get_metadata
from backend.core.vector_store import get_vector_store
from backend.config.azure_client import get_azure_client, get_async_azure_client, get_embedding_model
from sqlalchemy import text

# Get Azure clients and embedding model
client = get_azure_client()
async_client = get_async_azure_client()
EMBEDDING_MODEL = get_embedding_model()

# Bound the number of concurrent embedding requests so we parallelize without
# overrunning Azure OpenAI rate limits. Configurable via EMBEDDING_CONCURRENCY.
EMBEDDING_CONCURRENCY = int(os.getenv("EMBEDDING_CONCURRENCY", "10"))
_embedding_semaphore = asyncio.Semaphore(EMBEDDING_CONCURRENCY)



class DatabaseEmbedder:
    """Embeds database tables using Azure OpenAI embeddings"""
    
    def __init__(self):
        self.vector_store = get_vector_store()
        
    async def embed_text(self, text: str) -> List[float]:
        """Get embedding from Azure OpenAI (async, bounded concurrency)"""
        try:
            # Ensure text is a string and not empty
            if not isinstance(text, str):
                text = str(text)
            
            if not text or not text.strip():
                raise ValueError("Empty text cannot be embedded")
            
            # Use the async client so concurrent embed_text calls actually run
            # in parallel; the semaphore caps simultaneous in-flight requests.
            async with _embedding_semaphore:
                response = await async_client.embeddings.create(
                    input=text,
                    model=EMBEDDING_MODEL
                )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ Embedding error for text (len={len(text) if isinstance(text, str) else 'N/A'}): {str(e)}")
            raise
    
    async def get_table_metadata(self, database_name: str, table_name: str) -> str:
        """Get table schema from cached metadata (already built in parallel)"""
        try:
            # Get metadata from backend state (already cached)
            all_metadata = get_metadata()
            
            # Find metadata for this database and table
            for db_meta in all_metadata:
                if db_meta["db_name"] == database_name:
                    for table_meta in db_meta.get("tables", []):
                        if table_meta["name"] == table_name:
                            # Format metadata as readable text
                            metadata_text = f"Table: {table_name}\n"
                            metadata_text += f"Database: {database_name}\n\n"
                            
                            metadata_text += "Columns:\n"
                            for col in table_meta.get("columns", []):
                                nullable = "nullable" if col.get("nullable") else "NOT NULL"
                                col_type = str(col.get("type", "UNKNOWN"))
                                primary_key = " [PRIMARY KEY]" if col.get("primary_key") else ""
                                metadata_text += f"  - {col['name']}: {col_type} ({nullable}){primary_key}\n"
                            
                            if table_meta.get("relationships"):
                                metadata_text += "\nRelationships:\n"
                                for rel in table_meta.get("relationships", []):
                                    metadata_text += f"  - {rel}\n"
                            
                            if table_meta.get("constraints"):
                                constraints = table_meta["constraints"]
                                if constraints.get("foreign_keys"):
                                    metadata_text += "\nForeign Keys:\n"
                                    for fk in constraints["foreign_keys"]:
                                        metadata_text += f"  - {fk}\n"
                            
                            return metadata_text
            
            # Fallback: if not found in cache, create basic metadata
            print(f"⚠️  Metadata not found for {database_name}.{table_name}, using fallback")
            fallback_text = f"Table: {table_name}\nDatabase: {database_name}\n"
            return fallback_text
            
        except Exception as e:
            print(f"❌ Error fetching cached metadata for {table_name}: {str(e)}")
            fallback_text = f"Table: {table_name}\nDatabase: {database_name}\n"
            return fallback_text
    
    
    async def embed_table(self, database_name: str, table_name: str) -> Optional[Dict[str, Any]]:
        """Embed a single table using cached metadata only"""
        try:
            print(f"  📝 Embedding {database_name}.{table_name}...")
            
            # Get metadata (no database query needed - already cached)
            metadata = await self.get_table_metadata(database_name, table_name)
            
            if not metadata:
                print(f"⚠️  No metadata found for {table_name}")
                return None
            
            # Get embedding
            embedding = await self.embed_text(metadata)
            
            embedding_entry = {
                "database": database_name,
                "table": table_name,
                "embedding": embedding,
                "metadata": metadata,
                "timestamp": datetime.now().isoformat()
            }
            
            return embedding_entry
        except Exception as e:
            print(f"❌ Error embedding {table_name}: {str(e)}")
            return None
    
    async def embed_database_tables(self, database_name: str) -> List[Dict[str, Any]]:
        """Embed all tables in a database concurrently using cached metadata"""
        try:
            # Get cached metadata
            all_metadata = get_metadata()
            
            # Find tables for this database
            table_names = []
            for db_meta in all_metadata:
                if db_meta["db_name"] == database_name:
                    table_names = [t["name"] for t in db_meta.get("tables", [])]
                    break
            
            print(f"\n🔗 Embedding database: {database_name} ({len(table_names)} tables)")
            
            # Create tasks for all tables
            tasks = [
                self.embed_table(database_name, table_name)
                for table_name in table_names
            ]
            
            # Run concurrently
            embeddings = await asyncio.gather(*tasks)
            
            # Filter out None results
            embeddings = [e for e in embeddings if e is not None]
            
            print(f"✅ Embedded {len(embeddings)}/{len(table_names)} tables in {database_name}")
            
            return embeddings
        except Exception as e:
            print(f"❌ Error embedding database {database_name}: {str(e)}")
            return []
    
    async def embed_all_databases(self, databases: Optional[List[str]] = None) -> Dict[str, Any]:
        """Embed all databases concurrently using cached metadata"""
        try:
            # Get databases from cached metadata if not provided
            if not databases:
                all_metadata = get_metadata()
                databases = [db_meta["db_name"] for db_meta in all_metadata]
            
            print("\n" + "="*60)
            print("🚀 DATABASE EMBEDDER - INITIALIZING (using cached metadata)")
            print("="*60)
            print(f"📊 Found {len(databases)} databases: {databases}")
            
            # Create concurrent tasks for each database
            tasks = [
                self.embed_database_tables(db_name)
                for db_name in databases
            ]
            
            # Run all database embeddings concurrently
            all_embeddings = await asyncio.gather(*tasks)
            
            # Flatten results
            all_embeddings_flat = []
            for embeddings in all_embeddings:
                all_embeddings_flat.extend(embeddings)
            
            # Store embeddings using vector store
            vector_store = get_vector_store()
            await vector_store.build_faiss_indices(all_embeddings_flat)
            
            print("\n✅ All embeddings completed!")
            print("="*60 + "\n")
            
            return {
                "status": "success",
                "databases_processed": len(databases),
                "total_tables_embedded": len(all_embeddings_flat),
                "embeddings": all_embeddings_flat
            }
        except Exception as e:
            print(f"❌ Error in embed_all_databases: {str(e)}")
            raise
    
    async def search_similar_tables(self, database_name: str, query_text: str, k: int = 5, similarity_threshold: float = 2.5) -> List[Dict[str, Any]]:
        """Search for similar tables using query embeddings
        
        Args:
            database_name: Database to search
            query_text: Natural language query
            k: Max results to return
            similarity_threshold: L2 distance threshold for filtering (lower = stricter)
        """
        try:
            # Get query embedding
            query_embedding = await self.embed_text(query_text)
            
            # Search using vector store
            vector_store = get_vector_store()
            results = vector_store.search_similar_tables(database_name, query_embedding, k, similarity_threshold)
            
            return results
        except Exception as e:
            print(f"❌ Search error: {str(e)}")
            return []
    
    def search_similar_tables_sync(self, database_name: str, query_text: str, k: int = 5, similarity_threshold: float = 2.5) -> List[Dict[str, Any]]:
        """Synchronous wrapper for search_similar_tables"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(self.search_similar_tables(database_name, query_text, k, similarity_threshold))
            loop.close()
            return results
        except Exception as e:
            print(f"❌ Sync search error: {str(e)}")
            return []


# Singleton instance
_embedder_instance = None


def get_embedder() -> DatabaseEmbedder:
    """Get or create embedder instance"""
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = DatabaseEmbedder()
    return _embedder_instance


async def initialize_embeddings(databases: Optional[List[str]] = None) -> Dict[str, Any]:
    """Initialize embeddings for all databases"""
    embedder = get_embedder()
    return await embedder.embed_all_databases(databases)


if __name__ == "__main__":
    # Test embedder
    print("Testing Database Embedder...")
    result = asyncio.run(initialize_embeddings())
    print(json.dumps(result, indent=2, default=str))
