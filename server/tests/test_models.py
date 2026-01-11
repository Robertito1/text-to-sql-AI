"""Unit tests for the models module."""
import pytest
from app.models import QueryRequest, QueryResponse, ChartConfig, ConversationMessage


class TestQueryRequest:
    """Tests for QueryRequest model."""
    
    def test_creates_with_question_only(self):
        req = QueryRequest(question="How many users?")
        assert req.question == "How many users?"
        assert req.history is None
    
    def test_creates_with_history(self):
        history = [
            ConversationMessage(role="user", content="Hello"),
            ConversationMessage(role="assistant", content="Hi there!")
        ]
        req = QueryRequest(question="Follow up", history=history)
        assert req.question == "Follow up"
        assert len(req.history) == 2


class TestQueryResponse:
    """Tests for QueryResponse model."""
    
    def test_creates_success_response(self):
        resp = QueryResponse(
            success=True,
            summary="Found 100 users",
            sql="SELECT COUNT(*) FROM users",
            data=[{"count": 100}]
        )
        assert resp.success is True
        assert resp.summary == "Found 100 users"
        assert resp.error is None
    
    def test_creates_error_response(self):
        resp = QueryResponse(
            success=False,
            summary="An error occurred",
            error="Database connection failed"
        )
        assert resp.success is False
        assert resp.error == "Database connection failed"


class TestChartConfig:
    """Tests for ChartConfig model."""
    
    def test_creates_bar_chart(self):
        chart = ChartConfig(
            type="bar",
            x_key="country",
            y_key="count",
            title="Customers by Country"
        )
        assert chart.type == "bar"
        assert chart.x_key == "country"
        assert chart.y_key == "count"
    
    def test_creates_chart_with_labels(self):
        chart = ChartConfig(
            type="line",
            x_key="month",
            y_key="revenue",
            title="Monthly Revenue",
            x_label="Month",
            y_label="Revenue ($)"
        )
        assert chart.x_label == "Month"
        assert chart.y_label == "Revenue ($)"


class TestConversationMessage:
    """Tests for ConversationMessage model."""
    
    def test_creates_user_message(self):
        msg = ConversationMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
    
    def test_creates_assistant_message(self):
        msg = ConversationMessage(role="assistant", content="Hi there!")
        assert msg.role == "assistant"
        assert msg.content == "Hi there!"
