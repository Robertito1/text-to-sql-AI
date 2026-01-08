import re
import logging
from typing import List, Any, Tuple, Union, Optional, Dict
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

from .db import get_sql_database
from .schema_docs import SCHEMA_SNIPPETS
from .safe_sql import is_safe_readonly_sql
from .llm import get_llm
from .models import QueryResponse, ChartConfig
from decimal import Decimal
import json

logger = logging.getLogger(__name__)

CHROMA_DIR = "chroma_db"

def get_vectorstore() -> Chroma:
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vs = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)

    if vs._collection.count() == 0:
        docs: List[Document] = [Document(page_content=txt) for txt in SCHEMA_SNIPPETS]
        vs.add_documents(docs)
        vs.persist()

    return vs

def normalize_sql(sql: str) -> str:
    """Remove markdown code fences and fix common syntax issues for SQL Server."""
    if not sql:
        return sql
    
    s = sql.strip()
    s = re.sub(r"^```(?:sql)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```$", "", s)
    
    # Fix MySQL LIMIT to SQL Server TOP
    # Pattern: ... LIMIT N at the end of query
    limit_match = re.search(r'\bLIMIT\s+(\d+)\s*;?\s*$', s, flags=re.IGNORECASE)
    if limit_match:
        limit_num = limit_match.group(1)
        # Remove the LIMIT clause
        s = re.sub(r'\bLIMIT\s+\d+\s*;?\s*$', '', s, flags=re.IGNORECASE).strip()
        # Add TOP after SELECT
        s = re.sub(r'^(SELECT)\s+', rf'\1 TOP {limit_num} ', s, flags=re.IGNORECASE)
        # Ensure it ends with semicolon
        if not s.endswith(';'):
            s += ';'
    
    return s.strip()

def extract_sql(text: str) -> str:
    # If the model wraps it in ```sql ... ```
    m = re.search(r"```sql\s*(.*?)```", text, flags=re.S | re.I)
    if m:
        return m.group(1).strip()
    # Otherwise, return raw (and guard will reject if it's not SQL)
    return text.strip()

def _parse_raw_result(result: Any) -> List[Dict[str, Any]]:
    """
    Parse raw SQL result into a list of dictionaries.
    Handles string format like "[('2025-10', Decimal('436689.06')), ...]"
    """
    if result is None:
        return []
    
    # If result is already a list of tuples/lists
    if isinstance(result, list):
        parsed = []
        for row in result:
            if isinstance(row, (list, tuple)):
                # Convert to dict with generic keys
                row_dict = {}
                for i, val in enumerate(row):
                    if isinstance(val, Decimal):
                        row_dict[f"col_{i}"] = float(val)
                    else:
                        row_dict[f"col_{i}"] = val
                parsed.append(row_dict)
            elif isinstance(row, dict):
                parsed.append(row)
        return parsed
    
    # If result is a string (from db.run), try to parse it
    if isinstance(result, str):
        # Handle empty results
        if not result or result.strip() in ('', '[]', '()'):
            return []
        try:
            # Replace Decimal('...') with just the number for ast.literal_eval
            import ast
            import re
            # Convert Decimal('123.45') to 123.45
            cleaned = re.sub(r"Decimal\('([^']+)'\)", r"\1", result)
            evaluated = ast.literal_eval(cleaned)
            return _parse_raw_result(evaluated)
        except Exception as e:
            logger.warning(f"Failed to parse result string: {e}")
            pass
    
    return []


def _determine_chart_config(question: str, data: List[Dict], sql: str) -> Optional[ChartConfig]:
    """
    Determine if and what type of chart should be displayed based on the question and data.
    """
    if not data or len(data) < 2:
        return None
    
    question_lower = question.lower()
    keys = list(data[0].keys()) if data else []
    
    if len(keys) < 2:
        return None
    
    x_key = keys[0]
    y_key = keys[1]
    
    # Determine chart type based on question keywords
    if any(word in question_lower for word in ['trend', 'over time', 'monthly', 'daily', 'yearly', 'growth']):
        return ChartConfig(
            type='line',
            x_key=x_key,
            y_key=y_key,
            title='Trend Over Time',
            x_label=x_key.replace('_', ' ').title(),
            y_label=y_key.replace('_', ' ').title()
        )
    elif any(word in question_lower for word in ['top', 'most', 'highest', 'best', 'ranking', 'compare']):
        return ChartConfig(
            type='bar',
            x_key=x_key,
            y_key=y_key,
            title='Comparison',
            x_label=x_key.replace('_', ' ').title(),
            y_label=y_key.replace('_', ' ').title()
        )
    elif any(word in question_lower for word in ['distribution', 'breakdown', 'percentage', 'share']):
        return ChartConfig(
            type='pie',
            x_key=x_key,
            y_key=y_key,
            title='Distribution'
        )
    elif any(word in question_lower for word in ['revenue', 'sales', 'amount', 'total']):
        return ChartConfig(
            type='bar',
            x_key=x_key,
            y_key=y_key,
            title='Revenue Analysis',
            x_label=x_key.replace('_', ' ').title(),
            y_label=y_key.replace('_', ' ').title()
        )
    elif any(word in question_lower for word in ['count', 'number', 'how many']) and len(data) > 1:
        return ChartConfig(
            type='bar',
            x_key=x_key,
            y_key=y_key,
            title='Count Analysis',
            x_label=x_key.replace('_', ' ').title(),
            y_label='Count'
        )
    
    # Default: show bar chart if we have multiple rows
    if len(data) >= 2:
        return ChartConfig(
            type='bar',
            x_key=x_key,
            y_key=y_key,
            title='Query Results',
            x_label=x_key.replace('_', ' ').title(),
            y_label=y_key.replace('_', ' ').title()
        )
    
    return None


