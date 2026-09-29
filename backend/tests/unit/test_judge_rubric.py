"""Unit tests for workshop_evals.domain.scoring.judge_rubric."""

import json

import pytest

from workshop_evals.domain.scoring.judge_rubric import (
    CATEGORY_WEIGHTS,
    DIMENSIONS,
    JUDGE_SYSTEM,
    build_judge_messages,
    parse_judge_response,
    weighted_score,
)

# ---------------------------------------------------------------------------
# weighted_score
# ---------------------------------------------------------------------------


class TestWeightedScore:
    def test_perfect_scores_return_one(self):
        dims = dict.fromkeys(DIMENSIONS, 10.0)
        assert weighted_score(dims, "code_generation") == pytest.approx(1.0)

    def test_zero_scores_return_zero(self):
        dims = dict.fromkeys(DIMENSIONS, 0.0)
        assert weighted_score(dims, "code_generation") == pytest.approx(0.0)

    def test_known_category_uses_correct_weights(self):
        # For 'sql': correctness=0.50, so a response with only correctness=10
        # should score 0.50 * 10 / (1.0 * 10) = 0.50
        dims = dict.fromkeys(DIMENSIONS, 0.0)
        dims["correctness"] = 10.0
        score = weighted_score(dims, "sql")
        assert score == pytest.approx(0.50)

    def test_unknown_category_falls_back_to_defaults(self):
        dims = dict.fromkeys(DIMENSIONS, 10.0)
        assert weighted_score(dims, "unknown_category") == pytest.approx(1.0)

    def test_midpoint_dims_in_reasoning_category(self):
        # reasoning: correctness=0.45 completeness=0.30 clarity=0.15 robustness=0.10 efficiency=0.0
        dims = dict.fromkeys(DIMENSIONS, 5.0)
        score = weighted_score(dims, "reasoning")
        assert score == pytest.approx(0.5)

    def test_result_clamped_to_one(self):
        dims = dict.fromkeys(DIMENSIONS, 10.0)
        # Even with all 10s and any valid category the result must be <= 1.0
        for cat in CATEGORY_WEIGHTS:
            assert weighted_score(dims, cat) <= 1.0


# ---------------------------------------------------------------------------
# parse_judge_response
# ---------------------------------------------------------------------------


VALID_VERDICT = {
    "correctness": 8,
    "completeness": 7,
    "robustness": 6,
    "clarity": 9,
    "efficiency": 5,
    "justification": "The response is mostly correct but misses one edge case.",
}


class TestParseJudgeResponse:
    def test_parses_valid_json_verdict(self):
        text = json.dumps(VALID_VERDICT)
        score, justification, dims = parse_judge_response(text, "code_generation")
        assert 0.0 <= score <= 1.0
        assert dims["correctness"] == pytest.approx(8.0)
        assert dims["clarity"] == pytest.approx(9.0)
        assert "correct" in justification.lower() or justification != ""

    def test_strips_think_tags_before_parsing(self):
        think_prefix = "<think>Let me evaluate this carefully...</think>\n"
        text = think_prefix + json.dumps(VALID_VERDICT)
        score, justification, dims = parse_judge_response(text, "code_generation")
        assert 0.0 <= score <= 1.0
        assert len(dims) == len(DIMENSIONS)

    def test_strips_thinking_tags_variant(self):
        text = "<thinking>internal</thinking>" + json.dumps(VALID_VERDICT)
        score, justification, dims = parse_judge_response(text, "debugging")
        assert score > 0.0

    def test_clamps_out_of_range_values(self):
        verdict = dict.fromkeys(DIMENSIONS, 15.0)
        verdict["justification"] = "too high"
        text = json.dumps(verdict)
        _, _, dims = parse_judge_response(text, "code_generation")
        for v in dims.values():
            assert v <= 10.0

    def test_clamps_negative_values(self):
        verdict = dict.fromkeys(DIMENSIONS, -3.0)
        verdict["justification"] = "negative"
        text = json.dumps(verdict)
        _, _, dims = parse_judge_response(text, "code_generation")
        for v in dims.values():
            assert v >= 0.0

    def test_unparseable_text_returns_zero(self):
        score, justification, dims = parse_judge_response("no json here", "code_generation")
        assert score == 0.0
        assert justification == "unparseable judge output"
        assert dims == {}

    def test_malformed_json_returns_zero(self):
        score, justification, dims = parse_judge_response("{broken json", "code_generation")
        assert score == 0.0
        assert dims == {}

    def test_empty_string_returns_zero(self):
        score, justification, dims = parse_judge_response("", "code_generation")
        assert score == 0.0


# ---------------------------------------------------------------------------
# build_judge_messages
# ---------------------------------------------------------------------------


class TestBuildJudgeMessages:
    def test_returns_two_messages(self):
        msgs = build_judge_messages("Write a sort function.", "def sort(lst): return sorted(lst)")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"

    def test_system_message_content(self):
        msgs = build_judge_messages("prompt", "response")
        assert msgs[0]["content"] == JUDGE_SYSTEM

    def test_rubric_included_when_provided(self):
        rubric = ["Must handle empty input", "Must be O(n log n)"]
        msgs = build_judge_messages(
            "Sort an array.", "def sort(lst): return sorted(lst)", rubric=rubric
        )
        user_content = msgs[1]["content"]
        assert "Must handle empty input" in user_content
        assert "Must be O(n log n)" in user_content

    def test_reference_included_when_provided(self):
        msgs = build_judge_messages(
            "Add two numbers.",
            "def add(a, b): return a + b",
            reference="def add(a, b):\n    return a + b",
        )
        user_content = msgs[1]["content"]
        assert "def add(a, b):" in user_content

    def test_no_reference_inserts_expert_judgment_instruction(self):
        msgs = build_judge_messages("Do something.", "response without reference")
        user_content = msgs[1]["content"]
        assert "expert judgment" in user_content.lower()

    def test_no_rubric_inserts_expert_judgment_instruction(self):
        msgs = build_judge_messages("Do something.", "response without rubric")
        user_content = msgs[1]["content"]
        assert "expert judgment" in user_content.lower()

    def test_prompt_and_response_appear_in_user_message(self):
        prompt = "Write a unique sentinel prompt string 12345."
        response = "def unique_sentinel_67890(): pass"
        msgs = build_judge_messages(prompt, response)
        user_content = msgs[1]["content"]
        assert prompt in user_content
        assert response in user_content
