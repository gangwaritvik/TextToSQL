"""
SQL Generator - Uses Azure OpenAI to generate SQL queries from natural language
"""

from typing import List, Dict, Any
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.utils.prompt_builder import build_sql_generation_prompt, build_query_analysis_prompt
from backend.config.llm import model as llm_model

# Configure logging
logger = logging.getLogger(__name__)


class SQLGenerator:
    """Generate SQL queries using Azure OpenAI."""
    
    def __init__(self):
        """Initialize SQL Generator with LLM model from config."""
        self.model = llm_model
        self.max_tokens = 1000
        logger.info(f"🤖 SQLGenerator initialized with LLM model")
    
    def generate_sql(
        self,
        query_text: str,
        relevant_tables: List[str],
        table_metadata: List[Dict[str, Any]],
        join_graph: Dict[str, Any],
        database_name: str
    ) -> tuple:
        """
        Generate SQL query from natural language using Azure OpenAI.
        
        Returns:
            Tuple of (sql_query, tokens_used)
        """
        try:
            prompt = build_sql_generation_prompt(
                query_text=query_text,
                relevant_tables=relevant_tables,
                table_metadata=table_metadata,
                join_graph=join_graph,
                database_name=database_name
            )
            
            try:
                response = self.model.invoke(prompt)
                sql_query = response.content.strip()
            except Exception as invoke_error:
                raise invoke_error
            
            # Remove markdown code blocks if present
            if sql_query.startswith("```sql"):
                sql_query = sql_query[6:]
            if sql_query.startswith("```"):
                sql_query = sql_query[3:]
            if sql_query.endswith("```"):
                sql_query = sql_query[:-3]
            
            sql_query = sql_query.strip()
            
            # Extract tokens used from response metadata
            tokens_used = "0"
            try:
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    tokens_used = str(response.usage_metadata.get('total_tokens', '0'))
                elif hasattr(response, 'response_metadata') and response.response_metadata:
                    token_usage = response.response_metadata.get('token_usage', {})
                    tokens_used = str(token_usage.get('total_tokens', '0'))
            except:
                tokens_used = "0"
            
            return sql_query, tokens_used
            
        except Exception as e:
            logger.error(f"LLM call failed: {type(e).__name__}: {str(e)}")
            return "", "0"
    
    def analyze_query(
        self,
        query_text: str,
        relevant_tables: List[str],
        table_metadata: List[Dict[str, Any]],
        join_graph: Dict[str, Any],
        database_name: str
    ) -> str:
        """
        Analyze query requirements using Azure OpenAI.
        
        Args:
            query_text: Natural language query
            relevant_tables: List of relevant table names
            table_metadata: Metadata for all tables
            join_graph: Join graph for the database
            database_name: Database name
        
        Returns:
            Analysis result string
        """
        try:
            prompt = build_query_analysis_prompt(
                query_text=query_text,
                relevant_tables=relevant_tables,
                table_metadata=table_metadata,
                join_graph=join_graph,
                database_name=database_name
            )
            
            response = self.model.invoke(prompt)
            analysis = response.content.strip()
            
            logger.info(f"✅ Query analysis completed")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing query: {str(e)}")
            return ""


# Singleton instance
_sql_generator: SQLGenerator = None


def get_sql_generator() -> SQLGenerator:
    """Get or create singleton SQL generator instance."""
    global _sql_generator
    if _sql_generator is None:
        _sql_generator = SQLGenerator()
    return _sql_generator
