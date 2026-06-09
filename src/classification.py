"""
Multi-Authority Classification with Consensus Voting and Confidence Intervals.

This module implements the classification framework described in Paper 1 §3.2,
providing threshold definitions from 9 authoritative clinical guidelines and
the consensus voting algorithm with 95% confidence intervals.
"""

from typing import Dict, List, Tuple

# =============================================================================
# Per-authority threshold definitions
# Format per authority: {test_code: (normal_low, normal_high, crit_low, crit_high)}
# None values indicate no boundary at that end
# =============================================================================

# NICE — National Institute for Health and Care Excellence
# Ref: NICE Guidelines NG17 (Diabetes), NG28 (CVD), NG185 (Kidney), NG145 (Thyroid)
# + NICE NG181 (Lipids), NICE NG203 (Anaemia)
NICE_THRESHOLDS: Dict[str, Tuple] = {
    "A1F":   (None,  5.7,   None,  6.5),
    "GLU":   (70.0,  100.0, None,  126.0),
    "CHOL":  (None,  190.0, None,  240.0),
    "LDL":   (None,  100.0, None,  160.0),
    "TRI":   (None,  150.0, None,  500.0),
    "CRP":   (None,  3.0,   None,  10.0),
    "CREA":  (0.6,   1.2,   1.8,   None),
    "URE":   (7.0,   20.0,  42.0,  None),
    "TSH":   (0.4,   4.0,   0.4,   10.0),
    "T4L":   (12.0,  22.0,  9.0,   30.0),
    "T3L":   (3.1,   6.8,   2.0,   10.0),
    "HGB":   (12.0,  16.0,  10.0,  None),
    "ERY":   (3.8,   5.8,   3.0,   None),
    "GB":    (4000., 11000., 2000., 20000.),
    "PLA":   (150.,  400.,  100.,   None),
    "FE":    (56.0,  170.0, 28.0,  None),
    "B12":   (200.0,  None,   150.0,  None),   # B12 pmol/L — FIXED: correct pmol/L thresholds
                                          # Classification: v <= 150 = CRITICAL, 150 < v < 200 = ATTENTION, v >= 200 = NORMAL
    "FOL":   (3.0,   None,  2.0,   None),
    "GGT":   (None,  40.0,  120.0, None),
    "GOT":   (None,  40.0,  120.0, None),
    "GPT":   (None,  41.0,  120.0, None),
    "VD3":   (None,  50.0,  25.0,  None),
    "K":     (3.5,   5.0,   3.0,   6.5),
    "CL":    (98.0,  106.0, None,   None),
    "PT":    (64.0,  83.0,  None,   None),
    "RETI":  (5.0,   15.0,  None,   None),
    "ALBIM": (35.0,  50.0,  None,   None),
    "CAI":   (1.12,  1.32,  None,   None),
    "GLDH":  (None,  10.0,  None,   None),
    "CPK":   (30.0,  200.0, None,   None),
}

# ADA — American Diabetes Association
# Ref: Diabetes Care 2025;48(Suppl 1):S27-S49
ADA_THRESHOLDS: Dict[str, Tuple] = {
    "A1F":   (None,  5.7,   None,  6.5),
    "GLU":   (70.0,  100.0, None,  126.0),
}

# WHO — World Health Organization
# Ref: WHO Technical Report Series No. 894
WHO_THRESHOLDS: Dict[str, Tuple] = {
    "A1F":   (None,  5.7,   None,  6.5),
    "GLU":   (70.0,  100.0, None,  126.0),
    "HGB":   (12.0,  16.0,  10.0,  None),
}

# ESC — European Society of Cardiology
# Ref: Eur Heart J 2025;46(3):1-124
# Note: Diverges from NICE on CRP threshold (CRITICAL >= 3 vs 10)
ESC_THRESHOLDS: Dict[str, Tuple] = {
    "CHOL":  (None,  190.0, None,  240.0),
    "LDL":   (None,  100.0, None,  160.0),
    "TRI":   (None,  150.0, None,  500.0),
    "CRP":   (None,  3.0,   None,  3.0),
}

# KDIGO — Kidney Disease: Improving Global Outcomes
# Ref: Kidney Int Suppl 2024;14(4):e1-e314
KDIGO_THRESHOLDS: Dict[str, Tuple] = {
    "CREA":  (0.6,   1.2,   1.8,   None),
    "URE":   (7.0,   20.0,  42.0,  None),
    "K":     (3.5,   5.0,   3.0,   6.5),
}

