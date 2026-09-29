from workshop_evals.domain.scoring.deterministic import (
    exact_match,
    json_schema_match,
    numeric,
    regex_match,
)


class TestExactMatch:
    def test_identical(self):
        score, _ = exact_match("Paris", "Paris")
        assert score == 1.0

    def test_case_insensitive(self):
        score, _ = exact_match("PARIS", "paris")
        assert score == 1.0

    def test_trailing_punctuation_stripped(self):
        score, _ = exact_match("Paris.", "Paris")
        assert score == 1.0

    def test_variant_pipe_first(self):
        score, _ = exact_match("forty-two", "forty-two|42")
        assert score == 1.0

    def test_variant_pipe_second(self):
        score, _ = exact_match("42", "forty-two|42|quarante-deux")
        assert score == 1.0

    def test_last_line_match(self):
        score, _ = exact_match("Some preamble\nParis", "Paris")
        assert score == 1.0

    def test_substring_of_full_response(self):
        score, _ = exact_match("The answer is Paris, France", "Paris")
        assert score == 1.0

    def test_substring_of_last_line(self):
        score, _ = exact_match("Step 1\nThe capital is Paris.", "Paris")
        assert score == 1.0

    def test_no_match(self):
        score, detail = exact_match("London", "Paris")
        assert score == 0.0
        assert "no match" in detail.lower()

    def test_empty_response(self):
        score, _ = exact_match("", "Paris")
        assert score == 0.0

    def test_empty_reference(self):
        # All variants are empty strings → all skipped → no match
        score, _ = exact_match("Paris", "")
        assert score == 0.0

    def test_multiline_last_line_wins(self):
        score, _ = exact_match("Berlin\nLondon\nParis", "Paris")
        assert score == 1.0

    def test_returns_detail_on_match(self):
        _, detail = exact_match("42", "42")
        assert "42" in detail


class TestNumeric:
    def test_exact_integer(self):
        score, detail = numeric("42", "42")
        assert score == 1.0
        assert "got=42" in detail

    def test_exact_float(self):
        score, _ = numeric("3.14", "3.14")
        assert score == 1.0

    def test_within_relative_tolerance(self):
        score, _ = numeric("100.5", "100", rel_tol=0.01)
        assert score == 1.0

    def test_outside_tolerance(self):
        score, _ = numeric("102", "100", rel_tol=0.01)
        assert score == 0.0

    def test_answer_marker(self):
        score, _ = numeric("Let me think...\nAnswer: 42", "42")
        assert score == 1.0

    def test_result_marker(self):
        score, _ = numeric("Result: 3.14", "3.14")
        assert score == 1.0

    def test_respuesta_marker(self):
        score, _ = numeric("Razonamiento...\nRespuesta: 100", "100")
        assert score == 1.0

    def test_last_number_fallback(self):
        # No marker → last number in text
        score, _ = numeric("Maybe 7 but actually 42", "42")
        assert score == 1.0

    def test_comma_decimal(self):
        score, _ = numeric("3,14", "3.14")
        assert score == 1.0

    def test_negative_number(self):
        score, _ = numeric("-5", "-5")
        assert score == 1.0

    def test_no_number(self):
        score, detail = numeric("I don't know", "42")
        assert score == 0.0
        assert "no number" in detail.lower()

    def test_non_numeric_reference(self):
        score, detail = numeric("42", "not-a-number")
        assert score == 0.0
        assert "not numeric" in detail.lower()

    def test_zero_reference_absolute_floor(self):
        # Reference is 0; absolute floor 1e-6 prevents division
        score, _ = numeric("0", "0")
        assert score == 1.0

    def test_detail_contains_want(self):
        _, detail = numeric("5", "10")
        assert "want=10" in detail


