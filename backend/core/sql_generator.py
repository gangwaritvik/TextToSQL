"""
SQL Generator - Uses Azure OpenAI to generate SQL queries from natural language
"""

from typing import List, Dict, Any
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.utils.prompt_builder import build_sql_generation_prompt
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
        Also includes danger assessment in single LLM call.
        
        Returns:
            Tuple of (sql_query, tokens_used, is_dangerous, danger_reason)
        """
        try:
            logger.info("🔨 Building prompt for SQL generation...")
            
            # Log table analysis
            uploaded_tables = [t for t in table_metadata if t.get("uploaded", False)]
            regular_tables = [t for t in table_metadata if not t.get("uploaded", False)]
            
            if uploaded_tables:
                logger.info(f"📤 Uploaded tables in context: {[t['name'] for t in uploaded_tables]}")
            logger.info(f"📊 Database tables in context: {[t['name'] for t in regular_tables]}")
            
            prompt = build_sql_generation_prompt(
                query_text=query_text,
                relevant_tables=relevant_tables,
                table_metadata=table_metadata,
                join_graph=join_graph,
                database_name=database_name
            )
            
            logger.info("📤 SENDING TO LLM:")
            logger.info("=" * 80)
            logger.info(prompt)
            logger.info("=" * 80)
            
            try:
                logger.info("⏳ Waiting for LLM response...")
                response = self.model.invoke(prompt)
                response_text = response.content.strip()
                
                logger.info("📥 LLM RESPONSE:")
                logger.info("=" * 80)
                logger.info(response_text)
                logger.info("=" * 80)
                
            except Exception as invoke_error:
                logger.error(f"❌ LLM invocation failed: {str(invoke_error)}", exc_info=True)
                raise invoke_error
            
            # Parse response to extract DANGEROUS, REASON, and SQL
            is_dangerous = False
            danger_reason = ""
            sql_query = ""
            
            lines = response_text.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith("DANGEROUS:"):
                    is_dangerous = "YES" in line.upper()
                    logger.info(f"🚨 DANGEROUS FLAG: {is_dangerous}")
                elif line.startswith("REASON:"):
                    danger_reason = line.replace("REASON:", "").strip()
                    logger.info(f"📝 REASON: {danger_reason}")
                elif line.startswith("SQL:"):
                    sql_query = line.replace("SQL:", "").strip()
                    logger.info(f"📋 EXTRACTED SQL: {sql_query}")
            
            # Clean up SQL if still has markdown
            if sql_query.startswith("```sql"):
                sql_query = sql_query[6:]
            if sql_query.startswith("```"):
                sql_query = sql_query[3:]
            if sql_query.endswith("```"):
                sql_query = sql_query[:-3]
            
            sql_query = sql_query.strip()
            
            logger.info("✅ CLEANED SQL:")
            logger.info("=" * 80)
            logger.info(sql_query)
            logger.info("=" * 80)
            
            if is_dangerous:
                logger.warning(f"⚠️ DANGEROUS OPERATION DETECTED: {danger_reason}")
            
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
            
            logger.info(f"💰 Tokens used: {tokens_used}")
            
            return sql_query, tokens_used, is_dangerous, danger_reason
            
        except Exception as e:
            logger.error(f"LLM call failed: {type(e).__name__}: {str(e)}")
            return "", "0", False, ""

# Singleton instance
_sql_generator: SQLGenerator = None


def get_sql_generator() -> SQLGenerator:
    """Get or create singleton SQL generator instance."""
    global _sql_generator
    if _sql_generator is None:
        _sql_generator = SQLGenerator()
    return _sql_generator