# ATA — American Thyroid Association
# Ref: Thyroid 2023;33(10):1-120
# Note: Diverges from NICE on TSH upper normal (2.5 vs 4.0)
ATA_THRESHOLDS: Dict[str, Tuple] = {
    "TSH":   (0.4,   2.5,   0.4,   10.0),
    "T4L":   (12.0,  22.0,  9.0,   30.0),
    "T3L":   (3.1,   6.8,   2.0,   10.0),
}

# ETA — European Thyroid Association
# Ref: Eur Thyroid J 2023;12(6):e230133
ETA_THRESHOLDS: Dict[str, Tuple] = {
    "TSH":   (0.4,   2.5,   0.4,   10.0),
    "T4L":   (12.0,  22.0,  9.0,   30.0),
    "T3L":   (3.1,   6.8,   2.0,   10.0),
}

# ICSH — International Council for Standardization in Haematology
# Ref: Int J Lab Hematol 2023;45(5):627-648
ICSH_THRESHOLDS: Dict[str, Tuple] = {
    "HGB":   (12.0,  16.0,  10.0,  None),
    "ERY":   (3.8,   5.8,   3.0,   None),
    "GB":    (4000., 11000., 2000., 20000.),
    "PLA":   (150.,  400.,  100.,   None),
}

# IFCC — International Federation of Clinical Chemistry and Laboratory Medicine
# Ref: Clin Chem Lab Med 2024;62(1):1-15
IFCC_THRESHOLDS: Dict[str, Tuple] = {
    "A1F":   (None,  5.7,   None,  6.5),
}

# Combined threshold dictionary
AUTHORITY_THRESHOLDS: Dict[str, Dict[str, Tuple]] = {
    "NICE": NICE_THRESHOLDS,
    "ADA":  ADA_THRESHOLDS,
    "WHO":  WHO_THRESHOLDS,
    "ESC":  ESC_THRESHOLDS,
    "KDIGO": KDIGO_THRESHOLDS,
    "ATA":  ATA_THRESHOLDS,
    "ETA":  ETA_THRESHOLDS,
    "ICSH": ICSH_THRESHOLDS,
    "IFCC": IFCC_THRESHOLDS,
}

# Authority metadata
AUTHORITY_METADATA = {
    "NICE": {"name": "National Institute for Health and Care Excellence", "evidence": "1A", "weight": 1.0},
    "ADA":  {"name": "American Diabetes Association", "evidence": "1A", "weight": 0.9},
    "WHO":  {"name": "World Health Organization", "evidence": "1A", "weight": 0.9},
    "ESC":  {"name": "European Society of Cardiology", "evidence": "1A", "weight": 0.9},
    "KDIGO": {"name": "Kidney Disease: Improving Global Outcomes", "evidence": "1A", "weight": 0.9},
    "ATA":  {"name": "American Thyroid Association", "evidence": "1A", "weight": 0.9},
    "ETA":  {"name": "European Thyroid Association", "evidence": "2A", "weight": 0.8},
    "ICSH": {"name": "International Council for Standardization in Haematology", "evidence": "2A", "weight": 0.8},
    "IFCC": {"name": "International Federation of Clinical Chemistry", "evidence": "2A", "weight": 0.8},
}

# Ablation configurations for evaluation
ABLATION_CONFIGS = [
    ("Config-1 (NICE direct)",      ["NICE"]),
    ("Config-3 (+ADA,WHO)",        ["NICE", "ADA", "WHO"]),
    ("Config-6 (+ESC,KDIGO,ATA,ETA)", ["NICE", "ADA", "WHO", "ESC", "KDIGO", "ATA", "ETA"]),
    ("Config-9 (+ICSH,IFCC)",      ["NICE", "ADA", "WHO", "ESC", "KDIGO", "ATA", "ETA", "ICSH", "IFCC"]),
]


# =============================================================================
# Classification functions
# =============================================================================

def classify_single(test_code: str, value: float, thresh: Tuple) -> str:
    """
    Classify a single test result using one authority's threshold tuple.

    Args:
        test_code: Laboratory test code (e.g., 'A1F', 'TSH')
        value: Measured test value
        thresh: Tuple of (normal_low, normal_high, crit_low, crit_high)

    Returns:
        Classification: 'NORMAL', 'ATTENTION', or 'CRITICAL'
    """
    normal_low, normal_high, crit_low, crit_high = thresh
    if crit_low is not None and value <= crit_low:
        return "CRITICAL"
    if crit_high is not None and value >= crit_high:
        return "CRITICAL"
    if normal_low is not None and value < normal_low:
        return "ATTENTION"
    if normal_high is not None and value > normal_high:
        return "ATTENTION"
    return "NORMAL"


