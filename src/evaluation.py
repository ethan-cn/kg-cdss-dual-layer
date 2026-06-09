"""
Baseline Comparison and Ablation Study Evaluation Engine.

This module implements the evaluation framework described in Paper 1 §5.2-5.4:
- B1/B2/B3/Full baseline comparison (Table 1-5)
- Config-1/3/6/9 authority ablation (Tables A-D)

Requires a Neo4j database populated with:
- Patient nodes (id)
- TestResult nodes with test_code and value
- NormalTest/AttentionTest/CriticalTest nodes (from Phase 2 classification)
- OvertDiseaseRisk/HiddenDiseaseRisk nodes (from Phase 2 inference)
"""

from __future__ import annotations

import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from neo4j import GraphDatabase

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
from credentials import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from .config import TARGET_DB

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
log = logging.getLogger("evaluation")

from .classification import (
    AUTHORITY_THRESHOLDS,
    ABLATION_CONFIGS,
    classify_nice_direct,
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


# =============================================================================
# TDL Reference Ranges (for B2 baseline)
# =============================================================================

TDL_THRESHOLDS: Dict[str, Tuple] = {
    "A1F":   (None,  5.7,   None,  None),
    "GLU":   (70.0,  100.0,  None,  None),
    "CHOL":  (None,  200.0, None,  None),
    "LDL":   (None,  100.0, None,  None),
    "TRI":   (None,  150.0, None,  None),
    "CRP":   (None,  5.0,   None,  None),
    "CREA":  (0.6,   1.2,   None,  None),
    "URE":   (7.0,   20.0,  None,  None),
    "TSH":   (0.4,   4.0,   None,  None),
    "T4L":   (12.0,  22.0,  None,  None),
    "T3L":   (3.1,   6.8,   None,  None),
    "HGB":   (12.0,  16.0,  None,  None),
    "ERY":   (3.8,   5.8,   None,  None),
    "GB":    (4000., 11000., None,  None),
    "PLA":   (150.,  400.,   None,  None),
    "FE":    (60.0,  170.0, None,  None),
    "B12":   (200.,  900.,   None,  None),
    "FOL":   (3.0,   17.0,  None,  None),
    "GGT":   (None,  60.0,  None,  None),
    "GOT":   (None,  40.0,  None,  None),
    "GPT":   (None,  41.0,  None,  None),
    "VD3":   (20.0,  50.0,  None,  None),
    "K":     (3.5,   5.0,   None,  None),
    "CL":    (98.0,  106.0, None,  None),
    "PT":    (64.0,  83.0,  None,  None),
    "RETI":  (5.0,   15.0,  None,  None),
    "ALBIM": (35.0,  50.0,  None,  None),
    "CAI":   (1.12,  1.32,  None,  None),
    "GLDH":  (None,  10.0,  None,  None),
    "CPK":   (30.0,  200.0, None,  None),
}


# =============================================================================
# Classification helpers
# =============================================================================

def classify_tdl(test_code: str, value: float) -> str:
    """
    Classify using TDL reference range (B2 baseline).
    TDL uses a single reference range with no critical threshold.
    """
    thresh = TDL_THRESHOLDS.get(test_code)
    if thresh is None:
        return "NORMAL"
    normal_low, normal_high, _, _ = thresh
    if normal_low is not None and value < normal_low:
        return "ATTENTION"
    if normal_high is not None and value > normal_high:
        return "ATTENTION"
    return "NORMAL"


# =============================================================================
# Database query functions
# =============================================================================

def get_test_values(driver) -> Dict[int, Dict[str, float]]:
    """Fetch all test values from database."""
    test_values: Dict[int, Dict[str, float]] = defaultdict(dict)
    with driver.session(database=TARGET_DB) as session:
        for label, rel in [("NormalTest", "HAS_NORMAL"),
                           ("AttentionTest", "NEEDS_ATTENTION"),
                           ("CriticalTest", "CRITICAL_ALERT")]:
            result = session.run(f"""
                MATCH (p:Patient)-[:{rel}]->(t:{label})
                WHERE t.value IS NOT NULL AND t.test_code IS NOT NULL
                RETURN p.id AS patient_id, t.test_code AS test_code, t.value AS value
            """)
            for record in result:
                pid = record["patient_id"]
                tc = record["test_code"]
                val = record["value"]
                if val is not None:
                    try:
                        test_values[pid][tc] = float(val)
                    except (ValueError, TypeError):
                        pass
    return dict(test_values)


def get_db_disease_risks(driver) -> Tuple[Dict[int, Set[str]], Dict[int, Set[str]]]:
    """Get current database disease risk assignments."""
    overt: Dict[int, Set[str]] = defaultdict(set)
    hidden: Dict[int, Set[str]] = defaultdict(set)
    with driver.session(database=TARGET_DB) as session:
        result = session.run("""
            MATCH (p:Patient)-[:HAS_DISEASE_RISK]->(o:OvertDiseaseRisk)
            RETURN p.id AS patient_id, o.disease AS disease
        """)
        for record in result:
            overt[record["patient_id"]].add(record["disease"])

        result = session.run("""
            MATCH (p:Patient)-[:HAS_POTENTIAL_RISK]->(h:HiddenDiseaseRisk)
            RETURN p.id AS patient_id, h.disease AS disease
        """)
        for record in result:
            hidden[record["patient_id"]].add(record["disease"])
    return dict(overt), dict(hidden)


# =============================================================================
# Baseline evaluation (B1/B2/B3/Full)
# =============================================================================

def run_baseline_evaluation():
    """Run B1/B2/B3/Full baseline comparison."""
    log.info("Paper 1 §5.3 — Baseline Evaluation: B1/B2/B3/Full")
    log.info("  Database: %s", TARGET_DB)
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        test_values = get_test_values(driver)
        db_overt, db_hidden = get_db_disease_risks(driver)

        n_total = len(test_values)
        all_patients = set(test_values.keys())

        b1_classified = {}
        b2_classified = {}
        b1_overt = {}
        b1_hidden = {}
        b2_overt = {}
        b2_hidden = {}
        b3_overt = {}

        for pid, values in test_values.items():
            b1_cls = {tc: classify_nice_direct(tc, v) for tc, v in values.items()}
            b2_cls = {tc: classify_tdl(tc, v) for tc, v in values.items()}

            b1_classified[pid] = b1_cls
            b2_classified[pid] = b2_cls

            fired_o1 = fire_overt(b1_cls)
            fired_h1 = fire_hidden(b1_cls, fired_o1)
            b1_overt[pid] = fired_o1
            b1_hidden[pid] = fired_h1

            fired_o2 = fire_overt(b2_cls)
            fired_h2 = fire_hidden(b2_cls, fired_o2)
            b2_overt[pid] = fired_o2
            b2_hidden[pid] = fired_h2

            b3_overt[pid] = fire_overt(b1_cls)

        _print_baseline_table1(b1_overt, b1_hidden, b2_overt, b2_hidden,
                               db_overt, db_hidden, all_patients, n_total)
        _print_baseline_table2(b1_overt, b2_overt, db_overt)
        _print_baseline_table3(b1_hidden, b2_hidden, db_hidden)
        _print_baseline_table4(b1_overt, b2_overt, db_overt, all_patients, n_total)

    finally:
        driver.close()


def _pct(n: int, total: int) -> str:
    if total == 0:
        return "0 (0.0%)"
    return f"{n} ({100*n/total:.1f}%)"


def _fmt(n: int) -> str:
    return f"{n:,}"


def _print_baseline_table1(b1_o, b1_h, b2_o, b2_h, db_o, db_h, patients, n_total):
    print("\n" + "=" * 78)
    print("  TABLE 1: Patient Coverage by Classification Mode")
    print("=" * 78)

    def count(has_dict, patients):
        return sum(1 for p in patients if has_dict.get(p))

    b1_ov = count(b1_o, patients)
    b2_ov = count(b2_o, patients)
    db_ov = count(db_o, patients)
    b1_hd = count(b1_h, patients)
    b2_hd = count(b2_h, patients)
    db_hd = count(db_h, patients)
    b1_nr = sum(1 for p in patients if not b1_o.get(p) and not b1_h.get(p))
    b2_nr = sum(1 for p in patients if not b2_o.get(p) and not b2_h.get(p))
    db_nr = sum(1 for p in patients if p not in db_o and p not in db_h)

    print(f"\n{'Mode':<22} {'≥1 Overt':<24} {'≥1 Hidden':<24} {'No Risk':<15}")
    print("-" * 85)
    print(f"{'B1 (NICE-only)':<22} {_pct(b1_ov, n_total):<24} {_pct(b1_hd, n_total):<24} {_pct(b1_nr, n_total):<15}")
    print(f"{'B2 (TDL range)':<22} {_pct(b2_ov, n_total):<24} {_pct(b2_hd, n_total):<24} {_pct(b2_nr, n_total):<15}")
    print(f"{'Full (Dual-layer)':<22} {_pct(db_ov, n_total):<24} {_pct(db_hd, n_total):<24} {_pct(db_nr, n_total):<15}")


def _print_baseline_table2(b1_o, b2_o, db_o):
    print("\n" + "=" * 78)
    print("  TABLE 2: Overt Disease Distribution — B1 vs B2 vs Full")
    print("=" * 78)

    b1_cnt = defaultdict(int)
    b2_cnt = defaultdict(int)
    db_cnt = defaultdict(int)

    for diseases in b1_o.values():
        for d in diseases:
            b1_cnt[d] += 1
    for diseases in b2_o.values():
        for d in diseases:
            b2_cnt[d] += 1
    for diseases in db_o.values():
        for d in diseases:
            db_cnt[d] += 1

    all_diseases = sorted(set(b1_cnt) | set(b2_cnt) | set(db_cnt))
    print(f"\n{'Disease':<28} {'B1':<10} {'B2':<10} {'Full':<10}")
    print("-" * 60)
    for d in all_diseases:
        print(f"{d:<28} {_fmt(b1_cnt[d]):<10} {_fmt(b2_cnt[d]):<10} {_fmt(db_cnt[d]):<10}")


def _print_baseline_table3(b1_h, b2_h, db_h):
    print("\n" + "=" * 78)
    print("  TABLE 3: Hidden Disease Distribution — B1 vs B2 vs Full")
    print("=" * 78)

    b1_cnt = defaultdict(int)
    b2_cnt = defaultdict(int)
    db_cnt = defaultdict(int)

    for diseases in b1_h.values():
        for d in diseases:
            b1_cnt[d] += 1
    for diseases in b2_h.values():
        for d in diseases:
            b2_cnt[d] += 1
    for diseases in db_h.values():
        for d in diseases:
            db_cnt[d] += 1

    all_diseases = sorted(set(b1_cnt) | set(b2_cnt) | set(db_cnt))
    print(f"\n{'Hidden Disease':<30} {'B1':<10} {'B2':<10} {'Full':<10}")
    print("-" * 62)
    for d in all_diseases:
        print(f"{d:<30} {_fmt(b1_cnt[d]):<10} {_fmt(b2_cnt[d]):<10} {_fmt(db_cnt[d]):<10}")


def _print_baseline_table4(b1_o, b2_o, db_o, patients, n_total):
    print("\n" + "=" * 78)
    print("  TABLE 4: Pairwise Patient-Level Agreement")
    print("=" * 78)

    b1_has = {p: bool(b1_o.get(p)) for p in patients}
    b2_has = {p: bool(b2_o.get(p)) for p in patients}
    db_has = {p: bool(db_o.get(p)) for p in patients}

    agree_12 = sum(1 for p in patients if b1_has[p] == b2_has[p])
    agree_1f = sum(1 for p in patients if b1_has[p] == db_has[p])
    agree_2f = sum(1 for p in patients if b2_has[p] == db_has[p])

    print(f"\n{'Comparison':<22} {'Agree':<18} {'Agreement':<12}")
    print("-" * 55)
    print(f"{'B1 vs B2':<22} {agree_12}/{n_total} ({100*agree_12/n_total:.1f}%)")
    print(f"{'B1 vs Full':<22} {agree_1f}/{n_total} ({100*agree_1f/n_total:.1f}%)")
    print(f"{'B2 vs Full':<22} {agree_2f}/{n_total} ({100*agree_2f/n_total:.1f}%)")


# =============================================================================
# Authority ablation (Config-1/3/6/9)
# =============================================================================

def run_ablation():
    """Run authority ablation study: Config-1 → 3 → 6 → 9."""
    log.info("Paper 1 §5.2 — Authority Ablation: Config-1/3/6/9")
    log.info("  Database: %s", TARGET_DB)
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        test_values = get_test_values(driver)
        n_total = len(test_values)
        all_patients = sorted(test_values.keys())

        config_results = {}

        for config_name, authorities in ABLATION_CONFIGS:
            log.info("  Processing %s (authorities: %s)", config_name, authorities)

            class_dist = {"NORMAL": 0, "ATTENTION": 0, "CRITICAL": 0}
            patient_overt: Dict[int, Set[str]] = {}
            patient_hidden: Dict[int, Set[str]] = {}
            ci_widths: List[float] = []
            result_count = 0

            for pid in all_patients:
                tests = test_values[pid]
                classified: Dict[str, str] = {}

                for tc, val in tests.items():
                    if "Config-1" in config_name:
                        cls = classify_nice_direct(tc, val)
                        classified[tc] = cls
                        class_dist[cls] += 1
                        ci_widths.append(0.199)
                        result_count += 1
                        if tc == "TSH":
                            if val >= 10.0:
                                classified["TSH_H"] = "CRITICAL"
                            elif val >= 4.0:
                                classified["TSH_H"] = "ATTENTION"
                            else:
                                classified["TSH_H"] = "NORMAL"
                            if val <= 0.4:
                                classified["TSH_L"] = "CRITICAL"
                            elif val <= 4.0:
                                classified["TSH_L"] = "NORMAL"
                            else:
                                classified["TSH_L"] = "ATTENTION"
                    else:
                        votes = vote_for_authorities(tc, val, authorities)
                        if votes:
                            cls = consensus_class(votes)
                            _, ci_w = consensus_confidence(votes, cls)
                            classified[tc] = cls
                            class_dist[cls] += 1
                            ci_widths.append(ci_w)
                            result_count += 1
                            if tc == "TSH":
                                if cls == "CRITICAL":
                                    classified["TSH_H"] = "CRITICAL" if val >= 10.0 else "CRITICAL"
                                    classified["TSH_L"] = "CRITICAL" if val <= 0.4 else "CRITICAL"
                                elif cls == "ATTENTION":
                                    classified["TSH_H"] = "ATTENTION" if val >= 4.0 else "ATTENTION"
                                    classified["TSH_L"] = "ATTENTION" if val <= 4.0 else "ATTENTION"
                                else:
                                    classified["TSH_H"] = "NORMAL"
                                    classified["TSH_L"] = "NORMAL"

                overt = fire_overt(classified)
                hidden = fire_hidden(classified, overt)
                patient_overt[pid] = overt
                patient_hidden[pid] = hidden

            avg_ci = sum(ci_widths) / len(ci_widths) if ci_widths else 0.0

            config_results[config_name] = {
                "n_authorities": len(authorities),
                "n_patients": n_total,
                "n_results": result_count,
                "class_dist": class_dist,
                "avg_ci_width": avg_ci,
                "patient_overt": patient_overt,
                "patient_hidden": patient_hidden,
            }

        _print_ablation_table_a(config_results, n_total)
        _print_ablation_table_b(config_results)
        _print_ablation_table_c(config_results)
        _print_ablation_table_d(config_results)

    finally:
        driver.close()


def _print_ablation_table_a(config_results, n_total):
    names = [n for n, _ in ABLATION_CONFIGS]

    print("\n" + "=" * 95)
    print("  TABLE A — Classification Distribution: Config-1(NICE) / 3 / 6 / 9")
    print("=" * 95)

    print(f"\n{'Config':<28} {'#Auth':>5} {'Covered':>8} {'NORMAL':>22} {'ATTENTION':>22} {'CRITICAL':>22} {'Avg CI':>10}")
    print("-" * 121)
    for name in names:
        r = config_results[name]
        dist = r["class_dist"]
        total = r["n_results"]
        print(
            f"{name:<28} "
            f"{r['n_authorities']:>5} "
            f"{_fmt(total):>8} "
            f"{_pct(dist['NORMAL'],    total):>22} "
            f"{_pct(dist['ATTENTION'], total):>22} "
            f"{_pct(dist['CRITICAL'],  total):>22} "
            f"{r['avg_ci_width']:>10.3f}"
        )


def _print_ablation_table_b(config_results):
    names = [n for n, _ in ABLATION_CONFIGS]

    all_overt = sorted(set(
        d for r in config_results.values()
          for s in r["patient_overt"].values()
          for d in s
    ))

    print("\n" + "=" * 95)
    print("  TABLE B — Overt Disease Distribution: Config-1 / 3 / 6 / 9")
    print("=" * 95)

    print(f"\n{'Disease':<28}", end="")
    for n in names:
        print(f" {n:>10}", end="")
    print()
    print("-" * (28 + 10 * len(names)))

    for disease in all_overt:
        print(f"{disease:<28}", end="")
        for name in names:
            cnt = sum(1 for s in config_results[name]["patient_overt"].values() if disease in s)
            print(f" {_fmt(cnt):>10}", end="")
        print()

    print(f"\n{'>=1 Overt (patient count)':<28}", end="")
    for name in names:
        cnt = sum(1 for s in config_results[name]["patient_overt"].values() if s)
        print(f" {_fmt(cnt):>10}", end="")
    print()
    print(f"{'(%)':<28}", end="")
    n_total = next(iter(config_results.values()))["n_patients"]
    for name in names:
        cnt = sum(1 for s in config_results[name]["patient_overt"].values() if s)
        print(f" {100*cnt/n_total:>10.1f}%", end="")
    print()


def _print_ablation_table_c(config_results):
    names = [n for n, _ in ABLATION_CONFIGS]

    all_hidden = sorted(set(
        d for r in config_results.values()
          for s in r["patient_hidden"].values()
          for d in s
    ))

    print("\n" + "=" * 95)
    print("  TABLE C — Hidden Disease Distribution: Config-1 / 3 / 6 / 9")
    print("=" * 95)

    print(f"\n{'Hidden Disease':<28}", end="")
    for n in names:
        print(f" {n:>10}", end="")
    print()
    print("-" * (28 + 10 * len(names)))

    for disease in all_hidden:
        print(f"{disease:<28}", end="")
        for name in names:
            cnt = sum(1 for s in config_results[name]["patient_hidden"].values() if disease in s)
            print(f" {_fmt(cnt):>10}", end="")
        print()

    print(f"\n{'>=1 Hidden (patient count)':<28}", end="")
    for name in names:
        cnt = sum(1 for s in config_results[name]["patient_hidden"].values() if s)
        print(f" {_fmt(cnt):>10}", end="")
    print()
    print(f"{'(%)':<28}", end="")
    n_total = next(iter(config_results.values()))["n_patients"]
    for name in names:
        cnt = sum(1 for s in config_results[name]["patient_hidden"].values() if s)
        print(f" {100*cnt/n_total:>10.1f}%", end="")
    print()


def _print_ablation_table_d(config_results):
    names = [n for n, _ in ABLATION_CONFIGS]

    print("\n" + "=" * 95)
    print("  TABLE D — Marginal Contribution: Added Authority Impact")
    print("=" * 95)

    print(f"\n{'Config':<10} {'Added':>16} {'d(CRITICAL)':>13} {'d(ATTENTION)':>13} "
          f"{'d(>=1 Overt)':>14} {'d(>=1 Hidden)':>14}")
    print("-" * 84)

    prev = None
    for i, name in enumerate(names):
        r = config_results[name]
        if prev is None:
            delta_crit = "—"
            delta_att = "—"
            delta_ov = "—"
            delta_hd = "—"
        else:
            delta_crit = r["class_dist"]["CRITICAL"] - prev["class_dist"]["CRITICAL"]
            delta_att = r["class_dist"]["ATTENTION"] - prev["class_dist"]["ATTENTION"]
            delta_ov = (
                sum(1 for s in r["patient_overt"].values() if s) -
                sum(1 for s in prev["patient_overt"].values() if s)
            )
            delta_hd = (
                sum(1 for s in r["patient_hidden"].values() if s) -
                sum(1 for s in prev["patient_hidden"].values() if s)
            )
        added = ", ".join(ABLATION_CONFIGS[i][1][len(prev["n_authorities"]) if prev else 0:]) if prev else "NICE"
        print(f"{name:<10} {added:>16} {str(delta_crit):>13} {str(delta_att):>13} "
              f"{str(delta_ov):>14} {str(delta_hd):>14}")
        prev = r


if __name__ == "__main__":
    run_baseline_evaluation()
    print("\n" + "=" * 78 + "\n")
    run_ablation()
