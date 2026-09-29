"""Execute and compare SQL queries against an in-memory SQLite database.

Both the candidate query and the reference query are run against the same schema +
seed data.  Results are compared:
  - order-sensitive  when the reference query contains an ORDER BY clause
  - as multisets     otherwise (row order is ignored; duplicates still matter)

Returns None (not 0.0) when the reference query itself errors, which signals a
broken dataset entry rather than a model failure.
"""

from __future__ import annotations

import re
import sqlite3


def extract_sql(text: str) -> str:
    """Return the SQL statement from a model response.

    Strips a ```sql (or generic ```) fenced block when present; otherwise returns
    the raw text with a trailing semicolon removed so sqlite3 does not complain.
    """
    m = re.search(r"```(?:sql)?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    raw = m.group(1) if m else text
    return raw.strip().rstrip(";").strip()


def _execute(schema: str, query: str) -> tuple[list | None, str | None]:
    """Run `query` inside a fresh in-memory database initialised with `schema`.

    Returns (rows, None) on success or (None, error_message) on failure.
    """
    con = sqlite3.connect(":memory:")
    try:
        con.executescript(schema)
        rows = con.execute(query).fetchall()
        return rows, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    finally:
        con.close()


def run_sql(
    candidate_sql: str,
    reference_sql: str,
    schema: str,
) -> tuple[float | None, str]:
    """Score a candidate SQL query against a reference query.

    Args:
        candidate_sql: The SQL produced by the model under evaluation.
        reference_sql: The correct SQL from the dataset.
        schema:        DDL statements (CREATE TABLE, INSERT, etc.) to populate the
                       in-memory database before running either query.

    Returns:
        (None, detail)  if the reference query fails -- signals a broken dataset row.
        (0.0, detail)   if the candidate query fails or returns wrong results.
        (1.0, detail)   if the result sets match under the applicable comparison mode.
    """
    ref_rows, err = _execute(schema, reference_sql)
    if err is not None:
        return None, f"invalid reference: {err}"

    cand_rows, err = _execute(schema, candidate_sql)
    if err is not None:
        return 0.0, f"candidate query failed: {err}"

    order_sensitive = "order by" in reference_sql.lower()
    if order_sensitive:
        match = cand_rows == ref_rows
    else:
        match = sorted(map(repr, cand_rows)) == sorted(map(repr, ref_rows))

    detail = (
        f"rows_candidate={len(cand_rows)} "
        f"rows_reference={len(ref_rows)} "
        f"order_sensitive={order_sensitive}"
    )
    return 1.0 if match else 0.0, detail
