import re
import logging
from typing import List, Any, Tuple, Union, Optional, Dict
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_cohere import CohereEmbeddings

from .db import get_sql_database
from .schema_docs import SCHEMA_SNIPPETS
from .safe_sql import is_safe_readonly_sql
from .llm import get_llm
from .models import QueryResponse, ChartConfig
from decimal import Decimal
import json

logger = logging.getLogger(__name__)

CHROMA_DIR = "chroma_db"

# Singleton for vectorstore to avoid repeated model loading
_vectorstore_instance: Chroma | None = None

def get_vectorstore() -> Chroma:
    global _vectorstore_instance
    
    if _vectorstore_instance is not None:
        return _vectorstore_instance
    
    logger.info("Initializing Cohere embeddings...")
    embeddings = CohereEmbeddings(
        model="embed-english-light-v3.0"
    )
    
    logger.info("Initializing ChromaDB...")
    vs = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)

    if vs._collection.count() == 0:
        logger.info("Populating vector store with schema docs...")
        docs: List[Document] = [Document(page_content=txt) for txt in SCHEMA_SNIPPETS]
        vs.add_documents(docs)
        vs.persist()
    
    _vectorstore_instance = vs
    logger.info("Vector store initialized successfully")
    return _vectorstore_instance

def normalize_sql(sql: str) -> str:
    """Remove markdown code fences."""
    if not sql:
        return sql
    
    s = sql.strip()
    s = re.sub(r"^```(?:sql)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```$", "", s)
    
    return s.strip()

def extract_sql(text: str) -> str:
    # If the model wraps it in ```sql ... ```
    m = re.search(r"```sql\s*(.*?)```", text, flags=re.S | re.I)
    if m:
        return m.group(1).strip()
    # Otherwise, return raw (and guard will reject if it's not SQL)
    return text.strip()

def _extract_column_names(sql: str) -> List[str]:
    """
    Extract column names/aliases from a SELECT SQL query.
    """
    try:
        # For CTEs, find the final SELECT statement (after the last closing paren of CTE)
        sql_to_parse = sql
        if sql.strip().upper().startswith('WITH'):
            # Find the main SELECT after the CTE definition
            # Look for SELECT that's not inside the CTE
            cte_depth = 0
            main_select_pos = -1
            i = 0
            while i < len(sql):
                if sql[i] == '(':
                    cte_depth += 1
                elif sql[i] == ')':
                    cte_depth -= 1
                elif cte_depth == 0 and sql[i:i+6].upper() == 'SELECT':
                    # Skip the first SELECT inside WITH clause
                    if i > 0:
                        main_select_pos = i
                        break
                i += 1
            if main_select_pos > 0:
                sql_to_parse = sql[main_select_pos:]
        
        # Get the SELECT ... FROM part
        match = re.search(r'SELECT\s+(.*?)\s+FROM', sql_to_parse, re.IGNORECASE | re.DOTALL)
        if not match:
            return []
        
        select_part = match.group(1).strip()
        
        # Handle SELECT TOP N / DISTINCT
        select_part = re.sub(r'^(TOP\s+\d+\s+|DISTINCT\s+)+', '', select_part, flags=re.IGNORECASE)
        
        columns = []
        # Split by comma, but be careful with functions containing commas
        depth = 0
        current = ""
        for char in select_part:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            elif char == ',' and depth == 0:
                columns.append(current.strip())
                current = ""
                continue
            current += char
        if current.strip():
            columns.append(current.strip())
        
        # Extract alias or column name from each column expression
        names = []
        for col in columns:
            col = col.strip()
            # Check for AS alias (with or without quotes)
            as_match = re.search(r'\s+AS\s+["\']?(\w+)["\']?\s*$', col, re.IGNORECASE)
            if as_match:
                names.append(as_match.group(1))
            elif '.' in col and '(' not in col:
                # Simple table.column format like c.Name, c.Email
                # Extract just the column name after the dot
                col_name = col.split('.')[-1].strip()
                # Remove any trailing whitespace or brackets
                col_name = re.sub(r'[\s\[\]]+', '', col_name)
                names.append(col_name)
            else:
                # Get the last word (column name)
                # Remove function wrappers if present
                clean_col = re.sub(r'^\w+\((.*)\)$', r'\1', col)
                parts = clean_col.split()
                if parts:
                    last_part = parts[-1]
                    # Clean up any table prefix
                    if '.' in last_part:
                        last_part = last_part.split('.')[-1]
                    names.append(last_part)
                else:
                    names.append(f"col_{len(names)}")
        
        return names
    except Exception as e:
        logger.warning(f"Failed to extract column names: {e}")
        return []


