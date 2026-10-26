"""Load the raw Synlab CSV export into one value per (patient, assay code).

Every exclusion is counted so the selection flow (Figure 1, R2 comment M1g) can be reported exactly.
"""
from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

NUM = re.compile(r"^\s*([<>]=?)?\s*(\d+(?:[.,]\d+)?)\s*$")


def parse_value(raw: str):
    """Return (value, censor) where censor is '<', '>' or ''; None if not numeric.

    Censored strings such as '<0.01' are kept at their endpoint (the manuscript's stated rule);
    the submitted pipeline dropped them, which removed 25 suppressed-TSH results.
    """
    m = NUM.match(raw or "")
    if not m:
        return None
    return float(m.group(2).replace(",", ".")), (m.group(1) or "")[:1]


def load_ages(csv_dir: Path) -> dict[int, int]:
    """Age in years from Patient.csv (column AGE); patients without a numeric age are absent."""
    out = {}
    for r in csv.DictReader(open(csv_dir / "Patient.csv", encoding="utf-8-sig")):
        pid, age = (r.get("PATIENT_ID") or "").strip(), (r.get("AGE") or "").strip()
        if pid.isdigit() and age.isdigit():
            out[int(pid)] = int(age)
    return out


def request_dates(csv_dir: Path) -> list[str]:
    """Distinct request dates (ISO yyyy-mm-dd) in Test_Request_with_uid.csv."""
    ds = set()
    for r in csv.DictReader(open(csv_dir / "Test_Request_with_uid.csv", encoding="utf-8-sig")):
        p = (r.get("DATE_ISO") or "").strip().split("/")
        if len(p) == 3 and all(x.isdigit() for x in p):
            ds.add(f"{int(p[0]):04d}-{int(p[1]):02d}-{int(p[2]):02d}")
    return sorted(ds)


def load(csv_dir: Path, max_patient_id: int | None, min_age: int | None = None):
    """One value per (patient, code). Decision R2-M1 (2026-10-21): all patients (no ID cut-off); adults only
    (age >= min_age and age recorded). Every excluded row is counted in `flow`."""
    flow = Counter()
    rows = list(csv.DictReader(open(csv_dir / "Result_with_uid.csv", encoding="utf-8-sig")))
    flow["raw_rows"] = len(rows)
    ages = load_ages(csv_dir) if min_age is not None else {}
    best: dict[tuple[int, str], dict] = {}
    units: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        pid_s = (r.get("Patient_ID") or "").strip()
        if not pid_s.isdigit():
            flow["excluded_malformed_patient_id"] += 1
            continue
        pid = int(pid_s)
        flow["rows_with_valid_patient_id"] += 1; flow.setdefault("_pids_valid", set()).add(int(pid_s))
        if max_patient_id is not None and pid > max_patient_id:
            flow["excluded_outside_cohort"] += 1
            continue
        if min_age is not None:
            if pid not in ages:
                flow["excluded_rows_age_missing"] += 1; flow.setdefault("_pids_age_missing", set()).add(pid)
                continue
            if ages[pid] < min_age:
                flow["excluded_rows_age_under_min"] += 1; flow.setdefault("_pids_age_under_min", set()).add(pid)
                continue
        code = (r.get("CODE_ANALYSE") or "").strip()
        if not code:
            flow["excluded_blank_code"] += 1
            continue
        pv = parse_value(r.get("Result", ""))
        if pv is None:
            flow[f"excluded_non_numeric:{code}"] += 1
            continue
        flow["numeric_results_in_cohort"] += 1
        if pv[1]:
            flow[f"censored_kept_at_endpoint:{code}"] += 1
        units[code][(r.get("Unit") or "").strip()] += 1
        key = (pid, code)
        rid = int(r["Result_ID"])
        if key in best:
            flow["duplicates_replaced_or_dropped"] += 1
            if rid < best[key]["result_id"]:
                continue
        best[key] = {"result_id": rid, "value": pv[0], "censor": pv[1], "unit": (r.get("Unit") or "").strip()}
    values: dict[int, dict[str, float]] = defaultdict(dict)
    for (pid, code), rec in best.items():
        values[pid][code] = rec["value"]
    flow["patient_code_pairs_after_dedup"] = len(best)
    flow["patients_with_any_result"] = len(values)
    flow["patients_with_valid_id"] = len(flow.pop("_pids_valid", set()))
    for k in ("_pids_age_missing", "_pids_age_under_min"):
        if k in flow:
            flow[k[1:].replace("pids", "patients")] = len(flow.pop(k))
    return dict(values), flow, {c: dict(u) for c, u in units.items()}


def load_lab_ri(csv_dir: Path) -> dict[str, dict]:
    """Author-compiled intervals from TestType_thresholds_and_categories.csv. Not used since decision D10 (2026-10-21):
    run_all.py reads spec/reference_intervals.json instead. Kept only so that the pre-D10 snapshot can be reproduced."""
    out = {}
    for r in csv.DictReader(open(csv_dir / "TestType_thresholds_and_categories.csv", encoding="utf-8-sig")):
        lo, hi = r.get("ref_low", "").strip(), r.get("ref_high", "").strip()
        out[r["CODE_ANALYSE"]] = {
            "category": r.get("category"),
            "unit": r.get("unit"),
            "low_attention": float(lo) if lo else None,
            "high_attention": float(hi) if hi else None,
            "low_op": "lt",
            "high_op": "gt",
        }
    return out
