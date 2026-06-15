"""
Vector Store - FAISS-based vector storage and similarity search
Manages embeddings indices and semantic search operations
"""

import json
import numpy as np
import faiss
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio

# Storage paths
EMBEDDINGS_DIR = Path(__file__).parent / ".." / "embeddings"
EMBEDDINGS_DIR.mkdir(exist_ok=True)


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
    
    def search_similar_tables(
        self, 
        database_name: str, 
        query_embedding: List[float], 
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar tables using FAISS"""
        try:
            if database_name not in self.faiss_indices:
                return []
            
            query_array = np.array([query_embedding], dtype=np.float32)
            
            # Search FAISS index
            index = self.faiss_indices[database_name]
            distances, indices = index.search(query_array, k)
            
            results = []
            entries = self.embeddings_store[database_name]
            for idx in indices[0]:
                if idx < len(entries):
                    results.append({
                        "table": entries[idx]["table"],
                        "database": entries[idx]["database"],
                        "distance": float(distances[0][list(indices[0]).index(idx)]),
                        "metadata": entries[idx]["metadata"]
                    })
            
            return results
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
