from pydantic import BaseModel


class QueryRequest(BaseModel):
    """
    Incoming payload for asking a SQL question in natural language.
    Example:
    {
        "question": "What is total revenue per month for 2024?"
    }
    """
    question: str


class QueryResponse(BaseModel):
    """
    Outgoing response from the API.
    - answer: natural language explanation or result
    - sql: the SQL that was generated/executed (optional but useful for debugging/demo)
    """
    answer: str
    sql: str | None = None