def _parse_raw_result(result: Any, sql: str = "") -> List[Dict[str, Any]]:
    """
    Parse raw SQL result into a list of dictionaries.
    Handles string format like "[('2025-10', Decimal('436689.06')), ...]"
    """
    if result is None:
        return []
    
    # Extract column names from SQL
    column_names = _extract_column_names(sql) if sql else []
    
    def get_key(index: int) -> str:
        if index < len(column_names):
            return column_names[index]
        return f"col_{index}"
    
    # If result is already a list of tuples/lists
    if isinstance(result, list):
        parsed = []
        for row in result:
            if isinstance(row, (list, tuple)):
                row_dict = {}
                for i, val in enumerate(row):
                    key = get_key(i)
                    if isinstance(val, Decimal):
                        row_dict[key] = float(val)
                    else:
                        row_dict[key] = val
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
            # Convert Decimal('123.45') to 123.45
            cleaned = re.sub(r"Decimal\('([^']+)'\)", r"\1", result)
            evaluated = ast.literal_eval(cleaned)
            return _parse_raw_result(evaluated, sql)
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
    
    # Check if this is a list query (not suitable for charts)
    # Lists typically have 3+ columns or contain text-heavy data like names/emails
    list_indicators = ['list', 'show me', 'who are', 'which customers', 'all customers', 'all orders']
    if any(indicator in question_lower for indicator in list_indicators):
        # Check if data has numeric aggregation column - if not, skip chart
        has_numeric_agg = False
        for key in keys:
            if any(data[0].get(key) is not None and isinstance(data[0].get(key), (int, float)) 
                   for _ in [1]):
                # Check if it looks like an aggregation (SUM, COUNT, AVG result)
                key_lower = key.lower()
                if any(agg in key_lower for agg in ['sum', 'count', 'avg', 'total', 'amount', 'revenue']):
                    has_numeric_agg = True
                    break
        if not has_numeric_agg:
            return None
    
    # Skip charts for data with more than 2 columns that looks like a detail list
    if len(keys) > 2:
        # Check if columns look like entity details (name, email, etc.)
        detail_columns = ['name', 'email', 'address', 'phone', 'country', 'status', 'date']
        detail_count = sum(1 for k in keys if any(d in k.lower() for d in detail_columns))
        if detail_count >= 2:
            return None
    
    x_key = keys[0]
    y_key = keys[1]
    
    # Check if y_key contains numeric data suitable for charting
    sample_y = data[0].get(y_key)
    if not isinstance(sample_y, (int, float)):
        return None
    
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
        total_count = len(data)
        sample_data = data[:20] if len(data) > 20 else data
        
        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "You are a helpful SQL assistant. "
             "Provide a brief, clear summary of the query results in 1-2 sentences. "
             "Focus on the key insights. Do not include SQL or raw data in your response."),
            ("human", 
             "Question: {question}\n\n"
             "Total results: {total_count}\n"
             "Sample data (first {sample_size}): {data}")
        ])
        
        summary = llm.invoke(summary_prompt.format_messages(
            question=question,
            total_count=total_count,
            sample_size=len(sample_data),
            data=json.dumps(sample_data, default=str)
        )).content
        
        return summary
    except Exception as e:
        logger.warning(f"Failed to generate LLM summary: {e}")
        return f"Found {len(data)} result(s) for your query."

def _is_database_question(question: str, llm) -> tuple[bool, str]:
    """
    Check if the question is related to database queries.
    
    Returns:
        Tuple of (is_relevant, message)
    """
    classification_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a classifier that determines if a user question is related to database queries.

Our database contains:
- Customers table: customer profiles with Name, Email, Country, CreatedAt
- Orders table: purchase orders with OrderDate, Amount, Status (PAID/PENDING/CANCELLED)

