"""LLM-judge rubric: prompts, per-category dimension weights, and response parsing.

The judge receives a structured prompt asking it to score a model response across
five dimensions (0-10 each) and return a JSON object.  The weighted_score function
collapses those five dimensions into a single [0, 1] float using category-specific
weights that reflect what matters most per task type.
"""

from __future__ import annotations

import json
import re

# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------

DIMENSIONS = ["correctness", "completeness", "robustness", "clarity", "efficiency"]

# ---------------------------------------------------------------------------
# Per-category dimension weights (values sum to 1.0 within each category)
# ---------------------------------------------------------------------------

CATEGORY_WEIGHTS: dict[str, dict[str, float]] = {
    "code_generation": {
        "correctness": 0.40,
        "robustness": 0.25,
        "completeness": 0.20,
        "clarity": 0.10,
        "efficiency": 0.05,
    },
    "debugging": {
        "correctness": 0.40,
        "robustness": 0.25,
        "completeness": 0.20,
        "clarity": 0.10,
        "efficiency": 0.05,
    },
    "refactoring": {
        "correctness": 0.30,
        "clarity": 0.30,
        "robustness": 0.20,
        "completeness": 0.15,
        "efficiency": 0.05,
    },
    "reasoning": {
        "correctness": 0.45,
        "completeness": 0.30,
        "clarity": 0.15,
        "robustness": 0.10,
        "efficiency": 0.0,
    },
    "instruction_following": {
        "correctness": 0.45,
        "completeness": 0.30,
        "clarity": 0.15,
        "robustness": 0.10,
        "efficiency": 0.0,
    },
    "sql": {
        "correctness": 0.50,
        "efficiency": 0.20,
        "completeness": 0.20,
        "clarity": 0.10,
        "robustness": 0.0,
    },
    "infra_shell": {
        "correctness": 0.35,
        "robustness": 0.35,
        "clarity": 0.20,
        "completeness": 0.10,
        "efficiency": 0.0,
    },
    "code_review": {
        "correctness": 0.40,
        "completeness": 0.35,
        "clarity": 0.25,
        "robustness": 0.0,
        "efficiency": 0.0,
    },
}

DEFAULT_WEIGHTS: dict[str, float] = {
    "correctness": 0.40,
    "completeness": 0.25,
    "clarity": 0.20,
    "robustness": 0.10,
    "efficiency": 0.05,
}

# ---------------------------------------------------------------------------
# Judge prompts
# ---------------------------------------------------------------------------

JUDGE_SYSTEM: str = (
    "You are an expert, impartial evaluator. "
    "Score the model response across five dimensions using the reference as a "
    "high-quality benchmark. Be strict and consistent; do not reward verbosity. "
    "Return ONLY the requested JSON object, with no surrounding text or markdown."
)

JUDGE_TEMPLATE: str = """\
TASK:
{prompt}

EVALUATION RUBRIC{rubric_header}:
{rubric}

REFERENCE RESPONSE (high quality):
{reference}

MODEL RESPONSE TO EVALUATE:
{response}

Return ONLY this JSON object, with no surrounding text:
{{
  "correctness": <0-10>,
  "completeness": <0-10>,
  "robustness": <0-10>,
  "clarity": <0-10>,
  "efficiency": <0-10>,
  "justification": "<1-2 sentences>"
}}"""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def build_judge_messages(
    prompt: str,
    response: str,
    *,
    reference: str | None = None,
    rubric: list[str] | None = None,
) -> list[dict]:
    """Build the messages list for an LLM judge call.

    Args:
        prompt:    The original task prompt shown to the candidate model.
        response:  The candidate model's response to evaluate.
        reference: An optional high-quality reference answer.  When absent, the
                   judge is instructed to apply expert judgment in its place.
        rubric:    Optional list of evaluation criteria strings.  Rendered as a
                   bullet list when present.

    Returns:
        A two-element list: [system message dict, user message dict].
    """
    if rubric:
        rubric_text = "\n".join(f"- {criterion}" for criterion in rubric)
        rubric_header = " (item-specific criteria)"
    else:
        rubric_text = "(apply your own expert judgment)"
        rubric_header = ""

    reference_text = reference if reference is not None else "(none provided — use expert judgment)"

    content = JUDGE_TEMPLATE.format(
        prompt=prompt,
        rubric_header=rubric_header,
        rubric=rubric_text,
        reference=reference_text,
        response=response,
    )

    return [
        {"role": "system", "content": JUDGE_SYSTEM},
        {"role": "user", "content": content},
    ]


