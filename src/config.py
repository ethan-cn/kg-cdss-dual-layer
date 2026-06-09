"""
Neo4j Connection and Database Configuration for Paper 1.

This module provides database connection parameters and schema constants
for the dual-layer disease inference framework.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from credentials import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# Database configuration
PAPER1_DB = "paper1"       # Evaluation database (3,869 NICE-covered patients analysed in the paper)
TARGET_DB = PAPER1_DB

# Disease identifiers for inference
DISEASE_IDS = [
    "diabetes_mellitus",
    "hypothyroidism",
    "hyperthyroidism",
    "anaemia",
    "cardiovascular_disease",
    "liver_dysfunction",
    "chronic_kidney_disease",
    "vitamin_d_deficiency",
    "gastroesophageal_reflux",
    "irritable_bowel_syndrome",
    "urinary_tract_infection",
    "b12_folate_deficiency",
    "thyroid_nodule",
    "depression",
    "infection_sepsis_risk",
]

# Logging configuration
LOG_FORMAT = "%(asctime)s  %(levelname)-8s  %(message)s"
LOG_DATE = "%Y-%m-%d %H:%M:%S"
