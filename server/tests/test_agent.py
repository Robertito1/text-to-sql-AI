"""Unit tests for the agent module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.agent import normalize_sql, extract_sql, _extract_column_names, _parse_raw_result


class TestNormalizeSql:
    """Tests for normalize_sql function."""
    
    def test_removes_markdown_code_fences(self):
        sql = "```sql\nSELECT * FROM users\n```"
        result = normalize_sql(sql)
        assert result == "SELECT * FROM users"
    
    def test_removes_code_fences_without_language(self):
        sql = "```\nSELECT * FROM users\n```"
        result = normalize_sql(sql)
        assert result == "SELECT * FROM users"
    
    def test_handles_plain_sql(self):
        sql = "SELECT * FROM users"
        result = normalize_sql(sql)
        assert result == "SELECT * FROM users"
    
    def test_handles_empty_string(self):
        result = normalize_sql("")
        assert result == ""
    
    def test_handles_none(self):
        result = normalize_sql(None)
        assert result is None
    
    def test_strips_whitespace(self):
        sql = "  SELECT * FROM users  "
        result = normalize_sql(sql)
        assert result == "SELECT * FROM users"


class TestExtractSql:
    """Tests for extract_sql function."""
    
    def test_extracts_select_statement(self):
        text = "Here is the query: SELECT * FROM users WHERE id = 1"
        result = extract_sql(text)
        assert "SELECT * FROM users" in result
    
    def test_extracts_with_statement(self):
        text = "WITH cte AS (SELECT * FROM users) SELECT * FROM cte"
        result = extract_sql(text)
        assert result.startswith("WITH")
    
    def test_handles_multiline_sql(self):
        text = """SELECT 
            name, 
            email 
        FROM users 
        WHERE active = true"""
        result = extract_sql(text)
        assert "SELECT" in result
        assert "FROM users" in result


class TestExtractColumnNames:
    """Tests for _extract_column_names function."""
    
    def test_extracts_simple_columns(self):
        sql = "SELECT name, email FROM users"
        result = _extract_column_names(sql)
        assert result == ["name", "email"]
    
    def test_extracts_aliased_columns(self):
        sql = "SELECT COUNT(*) AS total FROM users"
        result = _extract_column_names(sql)
        assert result == ["total"]
    
    def test_extracts_mixed_columns(self):
        sql = "SELECT country, COUNT(*) AS customer_count FROM customers GROUP BY country"
        result = _extract_column_names(sql)
        assert "country" in result
        assert "customer_count" in result
    
    def test_handles_star_select(self):
        sql = "SELECT * FROM users"
        result = _extract_column_names(sql)
        assert result == ['*']  # Returns ['*'] for star select


class TestParseRawResult:
    """Tests for _parse_raw_result function."""
    
    def test_parses_simple_result(self):
        raw = [('USA', 100), ('Canada', 50)]
        sql = "SELECT country, count FROM customers"
        result = _parse_raw_result(raw, sql)
        assert len(result) == 2
        assert result[0]["country"] == "USA"
        assert result[0]["count"] == 100
    
    def test_handles_empty_result(self):
        raw = []
        sql = "SELECT name FROM users"
        result = _parse_raw_result(raw, sql)
        assert result == []
    
    def test_handles_single_column(self):
        raw = [(100,)]
        sql = "SELECT COUNT(*) AS total FROM users"
        result = _parse_raw_result(raw, sql)
        assert result[0]["total"] == 100