Respond with ONLY "YES" or "NO":
- YES: if the question is about customers, orders, sales, revenue, data analysis, or anything that could be answered with a database query
- NO: if the question is about general knowledge, coding help, personal advice, weather, news, or anything unrelated to our database"""),
        ("human", "{question}")
    ])
    
    try:
        response = llm.invoke(classification_prompt.format_messages(question=question)).content.strip().upper()
        is_relevant = response.startswith("YES")
        return is_relevant, ""
    except Exception as e:
        logger.warning(f"Classification failed, assuming relevant: {e}")
        return True, ""  # Default to allowing the question

def answer_question(question: str, history: list = None) -> QueryResponse:
    """
    Answer a natural language question by generating and executing SQL.
    
    Args:
        question: Natural language question about the database
        history: List of previous conversation messages for context
        
    Returns:
        QueryResponse with structured data for frontend
    """
    if history is None:
        history = []
    
    if not question or not question.strip():
        return QueryResponse(
            success=False,
            summary="Question cannot be empty",
            error="Question cannot be empty"
        )
    
    logger.info(f"Starting question processing: {question[:100]}...")
    
    try:
        llm = get_llm()
        
        # Check if question is database-related (include history for context)
        is_relevant, _ = _is_database_question(question, llm)
        if not is_relevant:
            return QueryResponse(
                success=True,
                summary="I can only answer questions about the database. Try asking about customers, orders, sales, or revenue. For example: 'How many customers do we have?' or 'Show monthly revenue for the last 6 months'.",
                sql=None,
                data=None,
                chart=None,
                error=None
            )
        
        db = get_sql_database()

        # 1) RAG: retrieve schema context
        logger.debug("Retrieving schema context from vector store")
        vs = get_vectorstore()
        retriever = vs.as_retriever(search_kwargs={"k": 4})
        docs = retriever.invoke(question)
        schema_ctx = "\n\n".join(d.page_content for d in docs) if docs else "\n\n".join(SCHEMA_SNIPPETS[:4])
        logger.debug(f"Retrieved {len(docs)} schema documents")
        
        # Build conversation context from history
        conversation_context = ""
        if history:
            recent_history = history[-6:]  # Last 3 Q&A pairs (6 messages)
            history_parts = []
            for msg in recent_history:
                role = "User" if msg.role == "user" else "Assistant"
                history_parts.append(f"{role}: {msg.content}")
            conversation_context = "\n".join(history_parts)
            logger.debug(f"Using {len(recent_history)} messages from conversation history")

        # Generate SQL using the LLM
        logger.debug("Generating SQL query with LLM")
        
        # Detect database type from environment
        import os
        is_postgres = bool(os.getenv("DATABASE_URL"))
        
        if is_postgres:
            sql_system_prompt = (
                "You are a PostgreSQL expert.\n"
                "Return ONLY the SQL query, no explanations.\n"
                "CRITICAL PostgreSQL RULES:\n"
                "- READ ONLY: Only SELECT or WITH statements\n"
                "- LIMIT RULES:\n"
                "  - Use LIMIT only when the user asks for 'top N', 'first N', 'best N', or similar\n"
                "  - Do NOT add LIMIT for aggregation queries (COUNT, SUM, AVG) or when user wants all results\n"
                "- STRICT GROUP BY: In PostgreSQL, EVERY column in SELECT must either be:\n"
                "  1. Inside an aggregate function (SUM, COUNT, AVG, MAX, MIN), OR\n"
                "  2. Listed in the GROUP BY clause\n"
                "- Example: SELECT country, SUM(amount) FROM orders GROUP BY country -- country must be in GROUP BY\n"
                "- Use TO_CHAR(date, 'YYYY-MM') for year-month grouping\n"
                "- Use CURRENT_DATE for current date, date - INTERVAL 'N days' for date math\n"
                "- PREFER SIMPLE QUERIES: Use basic JOINs and single-level aggregations. Avoid complex multi-CTE queries.\n"
                "- Output only valid, executable PostgreSQL\n"
            )
        else:
            sql_system_prompt = (
                "You are a Microsoft SQL Server (T-SQL) expert.\n"
                "Return ONLY the SQL query, no explanations.\n"
                "CRITICAL T-SQL RULES:\n"
                "- READ ONLY: Only SELECT or WITH statements\n"
                "- Use SELECT TOP N instead of LIMIT\n"
                "- All non-aggregated columns in SELECT must be in GROUP BY\n"
                "- Use FORMAT(date, 'yyyy-MM') for year-month grouping\n"
                "- Use GETDATE() for current date, DATEADD() for date math\n"
                "- For monthly aggregations: GROUP BY FORMAT(DateColumn, 'yyyy-MM')\n"
                "- Output only valid, executable T-SQL\n"
            )
        
        # Include conversation context if available
        if conversation_context:
            human_message = "Schema:\n{schema}\n\nPrevious conversation:\n{history}\n\nCurrent question: {question}"
        else:
            human_message = "Schema:\n{schema}\n\nQuestion: {question}"
        
        sql_prompt = ChatPromptTemplate.from_messages([
            ("system", sql_system_prompt),
            ("human", human_message)
        ])
        
        if conversation_context:
            sql_raw = llm.invoke(sql_prompt.format_messages(schema=schema_ctx, history=conversation_context, question=question)).content
        else:
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
        data = _parse_raw_result(result, sql)
        
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
        
