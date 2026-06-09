"""
__init__.py — Paper 1: Dual-Layer Disease Inference Framework

Core modules:
    - classification: Multi-authority consensus classification with 95% CI
    - disease_inference: Overt/Hidden dual-layer disease rules
    - evaluation: Baseline comparison and ablation studies
"""

from .classification import (
    AUTHORITY_THRESHOLDS,
    AUTHORITY_METADATA,
    classify_single,
    vote_for_authorities,
    consensus_class,
    consensus_confidence,
)

from .disease_inference import (
    OVERT_RULES,
    HIDDEN_RULES,
    SUPPRESSION_MAP,
    fire_overt,
    fire_hidden,
)

__all__ = [
    "AUTHORITY_THRESHOLDS",
    "AUTHORITY_METADATA",
    "classify_single",
    "vote_for_authorities",
    "consensus_class",
    "consensus_confidence",
    "OVERT_RULES",
    "HIDDEN_RULES",
    "SUPPRESSION_MAP",
    "fire_overt",
    "fire_hidden",
]
