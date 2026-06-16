"""
File Upload Handler - Parse CSV/Excel and create temporary tables
"""
import pandas as pd
import io
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
import uuid
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db.db import get_engine

logger = logging.getLogger(__name__)


class FileUploadHandler:
    """Handle CSV and Excel file uploads, parse and create temporary tables."""
    
    # Store uploaded tables metadata in memory
    uploaded_tables = {}  # {table_name: {filename, rows, columns, created_at}}
    
    @staticmethod
    def parse_csv_file(file_content: bytes, filename: str) -> Tuple[pd.DataFrame, str]:
        """Parse CSV file and return DataFrame with table name."""
        try:
            df = pd.read_csv(io.BytesIO(file_content))
            # Use underscores instead of hyphens to avoid SQL quoting issues
            file_stem = Path(filename).stem.replace('-', '_').replace(' ', '_')
            table_name = f"uploaded__{file_stem}_{str(uuid.uuid4())[:8]}"
            return df, table_name
        except Exception as e:
            logger.error(f"Error parsing CSV: {str(e)}")
            raise ValueError(f"Failed to parse CSV file: {str(e)}")
    
    @staticmethod
    def parse_excel_file(file_content: bytes, filename: str) -> Tuple[pd.DataFrame, str]:
        """Parse Excel file and return DataFrame with table name."""
        try:
            # Try to read first sheet
            df = pd.read_excel(io.BytesIO(file_content), sheet_name=0)
            # Use underscores instead of hyphens to avoid SQL quoting issues
            file_stem = Path(filename).stem.replace('-', '_').replace(' ', '_')
            table_name = f"uploaded__{file_stem}_{str(uuid.uuid4())[:8]}"
            return df, table_name
        except Exception as e:
            logger.error(f"Error parsing Excel: {str(e)}")
            raise ValueError(f"Failed to parse Excel file: {str(e)}")
    
    @staticmethod
    def create_temp_table(df: pd.DataFrame, table_name: str, database_name: str = "fastapi_db") -> Dict[str, Any]:
        """Create temporary table from DataFrame in the database."""
        try:
            engine = get_engine(database_name)
            
            # Clean column names (remove spaces, special chars)
            df.columns = [col.strip().lower().replace(' ', '_').replace('-', '_') for col in df.columns]
            
            # Create table
            df.to_sql(table_name, engine, if_exists='replace', index=False)
            
            # Get column info
            columns = []
            for col, dtype in df.dtypes.items():
                columns.append({
                    "name": col,
                    "type": str(dtype),
                    "nullable": True
                })
            
            # Store metadata
            metadata = {
                "filename": table_name.split("__")[1],
                "rows": len(df),
                "columns": columns,
                "database": database_name,
                "created_at": pd.Timestamp.now().isoformat()
            }
            
            logger.info(f"Storing metadata for {table_name}: {metadata}")
            FileUploadHandler.uploaded_tables[table_name] = metadata
            logger.info(f"After storing, uploaded_tables: {FileUploadHandler.uploaded_tables}")
            
            logger.info(f"✓ Created temporary table: {table_name} with {len(df)} rows")
            
            return {
                "table_name": table_name,
                "rows": len(df),
                "columns": columns,
                "success": True
            }
        except Exception as e:
            logger.error(f"Error creating temporary table: {str(e)}")
            raise ValueError(f"Failed to create table: {str(e)}")
    
    @staticmethod
    def upload_file(file_content: bytes, filename: str, database_name: str = "fastapi_db") -> Dict[str, Any]:
        """Complete upload process: parse -> create table -> return metadata."""
        try:
            logger.info(f"Starting upload for: {filename} to database: {database_name}")
            
            file_ext = Path(filename).suffix.lower()
            
            # Parse file based on extension
            if file_ext == '.csv':
                df, table_name = FileUploadHandler.parse_csv_file(file_content, filename)
            elif file_ext in ['.xlsx', '.xls']:
                df, table_name = FileUploadHandler.parse_excel_file(file_content, filename)
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
            
            logger.info(f"Parsed file as table: {table_name} with {len(df)} rows")
            
            # Create table
            result = FileUploadHandler.create_temp_table(df, table_name, database_name)
            
            logger.info(f"Upload successful. Metadata stored. Current uploaded_tables: {list(FileUploadHandler.uploaded_tables.keys())}")
            
            return {
                "success": True,
                "table_name": table_name,
                "filename": filename,
                "rows": result["rows"],
                "columns": result["columns"],
                "message": f"Successfully uploaded {filename} as {table_name}"
            }
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to upload file: {str(e)}"
            }
    
    @staticmethod
    def get_uploaded_tables(database_name: str = "fastapi_db") -> list:
        """Get all uploaded tables for a database by querying the database directly.
        
        This method dynamically discovers uploaded tables (with uploaded__ prefix)
        from the database, making it resilient to server restarts.
        """
        try:
            engine = get_engine(database_name)
            uploaded_tables_list = []
            
            with engine.connect() as conn:
                # Find all tables with uploaded__ prefix
                query = text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name LIKE 'uploaded__%'
                    ORDER BY table_name
                """)
                result = conn.execute(query)
                table_names = [row[0] for row in result.fetchall()]
                
                logger.info(f"Found {len(table_names)} uploaded tables in {database_name}: {table_names}")
                
                # Get schema for each uploaded table
                for table_name in table_names:
                    try:
                        # Get columns info using parameterized query
                        schema_query = text("""
                            SELECT column_name, data_type, is_nullable
                            FROM information_schema.columns
                            WHERE table_schema = 'public'
                            AND table_name = :table_name
                            ORDER BY ordinal_position
                        """)
                        schema_result = conn.execute(schema_query, {"table_name": table_name})
                        columns = [
                            {
                                "name": row[0],
                                "type": row[1],
                                "nullable": row[2] == 'YES'
                            }
                            for row in schema_result.fetchall()
                        ]
                        
                        # Get row count using parameterized query
                        count_query = text(f"SELECT COUNT(*) FROM \"{table_name}\"")
                        count_result = conn.execute(count_query)
                        row_count = count_result.scalar() or 0
                        
                        # Extract original filename from table name
                        # Format: uploaded__<filename>_<uuid>
                        parts = table_name.replace("uploaded__", "").rsplit("_", 1)
                        filename = parts[0] if parts else table_name
                        
                        uploaded_tables_list.append({
                            "name": table_name,
                            "filename": filename,
                            "columns": columns,
                            "rows": row_count,
                            "database": database_name
                        })
                        
                        logger.debug(f"Loaded uploaded table {table_name}: {len(columns)} columns, {row_count} rows")
                    
                    except Exception as e:
                        logger.error(f"Error loading schema for {table_name}: {str(e)}")
                        continue
            
            logger.info(f"Successfully loaded {len(uploaded_tables_list)} uploaded tables from {database_name}")
            return uploaded_tables_list
            
        except Exception as e:
            logger.error(f"Error fetching uploaded tables from {database_name}: {str(e)}", exc_info=True)
            return []
    
    @staticmethod
    def delete_table(table_name: str, database_name: str = "fastapi_db") -> Dict[str, Any]:
        """Delete an uploaded table."""
        try:
            engine = get_engine(database_name)
            with engine.connect() as conn:
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                conn.commit()
            
            # Remove from metadata
            if table_name in FileUploadHandler.uploaded_tables:
                del FileUploadHandler.uploaded_tables[table_name]
            
            logger.info(f"✓ Deleted table: {table_name}")
            return {"success": True, "message": f"Deleted {table_name}"}
        except Exception as e:
            logger.error(f"Error deleting table: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def cleanup_uploaded_tables(databases: list = None) -> Dict[str, Any]:
        """Clean up all uploaded tables on app startup/refresh."""
        try:
            if databases is None:
                databases = []
            
            deleted_count = 0
            failed_tables = []
            
            logger.info(f"Starting cleanup for databases: {databases}")
            
            # Clean up from all databases
            for database_name in databases:
                logger.info(f"Checking database {database_name} for uploaded tables...")
                try:
                    engine = get_engine(database_name)
                    
                    # Get raw connection for direct SQL execution
                    with engine.raw_connection() as raw_conn:
                        cursor = raw_conn.cursor()
                        
                        try:
                            # Find all tables with uploaded__ prefix
                            find_tables_query = """
                                SELECT table_name 
                                FROM information_schema.tables 
                                WHERE table_schema = 'public' 
                                AND table_name LIKE 'uploaded__%'
                            """
                            cursor.execute(find_tables_query)
                            tables_to_drop = [row[0] for row in cursor.fetchall()]
                            
                            if tables_to_drop:
                                logger.info(f"Found {len(tables_to_drop)} uploaded tables in {database_name}: {tables_to_drop}")
                            
                            # Drop each table
                            for table_name in tables_to_drop:
                                try:
                                    drop_query = f'DROP TABLE IF EXISTS "{table_name}" CASCADE'
                                    logger.info(f"Executing: {drop_query}")
                                    cursor.execute(drop_query)
                                    raw_conn.commit()
                                    logger.info(f"✓ Successfully dropped table: {table_name}")
                                    deleted_count += 1
                                except Exception as e:
                                    logger.error(f"Failed to drop {table_name}: {str(e)}")
                                    failed_tables.append(table_name)
                                    try:
                                        raw_conn.rollback()
                                    except:
                                        pass
                        
                        finally:
                            cursor.close()
                    
                    # Dispose engine to clear connection pool
                    engine.dispose()
                    
                except Exception as e:
                    logger.error(f"Error cleaning up database {database_name}: {str(e)}")
            
            # Clear metadata dictionary
            FileUploadHandler.uploaded_tables.clear()
            logger.info(f"Cleared uploaded_tables metadata")
            
            logger.info(f"✓ Cleanup complete: Successfully deleted {deleted_count} uploaded tables")
            if failed_tables:
                logger.warning(f"Failed to delete {len(failed_tables)} tables: {failed_tables}")
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "failed_count": len(failed_tables),
                "message": f"Cleaned up {deleted_count} uploaded tables"
            }
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Cleanup failed: {str(e)}"
            }


def get_file_upload_handler():
    """Get FileUploadHandler singleton."""
    return FileUploadHandler()
