"""Execute generated Python code against a test suite and return a pass/fail score.

Security note: running LLM-generated code in a subprocess carries inherent risk.
This implementation uses a local subprocess with a timeout, which is appropriate for
a controlled evaluation environment with trusted (or self-owned) eval datasets.
For real isolation, the same interface can be backed by an ephemeral Docker container
with --network none: replace the `cmd` list below with the docker invocation from the
reference implementation, keeping everything else identical.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tempfile


def _try_parse(code: str) -> str | None:
    """Return `code` if it is syntactically valid Python, else None."""
    try:
        ast.parse(code)
        return code
    except SyntaxError:
        return None


def extract_code(text: str) -> str:
    """Extract the Python snippet from a model response.

    Handles responses from reasoning models that wrap their chain-of-thought in
    <think>/<thinking> tags, as well as plain prose with an embedded code block.

    Extraction order:
      1. Strip <think>...</think> / <thinking>...</thinking> blocks.
      2. Match a ```python or ```py fenced block.
      3. Match an unlabelled ``` fenced block.
      4. Heuristic: find the first line that looks like Python (def/class/import/from/@)
         and collect from there to the end, trimming trailing prose lines until the
         remaining block parses.

    Each candidate is validated with ast.parse(). Returns "" if nothing parseable is found.
    """
    clean = re.sub(
        r"<think(?:ing)?>\s*.*?\s*</think(?:ing)?>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    ).strip()

    # Named fenced block
    m = re.search(r"```(?:python|py)\s*\n(.*?)```", clean, re.DOTALL)
    if m:
        candidate = m.group(1).strip()
        if _try_parse(candidate) is not None:
            return candidate

    # Unlabelled fenced block
    m = re.search(r"```[ \t]*\n(.*?)```", clean, re.DOTALL)
    if m:
        candidate = m.group(1).strip()
        if _try_parse(candidate) is not None:
            return candidate

    # Bare-code heuristic: start from the first Python-marker line
    lines = clean.splitlines()
    code_start: int | None = None
    for i, line in enumerate(lines):
        if re.match(r"[ \t]*(def |class |import |from |@)", line):
            code_start = i
            break

    if code_start is not None:
        block_lines = lines[code_start:]
        block = "\n".join(block_lines).strip()
        if _try_parse(block) is not None:
            return block
        # Trim trailing non-Python prose one line at a time
        for trim in range(1, len(block_lines)):
            trimmed = "\n".join(block_lines[:-trim]).strip()
            if trimmed and _try_parse(trimmed) is not None:
                return trimmed

    return ""


def run_code(code: str, tests: str, *, timeout: float = 10.0) -> tuple[float, str]:
    """Run `code` followed by `tests` in a fresh subprocess.

    The script is written to a temporary file and executed with the same Python
    interpreter that is running the evaluation process. `shell=False` is intentional
    -- we never pass the code through a shell.

    Returns:
        (1.0, "")  if the process exits with returncode 0 (all assertions passed).
        (0.0, detail)  otherwise, where `detail` is a short excerpt of stderr/stdout
            or "timeout" when the process exceeds `timeout` seconds.
    """
    script = f"{code}\n\n# --- tests ---\n{tests}\n"
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "candidate.py")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(script)
        try:
            result = subprocess.run(
                [sys.executable, path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return 0.0, "timeout"

        if result.returncode == 0:
            return 1.0, ""

        stderr = (result.stderr or result.stdout or "").strip()
        detail = stderr[-600:] if stderr else f"exit {result.returncode}"
        return 0.0, detail
