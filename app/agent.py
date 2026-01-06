import re
import logging
from typing import List, Any, Tuple, Union, Optional
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

from .db import get_sql_database
from .schema_docs import SCHEMA_SNIPPETS
from .safe_sql import is_safe_readonly_sql
from .llm import get_llm

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
    """Remove markdown code fences from SQL queries."""
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

def _format_sql_result(question: str, sql: str, result: Any, llm: Any) -> str:
    """
    Format SQL query results into a user-friendly response.
    
    Args:
        question: The original user question
        sql: The SQL query that was executed
        result: The raw result from the database
        llm: The language model for generating summaries
        
    Returns:
        Formatted string with the query results
    """
    try:
        # Handle empty results
        if result is None:
            return "No results found.\n\n---\n**SQL used:**\n```sql\n{sql}\n```"
            
        # Handle single value results (like COUNT(*))
        if isinstance(result, (list, tuple)) and result and isinstance(result[0], (list, tuple)) and len(result[0]) == 1:
            value = result[0][0]
            # Special case for count-like queries
            if any(q in question.lower() for q in ["how many", "number of", "count of"]):
                try:
                    count = int(value) if value is not None else 0
                    noun = 'result' if 'result' in question.lower() else 'item'
                    noun = 'table' if 'table' in question.lower() else noun
                    return (
                        f"There {'is' if count == 1 else 'are'} {count} {noun}{'' if count == 1 else 's'}.\n\n"
                        f"---\n**SQL used:**\n```sql\n{sql}\n```\n\n"
                        f"---\n**Raw result:**\n```\n{result}\n```"
                    )
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not convert count result to integer: {e}")
        
        # For other results, use the LLM to generate a summary
        logger.debug("Generating natural language summary")
        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "You are a helpful SQL assistant. "
             "Summarize the query results in a clear, concise way. "
             "If the results are technical or complex, explain them in simple terms."),
            ("human", 
             "Question: {question}\n\n"
             "SQL Query:\n```sql\n{sql}\n```\n\n"
             "Query Results:\n```\n{result}\n```")
        ])
        
        summary = llm.invoke(summary_prompt.format_messages(
            question=question, 
            sql=sql, 
            result=str(result)[:2000]  # Limit size to avoid context window issues
        )).content
        
        return (
            f"{summary}\n\n"
            f"---\n**SQL used:**\n```sql\n{sql}\n```\n\n"
            f"---\n**Raw result (truncated):**\n```\n{str(result)[:500]}{'...' if len(str(result)) > 500 else ''}\n```"
        )
        
    except Exception as e:
        logger.error(f"Error formatting SQL result: {e}", exc_info=True)
        return (
            f"An error occurred while processing the query results.\n\n"
            f"---\n**SQL used:**\n```sql\n{sql}\n```\n\n"
            f"---\n**Raw result (truncated):**\n```\n{str(result)[:1000]}\n```\n\n"
            f"Error: {str(e)}"
        )

def answer_question(question: str) -> tuple[str, str]:
    """
    Answer a natural language question by generating and executing SQL.
    
    Args:
        question: Natural language question about the database
        
    Returns:
        Tuple of (formatted_answer, sql_query)
        
    Raises:
        ValueError: If question is empty or SQL generation fails
        RuntimeError: If database query execution fails
    """
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")
    
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
            "You are a SQL Server assistant.\n"
            "Return ONLY ONE SQL query.\n"
            "Rules:\n"
            "- READ ONLY (SELECT or WITH)\n"
            "- Prefer sys.tables / sys.columns over INFORMATION_SCHEMA\n"
            "- No explanations\n"
            ),
            ("human", "Schema:\n{schema}\n\nQuestion: {question}")
        ])
        
        sql_raw = llm.invoke(sql_prompt.format_messages(schema=schema_ctx, question=question)).content
        sql = extract_sql(sql_raw)
        sql = normalize_sql(sql)
        
        if not sql:
            logger.warning("LLM returned empty SQL")
            raise ValueError("Failed to generate SQL query from question")

        sql_raw = llm.invoke(sql_prompt.format_messages(schema=schema_ctx, question=question)).content
        sql = extract_sql(sql_raw)
        sql = normalize_sql(sql)
        
        if not sql:
            logger.warning("LLM returned empty SQL")
            raise ValueError("Failed to generate SQL query from question")
        
        logger.info(f"Generated SQL: {sql[:100]}...")

        # 3) Safe SQL guard
        if not is_safe_readonly_sql(sql):
            logger.warning(f"Unsafe SQL rejected: {sql}")
            error_msg = (
                "⚠️ Rejected unsafe SQL.\n\n"
                f"The generated query contains potentially dangerous operations.\n\n"
                f"Model output:\n```sql\n{sql}\n```"
            )
            return (error_msg, sql)

        # 4) Run query
        logger.debug("Executing SQL query")
        try:
            result = db.run(sql)
            logger.info("Query executed successfully")
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            raise RuntimeError(f"Failed to execute query: {str(e)}")

        # 5) Process and format the query results
        logger.debug("Processing query results")
        formatted_answer = _format_sql_result(question, sql, result, llm)
        return (formatted_answer, sql)
    
    except Exception as e:
        logger.error(f"Error in answer_question: {e}", exc_info=True)
        raise
        
