"""Unit tests for the canonical implementation. Run: python -m tests.test_core  (no pytest needed)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from cdss.classify import ATTENTION, CRITICAL, NORMAL, SpecError, classify, validate_row  # noqa: E402
from cdss.consensus import consensus_label, uncertainty_index  # noqa: E402
from cdss.data import parse_value  # noqa: E402
from cdss.rules import check_non_overlap, evaluate  # noqa: E402

FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)


def test_every_spec_row_classifies_in_its_own_direction():
    spec = json.loads((HERE / "spec/thresholds.json").read_text(encoding="utf-8"))
    for r in spec["rows"]:
        validate_row(r)
        tag = f'{r["authority"]}/{r["analyte"]}'
        if r.get("high_critical") is not None:
            check(classify(r["high_critical"] * 1.5, r) == (CRITICAL, "high"), f"{tag} far above high_critical")
        if r.get("low_critical") is not None:
            check(classify(r["low_critical"] * 0.5, r) == (CRITICAL, "low"), f"{tag} far below low_critical")
        lo = r.get("low_attention") or r.get("low_critical")
        hi = r.get("high_attention") or r.get("high_critical")
        if lo is not None and hi is not None:
            mid = (lo + hi) / 2
        elif lo is not None:
            mid = lo * 1.5
        else:
            mid = hi * 0.5
        check(classify(mid, r)[0] == NORMAL, f"{tag} mid-normal value {mid} not NORMAL")


def test_validator_rejects_submitted_inverted_tuples():
    # Submitted tuple (normal_low, normal_high, crit_low, crit_high) = (0.6, 1.2, 1.8, None) for CREA,
    # expressed with explicit names: low_critical=1.8 above low_attention=0.6 must be rejected.
    for bad in ({"low_critical": 1.8, "low_attention": 0.6, "high_attention": 1.2},
                {"low_critical": 120.0, "high_attention": 40.0},          # GOT/GGT
                {"low_critical": 25.0, "high_attention": 50.0, "low_attention": 50.0}):  # VD3
        try:
            validate_row(dict(bad, authority="X", analyte="Y", unit="u"))
            FAILS.append(f"validator accepted inverted row {bad}")
        except SpecError:
            pass


def test_boundaries_follow_source_wording():
    nice_b12 = {"authority": "NICE", "analyte": "B12", "unit": "ng/L", "low_critical": 180.0, "low_attention": 350.0,
                "low_critical_op": "lt", "low_attention_op": "le"}
    check(classify(179.9, nice_b12)[0] == CRITICAL, "B12 179.9 critical")
    check(classify(180.0, nice_b12)[0] == ATTENTION, "B12 180 indeterminate")
    check(classify(350.0, nice_b12)[0] == ATTENTION, "B12 350 indeterminate")
    check(classify(350.1, nice_b12)[0] == NORMAL, "B12 350.1 unlikely")


def test_definition_1():
    check(consensus_label([CRITICAL]) == CRITICAL, "single authority CRITICAL")
    check(consensus_label([CRITICAL, ATTENTION] + [NORMAL] * 5) == CRITICAL, "1C+1A+5N")
    check(consensus_label([CRITICAL, NORMAL, NORMAL]) == ATTENTION, "1C+2N")
    check(consensus_label([ATTENTION, NORMAL]) == ATTENTION, "1A+1N")
    check(consensus_label([NORMAL, NORMAL]) == NORMAL, "2N")


def test_uncertainty_index_definition_2():
    U = uncertainty_index
    single, split3, tie2, unan3 = U([NORMAL]), U([CRITICAL, ATTENTION, NORMAL]), U([ATTENTION, NORMAL]), U([NORMAL, NORMAL, NORMAL])
    check(split3 > single, "three-way split must exceed a single uncontested authority (R2 M3c)")
    check(tie2 > single, "tie must exceed a single uncontested authority")
    check(unan3 < single, "unanimous three below a single authority")
    # SI worked example and Appendix F.2 values (no 1.96 multiplier)
    check(abs(U([ATTENTION, NORMAL, NORMAL]) - 0.0632) < 1e-3, "majority of three: U = sqrt(0.02^2 + 0.06^2) = 0.063 (SI worked example)")
    check(abs(unan3 - 0.0224) < 1e-3, "unanimous three: U = 0.022 (SI worked example)")
    check(abs(single - 0.1005) < 1e-3, "single authority: U = 0.100 (SI F.2)")


def test_parse_censored():
    check(parse_value("<0.01") == (0.01, "<"), "censored TSH kept at endpoint")
    check(parse_value("#tps") is None, "non-numeric rejected")
    check(parse_value("3,5") == (3.5, ""), "decimal comma")


def test_thyroid_rules_and_theorem_1():
    rules = json.loads((HERE / "spec/rules.json").read_text(encoding="utf-8"))["rules"]
    hi = {"label": ATTENTION, "direction": "high"}
    lo = {"label": ATTENTION, "direction": "low"}
    nm = {"label": NORMAL, "direction": "none"}
    r = evaluate(rules, {"TSH": hi, "T4L": lo}); check_non_overlap(r)
    check(r["overt"] == {"Hypothyroidism"} and not r["hidden"], "TSH high + FT4 low -> overt hypothyroidism only")
    r = evaluate(rules, {"TSH": hi, "T4L": nm})
    check(r["hidden"] == {"Subclinical_Hypothyroidism"} and not r["overt"], "TSH high + FT4 normal -> SCH")
    r = evaluate(rules, {"TSH": hi})
    check(r["indeterminate"] == {"Subclinical_Hypothyroidism"} and not r["hidden"], "TSH high, no FT4 -> indeterminate")
    r = evaluate(rules, {"TSH": lo, "T4L": hi})
    check(r["overt"] == {"Hyperthyroidism"} and "Hypothyroidism" not in r["overt"], "low TSH + high FT4 -> hyper only")



def test_rules_d5():
    from cdss.rules import confidence, evidence_count, matches
    rules = {r["id"]: r for r in json.loads((HERE / "spec/rules.json").read_text(encoding="utf-8"))["rules"]}
    check(sum(r["layer"] == "overt" for r in rules.values()) == 9 and sum(r["layer"] == "hidden" for r in rules.values()) == 7, "9 overt and 7 hidden rules")
    for r in rules.values():
        if r["layer"] == "hidden" and r["id"] not in ("H-SCH", "H-SCHYPER"):
            check(r.get("overt_counterparts"), f"{r['id']} lists an overt counterpart")
    C = lambda lab, d: {"label": lab, "direction": d}
    alls = list(rules.values())
    r = evaluate(alls, {"A1F": C(ATTENTION, "high")}); check(r["hidden"] == {"Prediabetes"} and not r["overt"], "HbA1c ATTENTION -> prediabetes")
    r = evaluate(alls, {"A1F": C(ATTENTION, "high"), "GLU": C(CRITICAL, "high")}); check_non_overlap(r)
    check(r["overt"] == {"Diabetes_Mellitus"} and not r["hidden"], "FPG CRITICAL suppresses prediabetes (Theorem 1)")
    cons = {"A1F": C(CRITICAL, "high"), "GLU": C(ATTENTION, "high")}
    check(evidence_count(rules["O-DM"], cons) == 2 and confidence(rules["O-DM"], cons) == 0.80, "eta counts required + supporting once each: 0.70 + 2*0.05")
    r = evaluate(alls, {"K": C(ATTENTION, "high")}); check(not r["overt"] and not r["hidden"], "mild hyperkalaemia: no disease label")
    r = evaluate(alls, {"LDL": C(CRITICAL, "high"), "CHOL": C(ATTENTION, "high")}); check(r["overt"] == {"Dyslipidaemia"} and not r["hidden"], "LDL high -> dyslipidaemia; borderline suppressed")
    check(all(d not in {x["disease"] for x in alls} for d in ("Chronic_Kidney_Disease", "Liver_Disease", "Chronic_Low_Grade_Inflammation")), "suspended rules absent")


def test_reference_intervals_d10():
    ri = {r["analyte"]: r for r in json.loads((HERE / "spec/reference_intervals.json").read_text(encoding="utf-8"))["rows"]}
    spec = json.loads((HERE / "spec/thresholds.json").read_text(encoding="utf-8"))
    voted = {r["analyte"] for r in spec["rows"]}
    check(set(ri) == voted | set(spec["lab_reference_tier"]["use_for_rules"]) and len(ri) == 13, "13 intervals: 11 voted tests + FT4, FT3")
    for r in ri.values():
        validate_row(r)
        check(r.get("source") and r.get("ref"), f"{r['analyte']} interval has a source and a reference number")
        check(r.get("low_critical") is None and r.get("high_critical") is None, f"{r['analyte']} interval has no CRITICAL tier")
    for code, v, want in [("A1F", 5.6, NORMAL), ("A1F", 5.7, ATTENTION), ("GLU", 99, NORMAL), ("GLU", 100, ATTENTION), ("TSH", 4.0, NORMAL), ("TSH", 4.01, ATTENTION),
                          ("TSH", 0.39, ATTENTION), ("T4L", 12.0, NORMAL), ("T4L", 11.9, ATTENTION), ("T4L", 22.1, ATTENTION), ("T3L", 6.8, NORMAL), ("T3L", 6.9, ATTENTION),
                          ("HGB", 12.0, NORMAL), ("HGB", 11.9, ATTENTION), ("HGB", 18.0, NORMAL), ("B12", 199, ATTENTION), ("B12", 2000, NORMAL), ("FOL", 2.9, ATTENTION),
                          ("FOL", 25, NORMAL), ("VD3", 19.9, ATTENTION), ("VD3", 80, NORMAL), ("K", 5.0, NORMAL), ("K", 5.1, ATTENTION), ("K", 3.4, ATTENTION),
                          ("CHOL", 199, NORMAL), ("CHOL", 200, ATTENTION), ("LDL", 100, ATTENTION), ("TRI", 149, NORMAL), ("TRI", 150, ATTENTION)]:
        check(classify(v, ri[code])[0] == want, f"reference interval {code} {v} -> {want}")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("FAIL:\n  " + "\n  ".join(FAILS) if FAILS else "all tests passed")
    sys.exit(1 if FAILS else 0)
