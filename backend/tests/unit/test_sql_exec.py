"""Unit tests for workshop_evals.domain.scoring.sql_exec."""

from workshop_evals.domain.scoring.sql_exec import extract_sql, run_sql

SCHEMA = """
CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER);
INSERT INTO users VALUES (1, 'Alice', 30);
INSERT INTO users VALUES (2, 'Bob', 25);
INSERT INTO users VALUES (3, 'Charlie', 35);
"""


# ---------------------------------------------------------------------------
# extract_sql
# ---------------------------------------------------------------------------


class TestExtractSql:
    def test_fenced_sql_block(self):
        text = "The query is:\n```sql\nSELECT * FROM users\n```"
        sql = extract_sql(text)
        assert sql == "SELECT * FROM users"

    def test_unlabelled_fenced_block(self):
        text = "```\nSELECT name FROM users\n```"
        sql = extract_sql(text)
        assert sql == "SELECT name FROM users"

    def test_raw_text_passthrough(self):
        text = "SELECT id FROM users"
        assert extract_sql(text) == "SELECT id FROM users"

    def test_trailing_semicolon_stripped(self):
        text = "SELECT 1;"
        assert extract_sql(text) == "SELECT 1"


# ---------------------------------------------------------------------------
# run_sql
# ---------------------------------------------------------------------------


class TestRunSql:
    def test_correct_query_returns_one(self):
        candidate = "SELECT name FROM users WHERE id = 1"
        reference = "SELECT name FROM users WHERE id = 1"
        score, detail = run_sql(candidate, reference, SCHEMA)
        assert score == 1.0

    def test_wrong_query_returns_zero(self):
        candidate = "SELECT name FROM users WHERE id = 2"
        reference = "SELECT name FROM users WHERE id = 1"
        score, detail = run_sql(candidate, reference, SCHEMA)
        assert score == 0.0

    def test_order_by_order_sensitive_correct(self):
        reference = "SELECT name FROM users ORDER BY age ASC"
        candidate = "SELECT name FROM users ORDER BY age ASC"
        score, detail = run_sql(candidate, reference, SCHEMA)
        assert score == 1.0
        assert "order_sensitive=True" in detail

    def test_order_by_wrong_order_fails(self):
        reference = "SELECT name FROM users ORDER BY age ASC"
        candidate = "SELECT name FROM users ORDER BY age DESC"
        score, detail = run_sql(candidate, reference, SCHEMA)
        assert score == 0.0

    def test_no_order_by_insensitive_to_row_order(self):
        reference = "SELECT name FROM users"
        # Same rows, different order -- should still pass without ORDER BY
        candidate = "SELECT name FROM users ORDER BY name DESC"
        score, detail = run_sql(candidate, reference, SCHEMA)
        assert score == 1.0
        assert "order_sensitive=False" in detail

    def test_invalid_reference_returns_none(self):
        reference = "SELECT nonexistent_column FROM users"
        candidate = "SELECT name FROM users"
        score, detail = run_sql(candidate, reference, SCHEMA)
        assert score is None
        assert "invalid reference" in detail.lower()

    def test_candidate_syntax_error_returns_zero(self):
        reference = "SELECT name FROM users WHERE id = 1"
        candidate = "SELECT FROM WHERE"
        score, detail = run_sql(candidate, reference, SCHEMA)
        assert score == 0.0
        assert "failed" in detail.lower() or detail != ""

    def test_candidate_wrong_column_returns_zero(self):
        reference = "SELECT age FROM users WHERE id = 1"
        candidate = "SELECT age FROM users WHERE id = 2"
        score, detail = run_sql(candidate, reference, SCHEMA)
        assert score == 0.0

    def test_empty_candidate_reports_no_query(self):
        # e.g. a reasoning model that spent its whole token budget thinking
        reference = "SELECT name FROM users WHERE id = 1"
        score, detail = run_sql(extract_sql("   "), reference, SCHEMA)
        assert score == 0.0
        assert detail == "no SQL query found in the response"

    def test_empty_candidate_still_reports_a_broken_reference(self):
        score, detail = run_sql("", "SELECT nonexistent_column FROM users", SCHEMA)
        assert score is None
        assert "invalid reference" in detail.lower()
