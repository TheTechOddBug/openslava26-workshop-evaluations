"""Aggregate statistics for judge-agreement meta-evaluation."""

from __future__ import annotations

import math

from workshop_evals.domain.models import AgreementVerdict


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def pearson(xs: list[float], ys: list[float]) -> float:
    """Pearson correlation coefficient.

    Returns 0.0 when the input is too short, mismatched, or either series is constant.
    """
    n = len(xs)
    if n < 2 or len(ys) != n:
        return 0.0
    mx, my = _mean(xs), _mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=False))
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs) / n)
    sy = math.sqrt(sum((y - my) ** 2 for y in ys) / n)
    if sx == 0.0 or sy == 0.0:
        return 0.0
    return num / (n * sx * sy)


def _rank_list(xs: list[float]) -> list[float]:
    """Convert values to 1-indexed ranks; ties receive the mean rank."""
    indexed = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and xs[indexed[j + 1]] == xs[indexed[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[indexed[k]] = avg
        i = j + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float:
    """Spearman rank correlation (Pearson of ranks; ties get mean rank)."""
    if len(xs) < 2 or len(xs) != len(ys):
        return 0.0
    return pearson(_rank_list(xs), _rank_list(ys))


def rank_agreement(xs: list[float], ys: list[float]) -> float:
    """Fraction of concordant pairs over all i<j pairs.

    Tied pairs (dx*dy == 0) are excluded from the denominator.
    Returns 0.0 when there are no strictly ordered pairs.
    """
    concordant = discordant = 0
    n = len(xs)
    for i in range(n):
        for j in range(i + 1, n):
            product = (xs[i] - xs[j]) * (ys[i] - ys[j])
            if product > 0:
                concordant += 1
            elif product < 0:
                discordant += 1
    total = concordant + discordant
    return concordant / total if total > 0 else 0.0


def mae(xs: list[float], ys: list[float]) -> float:
    """Mean absolute error."""
    if not xs or len(xs) != len(ys):
        return 0.0
    return _mean([abs(x - y) for x, y in zip(xs, ys, strict=False)])


def agreement_verdict(pearson_r: float, mae_overall: float) -> AgreementVerdict:
    """Classify judge–reference agreement.

    RELIABLE:    pearson_r >= 0.7 and mae_overall <= 1.5
    QUESTIONABLE: pearson_r >= 0.4 (regardless of MAE)
    UNRELIABLE:  otherwise
    """
    if pearson_r >= 0.7 and mae_overall <= 1.5:
        return AgreementVerdict.RELIABLE
    if pearson_r >= 0.4:
        return AgreementVerdict.QUESTIONABLE
    return AgreementVerdict.UNRELIABLE