def _generate_summary(question: str, sql: str, data: List[Dict], llm: Any) -> str:
    """
    Generate a natural language summary of the query results.
    """
    if not data:
        return "No results found for your query."
    
    # For single value results
    if len(data) == 1 and len(data[0]) == 1:
        value = list(data[0].values())[0]
        if any(q in question.lower() for q in ["how many", "number of", "count of"]):
            try:
                count = int(value) if value is not None else 0
                noun = 'result' if 'result' in question.lower() else 'item'
                noun = 'table' if 'table' in question.lower() else noun
                noun = 'customer' if 'customer' in question.lower() else noun
                noun = 'order' if 'order' in question.lower() else noun
                return f"There {'is' if count == 1 else 'are'} {count} {noun}{'' if count == 1 else 's'}."
            except (ValueError, TypeError):
                pass
    
    # Use LLM for more complex summaries
    try:
        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "You are a helpful SQL assistant. "
             "Provide a brief, clear summary of the query results in 1-2 sentences. "
             "Focus on the key insights. Do not include SQL or raw data in your response."),
            ("human", 
             "Question: {question}\n\n"
             "Results (as JSON): {data}")
        ])
        
        summary = llm.invoke(summary_prompt.format_messages(
            question=question,
            data=json.dumps(data[:20], default=str)  # Limit to first 20 rows
        )).content
        
        return summary
    except Exception as e:
        logger.warning(f"Failed to generate LLM summary: {e}")
        return f"Found {len(data)} result(s) for your query."

def answer_question(question: str) -> QueryResponse:
    """
    Answer a natural language question by generating and executing SQL.
    
    Args:
        question: Natural language question about the database
        
    Returns:
        QueryResponse with structured data for frontend
    """
    if not question or not question.strip():
        return QueryResponse(
            success=False,
            summary="Question cannot be empty",
            error="Question cannot be empty"
        )
    
    logger.info(f"Starting question processing: {question[:100]}...")
    
    try:
        llm = get_llm()
        db = get_sql_database()

        # 1) RAG: retrieve schema context
        logger.debug("Retrieving schema context from vector store")
        vs = get_vectorstore()
        retriever = vs.as_retriever(search_kwargs={"k": 4})
        docs = retriever.invoke(question)
        schema_ctx = "\n\n".join(d.page_content for d in docs) if docs else "\n\n".join(SCHEMA_SNIPPETS[:4])
        logger.debug(f"Retrieved {len(docs)} schema documents")

        # Generate SQL using the LLM
        logger.debug("Generating SQL query with LLM")
        sql_prompt = ChatPromptTemplate.from_messages([
            ("system",
            "You are a Microsoft SQL Server (T-SQL) assistant.\n"
            "Return ONLY ONE SQL query using T-SQL syntax.\n"
            "CRITICAL RULES:\n"
            "- READ ONLY (SELECT or WITH)\n"
            "- NEVER use LIMIT - use SELECT TOP N instead (e.g., SELECT TOP 10 * FROM table)\n"
            "- Use FORMAT() for date formatting\n"
            "- Use GETDATE() for current date\n"
            "- Prefer sys.tables / sys.columns over INFORMATION_SCHEMA\n"
            "- No explanations, just the SQL query\n"
            ),
            ("human", "Schema:\n{schema}\n\nQuestion: {question}")
        ])
        
        sql_raw = llm.invoke(sql_prompt.format_messages(schema=schema_ctx, question=question)).content
        sql = extract_sql(sql_raw)
        sql = normalize_sql(sql)
        
        if not sql:
            logger.warning("LLM returned empty SQL")
            return QueryResponse(
                success=False,
                summary="Failed to generate SQL query from question",
                error="Failed to generate SQL query from question"
            )
        
        logger.info(f"Generated SQL: {sql[:100]}...")

        # Safe SQL guard
        if not is_safe_readonly_sql(sql):
            logger.warning(f"Unsafe SQL rejected: {sql}")
            return QueryResponse(
                success=False,
                summary="The generated query contains potentially dangerous operations and was rejected.",
                sql=sql,
                error="Unsafe SQL rejected"
            )

        # Run query
        logger.debug("Executing SQL query")
        try:
            result = db.run(sql)
            logger.info(f"Query executed successfully. Result type: {type(result)}, Result: {repr(result)[:500]}")
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            return QueryResponse(
                success=False,
                summary=f"Database query failed: {str(e)}",
                sql=sql,
                error=str(e)
            )

        # Parse and structure the results
        logger.debug("Processing query results")
        data = _parse_raw_result(result)
        
        # Generate summary
        summary = _generate_summary(question, sql, data, llm)
        
        # Determine if we should show a chart
        chart = _determine_chart_config(question, data, sql)
        
        return QueryResponse(
            success=True,
            summary=summary,
            sql=sql,
            data=data,
            chart=chart
        )
    
    except Exception as e:
        logger.error(f"Error in answer_question: {e}", exc_info=True)
        return QueryResponse(
            success=False,
            summary=f"An error occurred: {str(e)}",
            error=str(e)
        )
        
