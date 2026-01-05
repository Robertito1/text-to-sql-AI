import re

# Keywords we never want to allow
BLOCKLIST = {
    "insert", "update", "delete", "drop", "truncate", "alter", "create",
    "grant", "revoke", "merge", "exec", "execute", "xp_", "sp_", "backup",
    "restore", "dbcc", "shutdown", "kill"
}

def strip_sql_comments(sql: str) -> str:
    # remove /* ... */ and -- ...\n
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.S)
    sql = re.sub(r"--.*?$", "", sql, flags=re.M)
    return sql

def is_safe_readonly_sql(sql: str) -> bool:
    if not sql or not sql.strip():
        return False

    cleaned = strip_sql_comments(sql).strip()
    lowered = cleaned.lower()

    # Block multiple statements (simple + effective)
    if ";" in lowered.rstrip(";"):
        # allows a single trailing semicolon only
        return False

    # Must start with SELECT or WITH (CTE)
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return False

    # Block any dangerous keyword anywhere
    tokens = re.findall(r"[a-zA-Z_]+", lowered)
    for t in tokens:
        if t in BLOCKLIST:
            return False
        # block xp_cmdshell etc.
        if t.startswith("xp_") or t.startswith("sp_"):
            return False

    return True
