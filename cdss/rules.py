"""Disease rules as data, with the exclusion specification actually executed.

Condition forms (all evaluated on the per-analyte consensus of the active configuration):
    {"analyte": "TSH", "level": ["ATTENTION", "CRITICAL"], "direction": "high"}
    {"analyte": "T4L", "state": "normal"}        consensus NORMAL
    {"analyte": "T4L", "state": "abnormal", "direction": "low"}
Rule fields:
    id, disease, family (condition family shared by an overt rule and its hidden counterpart),
    layer ("overt" | "hidden"), all (conditions that must hold), any (alternatives: at least one must hold, if given),
    support (conditions that add to the evidence count eta but are not required),
    exclude (conditions any of which suppresses the rule),
    overt_counterparts (overt rule ids whose firing suppresses this hidden rule),
    indeterminate_if_missing (analytes whose absence makes the label 'indeterminate' instead of firing)
"""
from __future__ import annotations

from .classify import NORMAL


def _holds(cond: dict, cons: dict) -> bool:
    a = cons.get(cond["analyte"])
    if a is None:
        return False
    level, direction = a["label"], a["direction"]
    want_dir = cond.get("direction", "any")
    dir_ok = want_dir == "any" or direction == want_dir
    if "state" in cond:
        if cond["state"] == "normal":
            return level == NORMAL
        return level != NORMAL and dir_ok
    return level in cond["level"] and dir_ok


def matches(r: dict, cons: dict) -> bool:
    """Required part of a rule: every 'all' condition holds and, if 'any' is given, at least one of its conditions holds."""
    return all(_holds(c, cons) for c in r.get("all", [])) and (not r.get("any") or any(_holds(c, cons) for c in r["any"]))


def evidence_count(r: dict, cons: dict) -> int:
    """eta(r, P) = |R ∩ A_P| + |S ∩ A_P| (SI Appendix B): matched required conditions plus matched supporting conditions.
    Each analyte is counted once."""
    req = {c["analyte"] for c in r.get("all", []) + r.get("any", []) if _holds(c, cons)}
    sup = {c["analyte"] for c in r.get("support", []) if _holds(c, cons)} - req
    return len(req) + len(sup)


def confidence(r: dict, cons: dict) -> float:
    """SI Eqs. A.4-A.5: overt min(0.70 + 0.05*eta, 0.95); hidden min(0.50 + 0.05*eta, 0.75)."""
    eta = evidence_count(r, cons)
    return round(min(0.70 + 0.05 * eta, 0.95), 2) if r["layer"] == "overt" else round(min(0.50 + 0.05 * eta, 0.75), 2)


def evaluate(rules: list[dict], cons: dict, hidden_layer: bool = True) -> dict:
    """Return {'overt': set, 'hidden': set, 'indeterminate': set} of disease labels for one patient."""
    out = {"overt": set(), "hidden": set(), "indeterminate": set(), "overt_family": set(), "hidden_family": set()}
    fired_overt_ids = set()
    for r in (x for x in rules if x["layer"] == "overt"):
        if matches(r, cons) and not any(_holds(c, cons) for c in r.get("exclude", [])):
            out["overt"].add(r["disease"])
            out["overt_family"].add(r.get("family", r["disease"]))
            fired_overt_ids.add(r["id"])
    if not hidden_layer:
        return out
    for r in (x for x in rules if x["layer"] == "hidden"):
        if not matches(r, cons):
            continue
        if any(_holds(c, cons) for c in r.get("exclude", [])):
            continue
        if fired_overt_ids & set(r.get("overt_counterparts", [])):
            continue
        if any(a not in cons for a in r.get("indeterminate_if_missing", [])):
            out["indeterminate"].add(r["disease"])
            continue
        out["hidden"].add(r["disease"])
        out["hidden_family"].add(r.get("family", r["disease"]))
    return out


def check_non_overlap(result: dict) -> None:
    """Theorem 1 as a runtime assertion on every patient."""
    clash = result["overt_family"] & result["hidden_family"]
    if clash:
        raise AssertionError(f"Theorem 1 violated: {clash}")
