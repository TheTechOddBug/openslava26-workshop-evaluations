"""Pure text-similarity scoring functions.

All functions operate on whitespace-tokenised, lowercased text and return
(score, detail) where score is in [0.0, 1.0].
"""

from __future__ import annotations

import difflib
import math


def _tokenize(text: str) -> list[str]:
    """Whitespace-split, lowercase tokens."""
    return text.lower().split()


def _ngrams(tokens: list[str], n: int) -> list[tuple[str, ...]]:
    """Return all n-grams from a token list."""
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def _count(items: list) -> dict:
    counts: dict = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return counts


def bleu(response: str, reference: str) -> tuple[float, str]:
    """Sentence BLEU up to 4-grams with brevity penalty and add-epsilon smoothing.

    Only computes n-gram levels up to min(4, len(hyp), len(ref)); each level
    receives equal weight.  Epsilon smoothing prevents log(0) when a clipped
    count is zero.
    """
    hyp = _tokenize(response)
    ref = _tokenize(reference)

    if not hyp or not ref:
        return 0.0, "empty input"

    epsilon = 1e-9
    max_n = min(4, len(hyp), len(ref))
    precisions: list[float] = []

    for n in range(1, max_n + 1):
        hyp_ng = _ngrams(hyp, n)
        ref_counts = _count(_ngrams(ref, n))
        hyp_counts = _count(hyp_ng)
        clipped = sum(min(cnt, ref_counts.get(ng, 0)) for ng, cnt in hyp_counts.items())
        denom = len(hyp_ng) if hyp_ng else 1
        precisions.append((clipped + epsilon) / (denom + epsilon))

    log_avg = sum(math.log(p) for p in precisions) / len(precisions)
    bp = 1.0 if len(hyp) >= len(ref) else math.exp(1.0 - len(ref) / len(hyp))
    score = bp * math.exp(log_avg)
    return float(score), f"bp={bp:.3f} precisions={[round(p, 3) for p in precisions]}"


def rouge_l(response: str, reference: str) -> tuple[float, str]:
    """LCS-based ROUGE-L F1 (beta=1)."""
    hyp = _tokenize(response)
    ref = _tokenize(reference)

    if not hyp or not ref:
        return 0.0, "empty input"

    m, n = len(ref), len(hyp)

    # Rolling-array DP for LCS length
    prev = [0] * (n + 1)
    for i in range(1, m + 1):
        curr = [0] * (n + 1)
        for j in range(1, n + 1):
            if ref[i - 1] == hyp[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(curr[j - 1], prev[j])
        prev = curr
    lcs_len = prev[n]

    precision = lcs_len / n
    recall = lcs_len / m
    f1 = 0.0 if precision + recall == 0.0 else 2.0 * precision * recall / (precision + recall)
    return float(f1), f"lcs={lcs_len} P={precision:.3f} R={recall:.3f}"


def fuzzy(response: str, reference: str) -> tuple[float, str]:
    """difflib.SequenceMatcher ratio on normalized (lowercased, stripped) text."""
    a = response.strip().lower()
    b = reference.strip().lower()
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    return float(ratio), f"ratio={ratio:.3f}"
