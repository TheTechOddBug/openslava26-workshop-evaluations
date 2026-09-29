"""Unit tests for workshop_evals.domain.scoring.code_exec."""

from workshop_evals.domain.scoring.code_exec import extract_code, run_code

# ---------------------------------------------------------------------------
# extract_code
# ---------------------------------------------------------------------------


class TestExtractCode:
    def test_fenced_python_block(self):
        text = "Here is the answer:\n```python\ndef add(a, b):\n    return a + b\n```\n"
        code = extract_code(text)
        assert "def add" in code
        assert "return a + b" in code

    def test_unlabelled_fenced_block(self):
        text = "```\ndef greet(name):\n    return f'Hello, {name}'\n```"
        code = extract_code(text)
        assert "def greet" in code

    def test_think_tags_stripped_before_extraction(self):
        text = (
            "<think>Let me reason step by step.\nThis is my chain of thought.</think>\n"
            "```python\ndef multiply(x, y):\n    return x * y\n```"
        )
        code = extract_code(text)
        assert "def multiply" in code
        assert "<think>" not in code

    def test_thinking_tags_variant(self):
        text = "<thinking>Internal reasoning here.</thinking>\n```python\nx = 1 + 1\n```"
        code = extract_code(text)
        assert "x = 1 + 1" in code

    def test_bare_code_heuristic(self):
        text = "Sure, here you go:\ndef square(n):\n    return n * n\n"
        code = extract_code(text)
        assert "def square" in code

    def test_invalid_syntax_falls_through_to_empty(self):
        text = "```python\ndef broken(\n    # no closing paren\n```"
        code = extract_code(text)
        assert code == ""

    def test_import_line_triggers_heuristic(self):
        text = "Here is the solution:\nimport math\nresult = math.sqrt(9)\n"
        code = extract_code(text)
        assert "import math" in code

    def test_empty_string_returns_empty(self):
        assert extract_code("") == ""

    def test_prose_only_returns_empty(self):
        assert extract_code("The answer is forty-two.") == ""


# ---------------------------------------------------------------------------
# run_code
# ---------------------------------------------------------------------------


class TestRunCode:
    def test_passing_code_returns_one(self):
        code = "def add(a, b):\n    return a + b\n"
        tests = "assert add(2, 3) == 5\nassert add(-1, 1) == 0\n"
        score, detail = run_code(code, tests)
        assert score == 1.0
        assert detail == ""

    def test_failing_assertion_returns_zero(self):
        code = "def add(a, b):\n    return a - b\n"  # wrong implementation
        tests = "assert add(2, 3) == 5\n"
        score, detail = run_code(code, tests)
        assert score == 0.0
        assert detail != ""  # some error info must be present

    def test_runtime_exception_returns_zero(self):
        code = "def divide(a, b):\n    return a / b\n"
        tests = "assert divide(1, 0) == 0\n"  # ZeroDivisionError
        score, detail = run_code(code, tests)
        assert score == 0.0
        assert "ZeroDivisionError" in detail or detail != ""

    def test_timeout_returns_zero_with_timeout_detail(self):
        code = "import time\ntime.sleep(60)\n"
        tests = "pass\n"
        score, detail = run_code(code, tests, timeout=0.5)
        assert score == 0.0
        assert "timeout" in detail.lower()

    def test_syntax_error_in_code_returns_zero(self):
        code = "def broken(\n"  # SyntaxError
        tests = "pass\n"
        score, detail = run_code(code, tests)
        assert score == 0.0

    def test_empty_code_returns_zero(self):
        score, detail = run_code("", "assert False\n")
        assert score == 0.0
