import json

from workshop_evals.domain.scoring.judge_rubric import (
    build_pairwise_messages,
    parse_pairwise_verdict,
)


def test_parse_json_winner_a():
    assert parse_pairwise_verdict('{"winner": "A", "justification": "clearer"}') == ("A", "clearer")


def test_parse_json_winner_b():
    winner, _ = parse_pairwise_verdict('{"winner": "B", "justification": "more complete"}')
    assert winner == "B"


def test_parse_keeps_a_long_justification_whole():
    long_text = "Answer A covers every requirement and explains its trade-offs. " * 5
    winner, justification = parse_pairwise_verdict(
        json.dumps({"winner": "A", "justification": long_text})
    )
    assert winner == "A"
    assert justification == long_text


def test_parse_verdict_missing_its_closing_brace():
    # without the JSON, the keyword fallback would see both "A" and "B" and call a tie
    text = '{\n  "winner": "B",\n  "justification": "Answer B covers A\'s points and more."'
    assert parse_pairwise_verdict(text) == ("B", "Answer B covers A's points and more.")


def test_parse_json_tie():
    winner, _ = parse_pairwise_verdict('{"winner": "tie", "justification": "equivalent"}')
    assert winner == "tie"


def test_parse_strips_thinking_block():
    text = "<think>let me weigh both</think>\n{\"winner\": \"A\", \"justification\": \"x\"}"
    assert parse_pairwise_verdict(text)[0] == "A"


def test_parse_keyword_fallback_a():
    assert parse_pairwise_verdict("A is the stronger answer here")[0] == "A"


def test_parse_keyword_fallback_b():
    assert parse_pairwise_verdict("B wins on completeness")[0] == "B"


def test_parse_keyword_fallback_tie():
    assert parse_pairwise_verdict("Honestly it is a tie")[0] == "tie"


def test_parse_ambiguous_defaults_to_tie():
    assert parse_pairwise_verdict("comparing A against B is hard")[0] == "tie"


def test_build_pairwise_messages_includes_both_answers():
    messages = build_pairwise_messages("Summarise X", "answer one", "answer two", reference="ref")
    assert messages[0]["role"] == "system"
    user = messages[1]["content"]
    assert "answer one" in user
    assert "answer two" in user
    assert "ref" in user
