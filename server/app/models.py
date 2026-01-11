from pydantic import BaseModel
from typing import Any, Optional, List


class ConversationMessage(BaseModel):
    """A single message in the conversation history."""
    role: str  # 'user' or 'assistant'
    content: str


class QueryRequest(BaseModel):
    """Incoming payload for asking a SQL question in natural language."""
    question: str
    history: Optional[List[ConversationMessage]] = None  # Previous Q&A for context


class ChartConfig(BaseModel):
    """Configuration for rendering charts on the frontend."""
    type: str  # 'bar', 'line', 'pie', 'area'
    x_key: str  # Key for x-axis data
    y_key: str  # Key for y-axis data
    title: str
    x_label: Optional[str] = None
    y_label: Optional[str] = None


class QueryResponse(BaseModel):
    """Structured response for frontend consumption."""
    success: bool
    summary: str  # Natural language summary
    sql: str | None = None
    data: list[dict[str, Any]] | None = None  # Structured data for tables/charts
    chart: ChartConfig | None = None  # Chart configuration if applicable
    error: str | None = None