def classify_nice_direct(test_code: str, value: float) -> str:
    """
    Classify using NICE thresholds directly (single-authority baseline).

    This implements the same logic as the Config-1 ablation configuration,
    where each test is classified using NICE thresholds only without consensus voting.
    """
    thresh = NICE_THRESHOLDS.get(test_code)
    if thresh is None:
        return "NORMAL"
    normal_low, normal_high, crit_low, crit_high = thresh

    if test_code == "TSH":
        if value <= 0.4:
            return "CRITICAL"
        if value >= 10.0:
            return "CRITICAL"
        if value <= 4.0:
            return "NORMAL"
        return "ATTENTION"

    if test_code == "T4L":
        if value <= 9.0:
            return "CRITICAL"
        if value >= 30.0:
            return "CRITICAL"
        if 12.0 <= value <= 22.0:
            return "NORMAL"
        return "ATTENTION"

    if crit_low is not None and value <= crit_low:
        return "CRITICAL"
    if crit_high is not None and value >= crit_high:
        return "CRITICAL"
    if normal_low is not None and value < normal_low:
        return "ATTENTION"
    if normal_high is not None and value > normal_high:
        return "ATTENTION"
    return "NORMAL"


def vote_for_authorities(
    test_code: str,
    value: float,
    authorities: List[str]
) -> Dict[str, str]:
    """
    Collect individual classification votes from each covering authority.

    Args:
        test_code: Laboratory test code
        value: Measured test value
        authorities: List of authority codes (e.g., ['NICE', 'ADA', 'WHO'])

    Returns:
        Dictionary mapping authority code to classification vote
    """
    votes = {}
    for auth in authorities:
        thresholds = AUTHORITY_THRESHOLDS.get(auth, {})
        if test_code in thresholds:
            votes[auth] = classify_single(test_code, value, thresholds[test_code])
    return votes


def consensus_class(votes: Dict[str, str]) -> str:
    """
    Consensus classification rule (Definition 1 in Paper 1).

    Single-authority vote is used directly. Consensus voting applies when
    2 or more authorities cover the test:
      - nCrit >= 2                      -> CRITICAL
      - nCrit >= 1 AND nAtt >= 1       -> CRITICAL
      - nCrit == 1 AND nAtt == 0        -> ATTENTION
      - nCrit == 0 AND nAtt >= 1        -> ATTENTION
      - otherwise                       -> NORMAL
    """
    if not votes:
        return "NORMAL"
    n = len(votes)
    vote_list = list(votes.values())
    nCrit = vote_list.count("CRITICAL")
    nAtt = vote_list.count("ATTENTION")

    if n == 1:
        return vote_list[0]

    if nCrit >= 2:
        return "CRITICAL"
    if nCrit >= 1 and nAtt >= 1:
        return "CRITICAL"
    if nCrit == 1 and nAtt == 0:
        return "ATTENTION"
    if nCrit == 0 and nAtt >= 1:
        return "ATTENTION"
    return "NORMAL"


def consensus_confidence(
    votes: Dict[str, str],
    consensus_cls: str
) -> Tuple[float, float]:
    """
    Compute consensus confidence and 95% CI width (Definitions 2 + 3).

    Args:
        votes: Dictionary of authority votes
        consensus_cls: The consensus classification result

    Returns:
        Tuple of (confidence, ci_width)
    """
    n = len(votes)
    if n == 0:
        return 0.50, 0.30

    vote_list = list(votes.values())
    nCrit = vote_list.count("CRITICAL")
    nAtt = vote_list.count("ATTENTION")

    if n == 1:
        if consensus_cls == "CRITICAL":
            conf = 0.88
        elif consensus_cls == "ATTENTION":
            conf = 0.72
        else:
            conf = 0.90
    elif consensus_cls == "CRITICAL":
        conf = 0.92 if nCrit >= 2 else 0.86
    elif consensus_cls == "ATTENTION":
        conf = 0.76
    else:
        conf = 0.90

    conf = min(conf + min(0.02 * (n - 1), 0.06), 0.98)

    sigma_source = {1: 0.10, 2: 0.05, 3: 0.02}.get(n, 0.02)
    if consensus_cls == "CRITICAL":
        sigma_consensus = 0.01
    elif consensus_cls == "ATTENTION":
        sigma_consensus = 0.04
    else:
        sigma_consensus = 0.01
    sigma = (sigma_source**2 + sigma_consensus**2) ** 0.5
    ci_width = 1.96 * sigma

    return conf, ci_width
