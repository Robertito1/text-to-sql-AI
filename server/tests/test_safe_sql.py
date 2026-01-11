"""Unit tests for the safe_sql module."""
import pytest
from app.safe_sql import is_safe_readonly_sql


class TestIsSafeReadonlySql:
    """Tests for is_safe_readonly_sql function."""
    
    def test_allows_simple_select(self):
        sql = "SELECT * FROM users"
        assert is_safe_readonly_sql(sql) is True
    
    def test_allows_select_with_where(self):
        sql = "SELECT name, email FROM users WHERE active = true"
        assert is_safe_readonly_sql(sql) is True
    
    def test_allows_select_with_join(self):
        sql = "SELECT u.name, o.amount FROM users u JOIN orders o ON u.id = o.user_id"
        assert is_safe_readonly_sql(sql) is True
    
    def test_allows_select_with_aggregation(self):
        sql = "SELECT country, COUNT(*) FROM customers GROUP BY country"
        assert is_safe_readonly_sql(sql) is True
    
    def test_allows_cte_with_select(self):
        sql = "WITH cte AS (SELECT * FROM users) SELECT * FROM cte"
        assert is_safe_readonly_sql(sql) is True
    
    def test_rejects_insert(self):
        sql = "INSERT INTO users (name) VALUES ('test')"
        assert is_safe_readonly_sql(sql) is False
    
    def test_rejects_update(self):
        sql = "UPDATE users SET name = 'test' WHERE id = 1"
        assert is_safe_readonly_sql(sql) is False
    
    def test_rejects_delete(self):
        sql = "DELETE FROM users WHERE id = 1"
        assert is_safe_readonly_sql(sql) is False
    
    def test_rejects_drop(self):
        sql = "DROP TABLE users"
        assert is_safe_readonly_sql(sql) is False
    
    def test_rejects_truncate(self):
        sql = "TRUNCATE TABLE users"
        assert is_safe_readonly_sql(sql) is False
    
    def test_rejects_alter(self):
        sql = "ALTER TABLE users ADD COLUMN age INT"
        assert is_safe_readonly_sql(sql) is False
    
    def test_rejects_create(self):
        sql = "CREATE TABLE test (id INT)"
        assert is_safe_readonly_sql(sql) is False
    
    def test_rejects_grant(self):
        sql = "GRANT SELECT ON users TO public"
        assert is_safe_readonly_sql(sql) is False
    
    def test_rejects_exec(self):
        sql = "EXEC sp_executesql 'SELECT * FROM users'"
        assert is_safe_readonly_sql(sql) is False
    
    def test_handles_case_insensitive(self):
        sql = "select * from users"
        assert is_safe_readonly_sql(sql) is True
        
        sql = "DELETE from users"
        assert is_safe_readonly_sql(sql) is False
