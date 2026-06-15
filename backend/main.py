"""
Text-to-SQL Backend Entry Point
Run this file to start the FastAPI development server
"""

import uvicorn
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env.local
env_path = Path(__file__).parent.parent / ".env.local"
load_dotenv(env_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress FAISS loader INFO messages (they're just about trying different SIMD versions)
logging.getLogger("faiss.loader").setLevel(logging.WARNING)

# Add parent directory to path so backend package can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app import app

if __name__ == "__main__":
    print("🚀 Starting Text-to-SQL Backend...")
    print("📊 Server running on: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
