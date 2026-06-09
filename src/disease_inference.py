"""
Dual-Layer Disease Inference Engine.

This module implements the dual-layer disease inference framework described in
Paper 1 §3.3, providing overt disease rules, hidden disease rules, and the
suppression/exclusion mechanism (Theorem 1).
"""

from typing import Dict, Set

# =============================================================================
# Disease inference rules
# =============================================================================

# Overt disease rules: fired when classified test reaches CRITICAL level
# Format: (disease_name, test_code, required_classification)
OVERT_RULES = [
    ("Diabetes_Mellitus",        "A1F",  "CRITICAL"),
    ("Hypothyroidism",            "TSH",  "CRITICAL"),
    ("Hyperthyroidism",          "TSH",  "CRITICAL"),
    ("High_Cardiovascular_Risk",  "CHOL", "CRITICAL"),
    ("Chronic_Kidney_Disease",    "CREA", "CRITICAL"),
    ("Liver_Disease",            "GOT",  "CRITICAL"),
    ("Anaemia",                  "HGB",  "CRITICAL"),
    ("Vitamin_D_Deficiency",     "VD3",  "CRITICAL"),
]

# Hidden disease rules: fired when classified test reaches ATTENTION level
# These detect subclinical conditions that may not trigger immediate alerts
HIDDEN_RULES = [
    ("Subclinical_Hypothyroidism", "TSH",  "ATTENTION"),
    ("Prediabetes",               "A1F",  "ATTENTION"),
    ("Early_CKD_Risk",           "CREA", "ATTENTION"),
    ("Chronic_Inflammation",       "CRP",  "ATTENTION"),
    ("Dyslipidaemia",             "CHOL", "ATTENTION"),
    ("B12_Deficiency_Risk",      "B12",  "ATTENTION"),
    ("Vitamin_D_Insufficiency",    "VD3",  "ATTENTION"),
]

# Suppression map: hidden disease -> overt disease that suppresses it
# If the overt disease is fired, the corresponding hidden disease is suppressed.
# None value means no suppression (hidden disease always fires independently).
SUPPRESSION_MAP = {
    "Subclinical_Hypothyroidism": "Hypothyroidism",
    "Prediabetes":               "Diabetes_Mellitus",
    "Early_CKD_Risk":            "Chronic_Kidney_Disease",
    "Chronic_Inflammation":       None,
    "Dyslipidaemia":             "High_Cardiovascular_Risk",
    "B12_Deficiency_Risk":      None,
    "Vitamin_D_Insufficiency":    "Vitamin_D_Deficiency",
}


# =============================================================================
# Inference functions
# =============================================================================

def fire_overt(classified: Dict[str, str]) -> Set[str]:
    """
    Fire overt disease rules based on CRITICAL test classifications.

    Args:
        classified: Dictionary mapping test_code -> classification (NORMAL/ATTENTION/CRITICAL)

    Returns:
        Set of disease names that were fired
    """
    fired = set()
    for disease, tc, cls in OVERT_RULES:
        if tc in classified and classified[tc] == cls:
            fired.add(disease)
    return fired


def fire_hidden(classified: Dict[str, str], overt: Set[str]) -> Set[str]:
    """
    Fire hidden disease rules based on ATTENTION test classifications,
    applying the suppression mechanism (Theorem 1).

    A hidden disease is suppressed if its corresponding overt disease
    (defined in SUPPRESSION_MAP) is also fired.

    Args:
        classified: Dictionary mapping test_code -> classification
        overt: Set of diseases already fired by overt rules

    Returns:
        Set of hidden diseases that were fired (after suppression)
    """
    fired = set()
    for disease, tc, cls in HIDDEN_RULES:
        if tc in classified and classified[tc] == cls:
            suppressor = SUPPRESSION_MAP.get(disease)
            if suppressor is None or suppressor not in overt:
                fired.add(disease)
    return fired


def infer_diseases(classified: Dict[str, str]) -> Dict[str, Set[str]]:
    """
    Run full dual-layer disease inference.

    Applies overt rules first, then hidden rules with suppression.

    Args:
        classified: Dictionary mapping test_code -> classification

    Returns:
        Dictionary with 'overt' and 'hidden' sets of disease names
    """
    overt = fire_overt(classified)
    hidden = fire_hidden(classified, overt)
    return {
        "overt": overt,
        "hidden": hidden,
        "all": overt | hidden
    }
