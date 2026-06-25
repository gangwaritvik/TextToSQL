"""
Vector Store - FAISS-based vector storage and similarity search
Manages embeddings indices and semantic search operations
"""

import json
import numpy as np
import faiss
from typing import List, Dict, Any, Optional
import asyncio

from backend.paths import EMBEDDINGS_DIR


class VectorStore:
    """Manages FAISS indices for semantic search"""
    
    def __init__(self):
        self.faiss_indices = {}  # {db_name: faiss_index}
        self.embeddings_store = {}  # {db_name: embeddings_data}
    
    async def build_faiss_indices(self, embeddings_list: List[Dict[str, Any]]) -> None:
        """Build FAISS indices and store embeddings"""
        try:
            print("\n📚 Building FAISS indices...")
            
            # Group by database
            by_database = {}
            for entry in embeddings_list:
                db = entry["database"]
                if db not in by_database:
                    by_database[db] = []
                by_database[db].append(entry)
            
            # Create FAISS index for each database
            for db_name, entries in by_database.items():
                if not entries:
                    continue
                
                embeddings_array = np.array([
                    np.array(e["embedding"], dtype=np.float32)
                    for e in entries
                ])
                
                # Create FAISS index
                dimension = embeddings_array.shape[1]
                index = faiss.IndexFlatL2(dimension)
                index.add(embeddings_array)
                
                self.faiss_indices[db_name] = index
                self.embeddings_store[db_name] = entries
                
                # Save to disk
                index_path = EMBEDDINGS_DIR / f"{db_name}_index.faiss"
                faiss.write_index(index, str(index_path))
                
                # Save metadata
                metadata_path = EMBEDDINGS_DIR / f"{db_name}_metadata.json"
                with open(metadata_path, "w") as f:
                    json.dump(entries, f, indent=2)
                
                print(f"  ✅ {db_name}: {len(entries)} embeddings → {index_path.name}")
            
            print(f"✅ FAISS indices created for {len(by_database)} databases")
        except Exception as e:
            print(f"❌ Error building FAISS indices: {str(e)}")
            raise

    def get_indexed_tables(self, database_name: str) -> set:
        """Return the set of table names currently indexed for a database."""
        return {e["table"] for e in self.embeddings_store.get(database_name, [])}

    def set_database_index(self, database_name: str, entries: List[Dict[str, Any]]) -> None:
        """(Re)build a single database's FAISS index from ``entries`` and persist it.

        Used to keep the index in sync as uploaded tables are added or removed,
        without rebuilding every database. Passing an empty ``entries`` list drops
        the index and its persisted files.
        """
        index_path = EMBEDDINGS_DIR / f"{database_name}_index.faiss"
        metadata_path = EMBEDDINGS_DIR / f"{database_name}_metadata.json"

        if not entries:
            self.faiss_indices.pop(database_name, None)
            self.embeddings_store.pop(database_name, None)
            if index_path.exists():
                index_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()
            return

        embeddings_array = np.array(
            [np.array(e["embedding"], dtype=np.float32) for e in entries]
        )
        dimension = embeddings_array.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings_array)

        self.faiss_indices[database_name] = index
        self.embeddings_store[database_name] = entries

        faiss.write_index(index, str(index_path))
        with open(metadata_path, "w") as f:
            json.dump(entries, f, indent=2)

    def search_similar_tables(
        self, 
        database_name: str, 
        query_embedding: List[float], 
        k: int = 5,
        similarity_threshold: float = 2.5
    ) -> List[Dict[str, Any]]:
        """Search for similar tables using FAISS with similarity threshold
        
        Args:
            database_name: Database to search in
            query_embedding: Query embedding vector
            k: Max number of results to return
            similarity_threshold: L2 distance threshold (lower = more similar). Default 2.5 filters out poorly matched tables.
        """
        try:
            if database_name not in self.faiss_indices:
                return []
            
            query_array = np.array([query_embedding], dtype=np.float32)
            
            # Search FAISS index - get more results to filter by threshold
            index = self.faiss_indices[database_name]
            search_k = min(k * 3, len(self.embeddings_store[database_name]))  # Get up to 3x results for filtering
            distances, indices = index.search(query_array, search_k)
            
            results = []
            entries = self.embeddings_store[database_name]
            for i, idx in enumerate(indices[0]):
                if idx < len(entries):
                    distance = float(distances[0][i])
                    # Only include if below threshold (lower L2 distance = more similar)
                    if distance <= similarity_threshold:
                        results.append({
                            "table": entries[idx]["table"],
                            "database": entries[idx]["database"],
                            "distance": distance,
                            "metadata": entries[idx]["metadata"]
                        })
            
            # Return up to k results
            return results[:k]
        except Exception as e:
            print(f"❌ Search error: {str(e)}")
            return []
    
    def load_indices_from_disk(self) -> None:
        """Load pre-built FAISS indices from disk"""
        try:
            for db_file in EMBEDDINGS_DIR.glob("*_index.faiss"):
                db_name = db_file.stem.replace("_index", "")
                
                # Load FAISS index
                index = faiss.read_index(str(db_file))
                self.faiss_indices[db_name] = index
                
                # Load metadata
                metadata_file = EMBEDDINGS_DIR / f"{db_name}_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, "r") as f:
                        self.embeddings_store[db_name] = json.load(f)
                    print(f"✅ Loaded {db_name} index with {len(self.embeddings_store[db_name])} embeddings")
        except Exception as e:
            print(f"⚠️  Could not load FAISS indices from disk: {str(e)}")


# Singleton instance
_vector_store_instance = None


def get_vector_store() -> VectorStore:
    """Get or create vector store instance"""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
        _vector_store_instance.load_indices_from_disk()
    return _vector_store_instance
