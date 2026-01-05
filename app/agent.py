import re
import logging
from typing import List
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

        # 2) Ask Ollama for SQL ONLY
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

        # 5) Summarize results
        logger.debug("Generating natural language summary")
        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", "Summarize SQL results for the user in a short, clear answer."),
            ("human", "Question: {question}\n\nSQL:\n{sql}\n\nRaw result:\n{result}")
        ])
        summary = llm.invoke(summary_prompt.format_messages(
            question=question, sql=sql, result=result
        )).content

        formatted_answer = f"{summary}\n\n---\n**SQL used:**\n```sql\n{sql}\n```\n\n---\n**Raw result:**\n```\n{result}\n```"
        return (formatted_answer, sql)
    
    except Exception as e:
        logger.error(f"Error in answer_question: {e}", exc_info=True)
        raise
