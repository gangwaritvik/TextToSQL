"""
Query Logger - Stores query logs in a dedicated folder
Automatically cleans up logs on backend shutdown
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any

from backend.paths import LOGS_DIR


def get_query_logger():
    """Get or create a logger for query logging"""
    logger = logging.getLogger("query_logger")
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    # Create a handler for query logs
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"query_{timestamp}.log"
    
    handler = logging.FileHandler(log_file)
    handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


def log_query(query_text: str, database: str, tables: list, sql: str, status: str):
    """Log a query execution"""
    logger = get_query_logger()
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query_text,
        "database": database,
        "tables_found": tables,
        "generated_sql": sql,
        "status": status
    }
    
    logger.info(json.dumps(log_entry))
    
    # Flush all handlers to ensure data is written to disk
    for handler in logger.handlers:
        handler.flush()


def cleanup_logs():
    """Clean up all query logs"""
    try:
        if LOGS_DIR.exists():
            for log_file in LOGS_DIR.glob("query_*.log"):
                log_file.unlink()
        logging.getLogger("query_logger").info("Logs cleaned up on shutdown")
    except Exception as e:
        print(f"Error cleaning up logs: {e}")
