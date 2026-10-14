"""Unit tests for CandidateConfig.prompt_for: how a prompt override meets a case prompt."""

from workshop_evals.domain.models import PROMPT_PLACEHOLDER, CandidateConfig

CASE_PROMPT = 'Classify the sentiment.\n\nMessage: "Worst purchase I\'ve made in years."'


def _candidate(override: str | None) -> CandidateConfig:
    return CandidateConfig(model_id="m", prompt_override=override)


def test_placeholder_is_the_documented_one():
    assert PROMPT_PLACEHOLDER == "{prompt}"


def test_no_override_uses_the_case_prompt():
    assert _candidate(None).prompt_for(CASE_PROMPT) == CASE_PROMPT


def test_blank_override_uses_the_case_prompt():
    assert _candidate("  \n ").prompt_for(CASE_PROMPT) == CASE_PROMPT


def test_placeholder_is_replaced_by_the_case_prompt():
    override = "You are a sentiment classifier. Answer in one word.\n\nReview:\n{prompt}"
    assert _candidate(override).prompt_for(CASE_PROMPT) == (
        "You are a sentiment classifier. Answer in one word.\n\nReview:\n" + CASE_PROMPT
    )


def test_every_placeholder_is_replaced():
    assert _candidate("{prompt}\n---\n{prompt}").prompt_for("X") == "X\n---\nX"


def test_override_without_placeholder_is_sent_as_written():
    assert _candidate("What do you make of this?").prompt_for(CASE_PROMPT) == (
        "What do you make of this?"
    )


def test_other_braces_are_kept():
    # plain replacement, not str.format: JSON examples in a prompt must survive
    override = 'Reply as {"label": "<positive|negative|neutral>"}.\n\n{prompt}'
    assert _candidate(override).prompt_for("Great!") == (
        'Reply as {"label": "<positive|negative|neutral>"}.\n\nGreat!'
    )
