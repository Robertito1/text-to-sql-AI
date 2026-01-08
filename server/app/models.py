from pydantic import BaseModel
from typing import Any, Optional


class QueryRequest(BaseModel):
    """Incoming payload for asking a SQL question in natural language."""
    question: str


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
