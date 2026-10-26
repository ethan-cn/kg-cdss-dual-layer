"""Consensus label (Definition 1, as revised), agreement count k/n, and inter-authority uncertainty index U(t) (Definition 2).

Definition 1 (revised, author decision D4 = keep rule, state it exactly):
  |A_t| = 1             -> the single authority's vote
  |A_t| >= 2:
    CRITICAL  if nCrit >= 2 or (nCrit >= 1 and nAtt >= 1)
    ATTENTION if (nCrit == 0 and nAtt >= 1) or (nCrit == 1 and nAtt == 0)
    NORMAL    otherwise
"""
from __future__ import annotations

import math
from collections import Counter

from .classify import ATTENTION, CRITICAL, NORMAL

# Definition 2 / SI Eq. A.3 and Appendix F.2 (author approval 2026-10-19, item R2-M3). Design constants, not estimates.
# U(t) = sqrt(sigma_source^2 + sigma_disagree^2); no z multiplier: U is a descriptive index, not a confidence interval.
U_PARAMS = {
    "sigma_source": {1: 0.10, 2: 0.05, "3+": 0.02},
    "sigma_disagree": {"unanimous": 0.01, "majority": 0.06, "split_or_tie": 0.12},
}


def consensus_label(levels: list[str]) -> str:
    if not levels:
        raise ValueError("no covering authority")
    if len(levels) == 1:
        return levels[0]
    n_crit, n_att = levels.count(CRITICAL), levels.count(ATTENTION)
    if n_crit >= 2 or (n_crit >= 1 and n_att >= 1):
        return CRITICAL
    if (n_crit == 0 and n_att >= 1) or (n_crit == 1 and n_att == 0):
        return ATTENTION
    return NORMAL


def consensus_direction(votes: list[tuple[str, str]], label: str) -> str:
    """Direction of the consensus: the direction shared by the non-NORMAL votes; 'conflict' if they disagree."""
    if label == NORMAL:
        return "none"
    dirs = {d for lv, d in votes if lv != NORMAL}
    if len(dirs) == 1:
        return dirs.pop()
    return "conflict"


def agreement(levels: list[str], label: str) -> tuple[int, int]:
    return levels.count(label), len(levels)


def agreement_pattern(levels: list[str]) -> str:
    c = Counter(levels)
    if len(c) == 1:
        return "unanimous"
    top = c.most_common()
    if len(c) == 3 or top[0][1] == top[1][1]:
        return "split_or_tie"
    return "majority"


def uncertainty_index(levels: list[str], params: dict = U_PARAMS) -> float:
    """U(t) of SI Eq. A.3 for the votes of the covering authorities."""
    n = len(levels)
    s_src = params["sigma_source"][n] if n in (1, 2) else params["sigma_source"]["3+"]
    s_dis = params["sigma_disagree"][agreement_pattern(levels)]
    return math.sqrt(s_src ** 2 + s_dis ** 2)
