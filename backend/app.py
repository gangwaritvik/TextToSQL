"""
Text-to-SQL FastAPI Application
Main application entry point with lifespan management and route registration
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from contextlib import asynccontextmanager
import sys
from pathlib import Path
import shutil
import logging

# Configure logging to output to console (ensure it shows in terminal)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db.db import get_engine
from backend.utils.join_graph_builder import build_all_join_graphs
from backend.utils.metadata_builder import build_all_metadata
from backend.utils.state import set_join_graphs, set_metadata
from backend.core.file_handler import FileUploadHandler
from backend.routes import query_router, databases_router, join_graphs_router, metadata_router, upload_router
from backend.core.embedder import initialize_embeddings
from backend.utils.logger import cleanup_logs

# Embeddings directory path
EMBEDDINGS_DIR = Path(__file__).parent / ".." / "embeddings"


engine = get_engine()  # Initialize database connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    # ===== STARTUP =====
    print("\n" + "="*60)
    print("🚀 TEXT-TO-SQL BACKEND INITIALIZATION")
    print("="*60)
    
    try:
        # Fetch all available databases
        print("\n📍 Step 1: Fetching all databases...")
        with engine.connect() as connection:
            query = text(
                """
                SELECT datname FROM pg_database
                WHERE datistemplate = false AND datallowconn = true
                ORDER BY datname
                """
            )
            result = connection.execute(query)
            databases = [row[0] for row in result.fetchall()]
        
        print(f"✅ Found {len(databases)} databases: {databases}")
        
        # Clean up any leftover uploaded files from previous sessions
        print("\n📍 Step 2: Cleaning up uploaded files from previous sessions...")
        cleanup_result = FileUploadHandler.cleanup_uploaded_tables(databases)
        if cleanup_result["success"]:
            print(f"✅ {cleanup_result['message']}")
        else:
            print(f"⚠️  {cleanup_result['message']}")
        
        # Build join graphs
        print("\n📍 Step 3: Building join graphs...")
        join_graphs = build_all_join_graphs(databases)
        set_join_graphs(join_graphs)
        
        
        # Build metadata
        print("\n📍 Step 4: Building metadata...")
        metadata = build_all_metadata(databases)
        set_metadata(metadata)
        
        # Initialize embeddings (concurrent for all tables)
        print("\n📍 Step 5: Initializing embeddings for all tables...")
        import asyncio
        embeddings_result = await initialize_embeddings(databases)
        print(f"✅ Embeddings initialized: {embeddings_result['total_tables_embedded']} tables embedded")
        
    except Exception as e:
        print(f"\n❌ Error during initialization: {str(e)}")
        print("="*60 + "\n")
    
    yield
    
    # ===== SHUTDOWN =====
    print("\n" + "="*60)
    print("🛑 TEXT-TO-SQL BACKEND SHUTDOWN")
    print("="*60)
    cleanup_logs()
    print("✅ Cleanup complete\n")
    print("="*60)
    
    # Delete embeddings
    try:
        if EMBEDDINGS_DIR.exists():
            # Delete all .faiss index files
            for faiss_file in EMBEDDINGS_DIR.glob("*_index.faiss"):
                faiss_file.unlink()
                print(f"🗑️  Deleted {faiss_file.name}")
            
            # Delete all metadata JSON files
            for json_file in EMBEDDINGS_DIR.glob("*_metadata.json"):
                json_file.unlink()
                print(f"🗑️  Deleted {json_file.name}")
            
            print("✅ Embeddings cleaned up")
    except Exception as e:
        print(f"⚠️  Error cleaning up embeddings: {str(e)}")
    
    engine.dispose()
    print("✅ Database connections closed")
    print("="*60 + "\n")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Text-to-SQL Backend",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(query_router)
app.include_router(databases_router)
app.include_router(join_graphs_router)
app.include_router(metadata_router)
app.include_router(upload_router)