def weighted_score(dims: dict[str, float], category: str) -> float:
    """Collapse five dimension scores (0-10) into a single [0, 1] float.

    Uses the category-specific weights from CATEGORY_WEIGHTS, falling back to
    DEFAULT_WEIGHTS for unknown categories.  A category whose weights sum to zero
    returns 0.0 rather than raising.
    """
    weights = CATEGORY_WEIGHTS.get(category, DEFAULT_WEIGHTS)
    total_w = sum(weights.values())
    if total_w <= 0:
        return 0.0
    raw = sum(dims.get(k, 0.0) * w for k, w in weights.items())
    return max(0.0, min(1.0, raw / (total_w * 10.0)))


def _load_json_object(text: str) -> dict | None:
    """Return the JSON object in a judge reply, tolerating a reply cut off at the end.

    Small judges (Llama 3.2 3B, for one) often stop right before the closing brace, or
    inside the justification string. A complete object is preferred; otherwise the
    reply is closed with ``}`` or ``"}`` and parsed again. Returns None when no object
    can be read.
    """
    start = text.find("{")
    if start == -1:
        return None
    body = text[start:]
    candidates = []
    end = body.rfind("}")
    if end != -1:
        candidates.append(body[: end + 1])
    tail = body.rstrip().rstrip(",")
    candidates += [tail + "}", tail + '"}']
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def parse_judge_response(
    text: str,
    category: str,
) -> tuple[float, str, dict[str, float]]:
    """Parse the JSON verdict from a judge model response.

    Strips <think>...</think> reasoning blocks (produced by some reasoning models)
    before searching for the JSON object.  Dimension values are clamped to [0, 10].

    Args:
        text:     Raw text response from the judge model.
        category: Evaluation category, forwarded to weighted_score.

    Returns:
        (score, justification, dims)
        - score:         Weighted score in [0, 1].
        - justification: The judge's written justification, in full.
        - dims:          Dict mapping each dimension name to its raw score (0-10).

    On any parse failure returns (0.0, "unparseable judge output", {}).
    """
    # Remove reasoning blocks emitted by chain-of-thought models
    clean = re.sub(
        r"<think(?:ing)?>.*?</think(?:ing)?>", "", text, flags=re.DOTALL | re.IGNORECASE
    ).strip()

    verdict = _load_json_object(clean)
    if verdict is None:
        return 0.0, "unparseable judge output", {}

    try:
        dims: dict[str, float] = {}
        for dim in DIMENSIONS:
            raw_val = verdict.get(dim, 0)
            dims[dim] = max(0.0, min(10.0, float(raw_val)))

        score = weighted_score(dims, category)
        justification = str(verdict.get("justification", ""))
        return score, justification, dims
    except Exception:
        return 0.0, "unparseable judge output", {}


# ---------------------------------------------------------------------------
# Pairwise comparison
# ---------------------------------------------------------------------------

PAIRWISE_SYSTEM: str = (
    "You are an expert, impartial evaluator comparing two answers to the same task. "
    "Return ONLY the requested JSON object, with no surrounding text."
)

PAIRWISE_TEMPLATE: str = """\
TASK:
{prompt}

REFERENCE (high quality, may be absent):
{reference}

ANSWER A:
{answer_a}

ANSWER B:
{answer_b}

Decide which answer is better overall. Do not let the order (A/B) or the length influence
you; judge only quality. Return ONLY this JSON object, with no surrounding text:
{{
  "winner": "A" | "B" | "tie",
  "justification": "<1-2 sentences>"
}}"""


def build_pairwise_messages(
    prompt: str,
    answer_a: str,
    answer_b: str,
    *,
    reference: str | None = None,
) -> list[dict]:
    """Build the messages for a pairwise (A vs B) judge call."""
    reference_text = reference if reference is not None else "(none provided)"
    content = PAIRWISE_TEMPLATE.format(
        prompt=prompt, reference=reference_text, answer_a=answer_a, answer_b=answer_b
    )
    return [
        {"role": "system", "content": PAIRWISE_SYSTEM},
        {"role": "user", "content": content},
    ]


def parse_pairwise_verdict(text: str) -> tuple[str, str]:
    """Parse a pairwise verdict, returning ('A' | 'B' | 'tie', justification).

    Falls back to a keyword scan if the JSON is missing. Returns ('tie', ...) when
    the winner cannot be determined.
    """
    clean = re.sub(
        r"<think(?:ing)?>.*?</think(?:ing)?>", "", text, flags=re.DOTALL | re.IGNORECASE
    ).strip()
    winner = ""
    justification = ""
    verdict = _load_json_object(clean)
    if verdict is not None:
        winner = str(verdict.get("winner", "")).strip().upper()
        justification = str(verdict.get("justification", ""))
    if winner not in ("A", "B"):
        if winner == "TIE":
            return "tie", justification
        # keyword fallback on the cleaned text
        head = clean[:80].upper()
        if "TIE" in head:
            return "tie", justification or clean[:200]
        if "A" in head and "B" not in head:
            return "A", justification or clean[:200]
        if "B" in head and "A" not in head:
            return "B", justification or clean[:200]
        return "tie", justification or "undetermined verdict"
    return winner, justification