class TestRegexMatch:
    def test_simple_match(self):
        score, detail = regex_match("foo bar baz", r"bar")
        assert score == 1.0
        assert "matched" in detail.lower()

    def test_no_match(self):
        score, _ = regex_match("foo", r"bar")
        assert score == 0.0

    def test_multiline_flag(self):
        score, _ = regex_match("line1\nHELLO\nline3", r"^HELLO$")
        assert score == 1.0

    def test_dotall_flag(self):
        score, _ = regex_match("start\nmiddle\nend", r"start.*end")
        assert score == 1.0

    def test_invalid_regex(self):
        score, detail = regex_match("foo", r"[unclosed")
        assert score == 0.0
        assert "invalid regex" in detail.lower()

    def test_empty_response(self):
        score, _ = regex_match("", r"foo")
        assert score == 0.0

    def test_case_sensitive_by_default(self):
        score, _ = regex_match("HELLO", r"hello")
        assert score == 0.0

    def test_case_insensitive_flag_in_pattern(self):
        score, _ = regex_match("HELLO", r"(?i)hello")
        assert score == 1.0


class TestJsonSchemaMatch:
    def test_valid_empty_schema(self):
        score, detail = json_schema_match('{"name": "Alice"}', {})
        assert score == 1.0
        assert detail == "valid"

    def test_valid_object_type(self):
        score, _ = json_schema_match('{"name": "Alice"}', {"type": "object"})
        assert score == 1.0

    def test_valid_array_type(self):
        score, _ = json_schema_match('["a", "b"]', {"type": "array"})
        assert score == 1.0

    def test_wrong_type_string_vs_number(self):
        score, detail = json_schema_match('"hello"', {"type": "number"})
        assert score == 0.0
        assert "number" in detail

    def test_missing_required_property(self):
        schema = {"type": "object", "required": ["name"]}
        score, detail = json_schema_match('{"age": 1}', schema)
        assert score == 0.0
        assert "name" in detail

    def test_all_required_present(self):
        schema = {"type": "object", "required": ["a", "b"]}
        score, _ = json_schema_match('{"a": 1, "b": 2}', schema)
        assert score == 1.0

    def test_nested_property_correct_type(self):
        schema = {"type": "object", "properties": {"count": {"type": "integer"}}}
        score, _ = json_schema_match('{"count": 5}', schema)
        assert score == 1.0

    def test_nested_property_wrong_type(self):
        schema = {"type": "object", "properties": {"count": {"type": "integer"}}}
        score, detail = json_schema_match('{"count": "five"}', schema)
        assert score == 0.0
        assert "count" in detail

    def test_array_items_correct(self):
        schema = {"type": "array", "items": {"type": "string"}}
        score, _ = json_schema_match('["a", "b", "c"]', schema)
        assert score == 1.0

    def test_array_items_wrong_type(self):
        schema = {"type": "array", "items": {"type": "string"}}
        score, detail = json_schema_match('["a", 2]', schema)
        assert score == 0.0

    def test_invalid_json(self):
        score, detail = json_schema_match("not valid json", {"type": "object"})
        assert score == 0.0
        assert "parse" in detail.lower() or "json" in detail.lower()

    def test_markdown_fence_stripped(self):
        response = '```json\n{"key": "val"}\n```'
        score, _ = json_schema_match(response, {"type": "object"})
        assert score == 1.0

    def test_think_block_stripped(self):
        response = '<think>Let me reason...</think>\n{"key": "val"}'
        score, _ = json_schema_match(response, {"type": "object"})
        assert score == 1.0

    def test_boolean_rejected_as_integer(self):
        schema = {"type": "integer"}
        score, detail = json_schema_match("true", schema)
        assert score == 0.0
        assert "boolean" in detail

    def test_boolean_rejected_as_number(self):
        schema = {"type": "number"}
        score, detail = json_schema_match("false", schema)
        assert score == 0.0
        assert "boolean" in detail

    def test_json_preceded_by_preamble(self):
        response = 'Here is the result:\n{"x": 1}'
        score, _ = json_schema_match(response, {"type": "object"})
        assert score == 1.0
