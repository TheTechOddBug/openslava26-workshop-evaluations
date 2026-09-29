"""Pure deterministic scoring functions.

Each function returns (score, detail) where score is in [0.0, 1.0]
and detail is a human-readable string explaining the outcome.
"""

from __future__ import annotations

import json
import re


def _normalize(s: str) -> str:
    """Lowercase and strip leading/trailing whitespace and trailing punctuation."""
    s = s.strip().lower()
    s = re.sub(r"""[\s.,;:!?"'`]+$""", "", s).strip()
    return s


def exact_match(response: str, reference: str) -> tuple[float, str]:
    """Check whether the response matches any accepted reference variant.

    The reference may contain pipe-separated variants.  Both the full normalized
    response and its last non-empty line are checked for equality or containment
    against every variant.
    """
    cand_full = _normalize(response)
    lines = [line.strip() for line in response.strip().splitlines() if line.strip()]
    cand_last = _normalize(lines[-1]) if lines else ""

    for raw_variant in reference.split("|"):
        v = _normalize(raw_variant)
        if not v:
            continue
        if v in (cand_full, cand_last) or v in cand_full or v in cand_last:
            return 1.0, f"match '{raw_variant.strip()}'"

    preview = cand_last[:60] or cand_full[:60]
    return 0.0, f"no match (expected {reference!r}, got {preview!r})"


def _extract_final_number(text: str) -> float | None:
    """Return the last number from text, preferring a marked answer line.

    Looks for Answer: / Result: / Respuesta: markers first; falls back to
    the last numeric token in the whole text.
    """
    marked = re.findall(r"(?:answer|result|respuesta)\s*[:=]\s*(.+)", text, re.IGNORECASE)
    search_in = marked[-1] if marked else text
    nums = re.findall(r"-?\d+(?:[.,]\d+)?", search_in)
    if not nums and marked:
        nums = re.findall(r"-?\d+(?:[.,]\d+)?", text)
    return float(nums[-1].replace(",", ".")) if nums else None


def numeric(response: str, reference: str, rel_tol: float = 0.01) -> tuple[float, str]:
    """Score by comparing the final number in the response to the reference value.

    Uses relative tolerance with an absolute floor of 1e-6.
    Returns (0.0, detail) when no number can be extracted from the response.
    """
    got = _extract_final_number(response)
    if got is None:
        return 0.0, "no number found in response"
    try:
        want = float(reference.replace(",", "."))
    except ValueError:
        return 0.0, f"reference is not numeric: {reference!r}"

    tol = max(1e-6, abs(want) * rel_tol)
    ok = abs(got - want) <= tol
    return (1.0 if ok else 0.0), f"got={got} want={want}"


def regex_match(response: str, pattern: str) -> tuple[float, str]:
    """Return 1.0 when pattern matches anywhere in response, else 0.0."""
    try:
        m = re.search(pattern, response, re.MULTILINE | re.DOTALL)
    except re.error as exc:
        return 0.0, f"invalid regex: {exc}"
    if m:
        return 1.0, f"matched at position {m.start()}"
    return 0.0, "no match"


# ---------------------------------------------------------------------------
# Minimal JSON-Schema validator
# Supported keywords: type, required, properties, items
# ---------------------------------------------------------------------------

_SIMPLE_TYPES: dict[str, type | tuple[type, ...]] = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
}


def _validate(value: object, schema: dict, path: str = "$") -> str | None:
    """Recursively validate value against a minimal JSON-Schema subset.

    Returns None on success, or the first failure message string.
    """
    if not isinstance(schema, dict):
        return None

    type_name = schema.get("type")
    if type_name is not None:
        expected = _SIMPLE_TYPES.get(type_name)
        if expected is None:
            return f"{path}: unknown type {type_name!r}"
        # bool is a subclass of int; reject booleans when integer or number is expected
        if type_name in ("integer", "number") and isinstance(value, bool):
            return f"{path}: expected {type_name}, got boolean"
        if not isinstance(value, expected):
            return f"{path}: expected {type_name}, got {type(value).__name__}"

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                return f"{path}: missing required property '{key}'"
        for key, sub_schema in schema.get("properties", {}).items():
            if key in value:
                err = _validate(value[key], sub_schema, f"{path}.{key}")
                if err:
                    return err

    if isinstance(value, list):
        items_schema = schema.get("items")
        if items_schema is not None:
            for idx, item in enumerate(value):
                err = _validate(item, items_schema, f"{path}[{idx}]")
                if err:
                    return err

    return None


def _extract_json_value(text: str) -> object:
    """Strip markdown fences and think-blocks, then decode the first JSON value.

    Raises json.JSONDecodeError when no valid JSON is found.
    """
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"```(?:\w+)?\s*", "", text, flags=re.IGNORECASE).strip()

    decoder = json.JSONDecoder()
    for i in range(len(text)):
        if text[i] in ("{", "["):
            try:
                value, _ = decoder.raw_decode(text, i)
                return value
            except json.JSONDecodeError:
                pass

    # Last resort: parse the entire stripped text
    return json.loads(text)


def json_schema_match(response: str, schema: dict) -> tuple[float, str]:
    """Validate the first JSON value in response against a minimal schema subset.

    Handles markdown fences and <think> blocks in the response.
    """
    try:
        value = _extract_json_value(response)
    except (json.JSONDecodeError, ValueError) as exc:
        return 0.0, f"JSON parse error: {exc}"

    err = _validate(value, schema)
    if err:
        return 0.0, err
    return 1.0, "valid"
