"""Single canonical run: every count, table and figure input for the revised manuscript comes from here.

Usage:
    python run_all.py --csv-dir <neo4j CSV folder> --out <output dir> [--min-age 18] [--max-patient-id N] [--include-pending]

Cohort (decision R2-M1, 2026-10-21): all patients in the export, adults only (recorded age >= 18).

Writes results.json (all numbers) and run_manifest.json (input/spec/code hashes) to --out.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from cdss.classify import ATTENTION, CRITICAL, NORMAL, classify, validate_row
from cdss.consensus import U_PARAMS, agreement, agreement_pattern, consensus_direction, consensus_label, uncertainty_index
from cdss.data import load, load_ages, request_dates
from cdss.rules import check_non_overlap, confidence, evaluate, matches

HERE = Path(__file__).parent

# Configurations: cumulative authority panels (proposal; names follow the revised Methods)
CONFIGS = [   # author decision 2026-10-20: authorities added in four groups (main text Section 3.7)
    ("Config-1", ["NICE"]),
    ("Config-2", ["NICE", "ADA", "WHO"]),
    ("Config-3", ["NICE", "ADA", "WHO", "ETA", "ATA", "BCSH"]),
    ("Config-4", ["NICE", "ADA", "WHO", "ETA", "ATA", "BCSH", "SACN", "ROS", "UKKA", "NCEP"]),
]


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


U_ACTIVE = U_PARAMS   # constants of U(t); replaced only by --u-params (sensitivity analysis, SI S1)


def stage1(values: dict, rows_by_analyte: dict, authorities: list[str], lab_rows: dict):
    """Per-analyte consensus for one patient under one authority panel."""
    cons = {}
    for code, v in values.items():
        rows = [r for r in rows_by_analyte.get(code, []) if r["authority"] in authorities]
        if rows:
            votes = [classify(v, r) for r in rows]
            levels = [lv for lv, _ in votes]
            label = consensus_label(levels)
            k, n = agreement(levels, label)
            cons[code] = {"label": label, "direction": consensus_direction(votes, label), "source": "authority",
                          "k": k, "n": n, "pattern": agreement_pattern(levels), "U": round(uncertainty_index(levels, U_ACTIVE), 4),
                          "votes": {r["authority"]: lv for r, (lv, _) in zip(rows, votes)}}
        elif code in lab_rows:
            lv, d = classify(v, lab_rows[code])
            cons[code] = {"label": lv, "direction": d, "source": "lab_ri"}
    return cons


def kappa(a: list[int], b: list[int]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else round((po - pe) / (1 - pe), 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--max-patient-id", type=int, default=None, help="optional ID cut-off (the submitted analysis used 4000; not used since R2-M1)")
    ap.add_argument("--min-age", type=int, default=18, help="adults only; patients without a recorded age are excluded")
    ap.add_argument("--graph-out", type=Path, default=None, help="also write the Neo4j export of the full panel (CSV + load_graph.cypher)")
    ap.add_argument("--include-pending", action="store_true", help="include rows marked pending-author-decision")
    ap.add_argument("--u-params", type=Path, default=None, help="JSON with alternative constants of U(t) (SI S1); the paper uses the defaults in cdss/consensus.py")
    a = ap.parse_args()
    global U_ACTIVE
    if a.u_params:
        u = json.loads(a.u_params.read_text(encoding="utf-8"))
        U_ACTIVE = {"sigma_source": {1: u["sigma_source"]["1"], 2: u["sigma_source"]["2"], "3+": u["sigma_source"]["3+"]}, "sigma_disagree": dict(u["sigma_disagree"])}

    spec = json.loads((HERE / "spec/thresholds.json").read_text(encoding="utf-8"))
    rules = json.loads((HERE / "spec/rules.json").read_text(encoding="utf-8"))["rules"]
    rows = [r for r in spec["rows"] if a.include_pending or r.get("status") != "pending-author-decision"]
    for r in rows:
        validate_row(r)
    rows_by_analyte = defaultdict(list)
    for r in rows:
        rows_by_analyte[r["analyte"]].append(r)

    values, flow, units = load(a.csv_dir, a.max_patient_id, a.min_age)
    dates = request_dates(a.csv_dir)
    unit_problems = {r["analyte"]: units.get(r["analyte"]) for r in rows
                     if units.get(r["analyte"]) and set(units[r["analyte"]]) != {r["unit"]}}
    if unit_problems:
        raise SystemExit(f"unit mismatch between spec and data: {unit_problems}")
    # Reference intervals (decision D10): one per test, 11 guideline-covered tests + free T4/free T3 (SI Table A.2)
    ri_spec = json.loads((HERE / "spec/reference_intervals.json").read_text(encoding="utf-8"))
    ri_rows = {r["analyte"]: r for r in ri_spec["rows"]}
    for r in ri_rows.values():
        validate_row(r)
    voted = {r["analyte"] for r in rows}
    if set(ri_rows) != voted | set(spec["lab_reference_tier"]["use_for_rules"]):
        raise SystemExit(f"reference intervals must cover exactly the voted tests + {spec['lab_reference_tier']['use_for_rules']}: {sorted(ri_rows)}")
    ri_unit_problems = {c: units.get(c) for c, r in ri_rows.items() if units.get(c) and set(units[c]) != {r["unit"]}}
    if ri_unit_problems:
        raise SystemExit(f"unit mismatch between reference intervals and data: {ri_unit_problems}")
    lab_tier = {c: ri_rows[c] for c in spec["lab_reference_tier"]["use_for_rules"]}

    all_auth = sorted({r["authority"] for r in rows})
    # Analysis set for Figure 1 (R2 M1g): which codes and results enter the analysis
    used = voted | set(lab_tier)
    codes_in_data = sorted({c for v in values.values() for c in v})
    flow["codes_in_cohort_after_dedup"] = len(codes_in_data)
    flow["codes_analysed"] = len(used & set(codes_in_data))
    flow["results_on_analysed_codes"] = sum(1 for v in values.values() for c in v if c in used)
    flow["results_on_voted_codes"] = sum(1 for v in values.values() for c in v if c in voted)
    flow["results_on_other_codes_not_used"] = sum(1 for v in values.values() for c in v if c not in used)
    flow["patients_with_any_voted_result"] = sum(1 for v in values.values() if voted & set(v))
    per_code = {c: sum(1 for v in values.values() if c in v) for c in sorted(used)}
    configs = CONFIGS
    patients = sorted(p for p in values if voted & set(values[p]))   # analysis cohort: >= 1 result on a guideline-covered test
    flow["cohort_results_voted"] = sum(1 for p in patients for c in values[p] if c in voted)
    flow["cohort_results_reference_tier"] = sum(1 for p in patients for c in values[p] if c in lab_tier)
    res: dict = {"flow": dict(flow), "results_per_analysed_code": per_code, "units": units, "request_dates": {"first": dates[0], "last": dates[-1], "n_days_with_requests": len(dates)},
                 "configs": {}, "authorities_in_spec": all_auth}

    per_cfg_patient = {}
    per_cfg_result = {}
    for name, auths in configs:
        cls = Counter(); kn = Counter(); us = Counter(); conf = Counter(); pat_rows = {}; res_lab = {}
        for pid in patients:
            cons = stage1(values[pid], rows_by_analyte, auths, lab_tier)
            for code, c in cons.items():
                if c["source"] == "authority":
                    cls[c["label"]] += 1
                    kn[f'{c["k"]}/{c["n"]}'] += 1
                    us[f'{c["U"]:.3f}'] += 1
                    res_lab[(pid, code)] = c["label"]
            out = evaluate(rules, cons)
            check_non_overlap(out)
            pat_rows[pid] = out
            for r in rules:
                if r["disease"] in out[r["layer"]] and matches(r, cons):
                    conf[(r["layer"], f"{confidence(r, cons):.2f}")] += 1
        per_cfg_patient[name] = pat_rows
        per_cfg_result[name] = res_lab
        disease_counts = Counter(d for o in pat_rows.values() for d in o["overt"])
        hidden_counts = Counter(d for o in pat_rows.values() for d in o["hidden"])
        indet = Counter(d for o in pat_rows.values() for d in o["indeterminate"])
        res["configs"][name] = {
            "authorities": auths,
            "results_covered": sum(cls.values()),
            "class_counts": dict(cls),
            "agreement_kn": dict(kn),
            "uncertainty_index": dict(sorted(us.items())),
            "mean_covering_authorities": round(sum(int(k.split("/")[1]) * v for k, v in kn.items()) / sum(kn.values()), 3) if kn else None,
            "results_with_disagreement": sum(v for k, v in kn.items() if k.split("/")[0] != k.split("/")[1]),
            "results_multi_authority": sum(v for k, v in kn.items() if int(k.split("/")[1]) >= 2),
            "disease_confidence": {lay: {v: n for (l2, v), n in sorted(conf.items()) if l2 == lay} for lay in ("overt", "hidden")},
            "overt_patients": dict(disease_counts),
            "hidden_patients": dict(hidden_counts),
            "indeterminate_patients": dict(indet),
            "any_overt": sum(1 for o in pat_rows.values() if o["overt"]),
            "hidden_only": sum(1 for o in pat_rows.values() if o["hidden"] and not o["overt"]),
        }

    # Stepwise reclassification between consecutive configurations, on results covered by both (R2 M1b)
    names = [n for n, _ in configs]
    steps = {}
    for x, y in zip(names, names[1:]):
        common = set(per_cfg_result[x]) & set(per_cfg_result[y])
        trans = Counter(f"{per_cfg_result[x][k]}->{per_cfg_result[y][k]}" for k in common
                        if per_cfg_result[x][k] != per_cfg_result[y][k])
        by_test = Counter(f"{k[1]}:{per_cfg_result[x][k]}->{per_cfg_result[y][k]}" for k in common
                          if per_cfg_result[x][k] != per_cfg_result[y][k])
        new_by_test = Counter(k[1] for k in set(per_cfg_result[y]) - common)
        steps[f"{x}=>{y}"] = {"common_results": len(common), "newly_covered": len(set(per_cfg_result[y]) - common),
                              "changed": dict(trans), "changed_by_test": dict(by_test), "newly_covered_by_test": dict(new_by_test)}
    res["stepwise_reclassification"] = steps

    # Consistency across configurations (decision R2-M1, 2026-10-21): compare only what both configurations cover.
    # A disease label is compared between two configurations only if every test in its required conditions is covered
    # (voted by an authority, or in the FT4/FT3 reference tier) in both; otherwise it is listed as not compared.
    full = names[-1]
    auth_of = dict(configs)
    def covered(cfg):
        return {r["analyte"] for r in rows if r["authority"] in auth_of[cfg]} | set(lab_tier)
    req = defaultdict(set)
    for r in rules:
        req[(r["layer"], r["disease"])] |= {c["analyte"] for c in r.get("all", []) + r.get("any", [])}
    consistency = {}
    for x, y in list(zip(names, names[1:])) + [(names[0], full)]:
        both = covered(x) & covered(y)
        comp, skip = {}, []
        for (layer, d), tests in sorted(req.items()):
            if not tests <= both:
                skip.append(f"{layer}:{d}"); continue
            ax = [int(d in per_cfg_patient[x][p][layer]) for p in patients]
            ay = [int(d in per_cfg_patient[y][p][layer]) for p in patients]
            comp[f"{layer}:{d}"] = {"kappa": kappa(ax, ay), "n_" + x: sum(ax), "n_" + y: sum(ay), "discordant": sum(i != j for i, j in zip(ax, ay))}
        consistency[f"{x}=>{y}"] = {"compared": comp, "not_compared_coverage": skip}
    res["consistency"] = consistency
    # Patients in the analysis cohort who have the results a rule needs to be evaluated (Table 2 "Tested"):
    # every test in its "all" conditions and at least one test in its "any" conditions
    def testable(r, have):
        return all(c["analyte"] in have for c in r.get("all", [])) and (not r.get("any") or any(c["analyte"] in have for c in r["any"]))
    res["patients_tested_per_label"] = {f"{r['layer']}:{r['disease']}": sum(1 for p in patients if testable(r, set(values[p]))) for r in rules}

    # Baselines (main text Section 3.7, decision D10):
    #   B1 = NICE limits for the tests NICE covers, reference intervals (Table A.2) for the other 7 voted tests and FT4/FT3; both layers
    #   B2 = reference intervals (Table A.2) for all 13 tests, no CRITICAL tier; both layers
    #   B3 = B1, overt layer only
    def mode(auths):
        out = {}
        for pid in patients:
            o = evaluate(rules, stage1(values[pid], rows_by_analyte, auths, ri_rows))
            check_non_overlap(o)
            out[pid] = o
        return out
    def summary(pat):
        return {"overt_patients": dict(Counter(d for o in pat.values() for d in o["overt"])),
                "hidden_patients": dict(Counter(d for o in pat.values() for d in o["hidden"])),
                "indeterminate_patients": dict(Counter(d for o in pat.values() for d in o["indeterminate"])),
                "any_overt": sum(1 for o in pat.values() if o["overt"]),
                "hidden_only": sum(1 for o in pat.values() if o["hidden"] and not o["overt"])}
    b1_pat, b2_pat = mode(["NICE"]), mode([])
    res["baseline_modes"] = {"B1": summary(b1_pat), "B2": summary(b2_pat),
                             "B3": {"overt_patients": summary(b1_pat)["overt_patients"], "any_overt": summary(b1_pat)["any_overt"]}}
    b = {"B1_NICE_both_layers": 0, "B2_ri_any_flag": 0, "B3_NICE_overt_only": 0, "B4_any_threshold_flag": 0}
    full_hidden_only = {p for p, o in per_cfg_patient[full].items() if o["hidden"] and not o["overt"]}
    b4_flagged = set()
    for pid in patients:
        c1 = b1_pat[pid]
        b["B1_NICE_both_layers"] += bool(c1["overt"] or c1["hidden"])
        b["B3_NICE_overt_only"] += bool(c1["overt"])
        if any(classify(v, ri_rows[c])[0] != NORMAL for c, v in values[pid].items() if c in ri_rows):
            b["B2_ri_any_flag"] += 1
        if any(classify(v, r)[0] != NORMAL for c, v in values[pid].items() for r in rows_by_analyte.get(c, [])):
            b4_flagged.add(pid)
    b["B4_any_threshold_flag"] = len(b4_flagged)
    res["baselines"] = b
    # Patients with a hidden label under Full and no overt label under B3 (the submitted "structurally invisible" count, Table 3)
    b3_none_full_hidden = {p for p in patients if not b1_pat[p]["overt"] and per_cfg_patient[full][p]["hidden"]}
    res["B3_none_full_hidden"] = {"patients": len(b3_none_full_hidden), "also_flagged_by_B4": len(b3_none_full_hidden & b4_flagged),
                                  "also_any_label_B1": sum(1 for p in b3_none_full_hidden if b1_pat[p]["overt"] or b1_pat[p]["hidden"]),
                                  "analysis_cohort": len(patients)}
    # Table 3: mutually exclusive patient categories, B3 (NICE, overt layer) vs Full (both layers)
    t3 = Counter()
    for p in patients:
        b3o, fo, fh = bool(b1_pat[p]["overt"]), bool(per_cfg_patient[full][p]["overt"]), bool(per_cfg_patient[full][p]["hidden"])
        t3["B3_overt__Full_overt" if b3o and fo else "B3_overt__Full_no_overt" if b3o else
           "B3_none__Full_overt" if fo else "B3_none__Full_hidden_only" if fh else "B3_none__Full_none"] += 1
    res["table3"] = dict(t3)
    # Age of the analysis cohort (WHO 2024 haemoglobin cut-offs are stated for 15-65 years)
    ages = load_ages(a.csv_dir)
    coh_ages = [ages[p] for p in patients if p in ages]
    res["cohort_age"] = {"n": len(coh_ages), "min": min(coh_ages), "max": max(coh_ages),
                         "median": sorted(coh_ages)[len(coh_ages) // 2], "over_65": sum(x > 65 for x in coh_ages),
                         "hgb_results_over_65": sum(1 for p in patients if "HGB" in values[p] and ages.get(p, 0) > 65),
                         "anaemia_full_over_65": sum(1 for p in patients if "Anaemia" in per_cfg_patient[full][p]["overt"] and ages.get(p, 0) > 65)}
    res["B4_vs_full_hidden_only"] = {"full_hidden_only": len(full_hidden_only),
                                     "also_flagged_by_B4": len(full_hidden_only & b4_flagged)}
    res["theorem1_checked_patients"] = len(patients) * len(configs)

    if a.graph_out:
        from cdss.graph_export import export
        authorities = json.loads((HERE / "spec/authorities.json").read_text(encoding="utf-8"))["authorities"]
        cons_full = {pid: stage1(values[pid], rows_by_analyte, auth_of[full], lab_tier) for pid in patients}
        gstats = export(a.graph_out, patients, values, units, cons_full, per_cfg_patient[full], rules, rows_by_analyte, authorities, ri_rows, ages)
        (a.graph_out / "graph_manifest.json").write_bytes(json.dumps({"counts": gstats, "files": {f.name: sha_file(f) for f in sorted(a.graph_out.glob("*")) if f.name != "graph_manifest.json"}}, indent=1).encode("utf-8"))   # LF only

    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "results.json").write_bytes(json.dumps(res, indent=1, ensure_ascii=False, sort_keys=True).encode("utf-8"))   # sorted keys, LF only: byte-identical across runs and platforms
    manifest = {
        "inputs": {f: sha_file(a.csv_dir / f) for f in ("Result_with_uid.csv", "Patient.csv", "Test_Request_with_uid.csv")},
        "spec": {f: sha_file(HERE / "spec" / f) for f in ("thresholds.json", "rules.json", "reference_intervals.json", "authorities.json")},
        "code": {p.relative_to(HERE).as_posix(): sha_file(p) for p in sorted(HERE.glob("**/*.py"), key=lambda q: q.relative_to(HERE).as_posix()) if "tests" not in p.parts},   # "/" on every platform
        "args": {"max_patient_id": a.max_patient_id, "min_age": a.min_age, "include_pending": a.include_pending, "u_params": str(a.u_params) if a.u_params else None},
        "results_sha256": sha_file(a.out / "results.json"),
    }
    (a.out / "run_manifest.json").write_bytes(json.dumps(manifest, indent=1).encode("utf-8"))   # LF only
    print(json.dumps({k: res[k] for k in ("baselines", "baseline_modes", "B4_vs_full_hidden_only")}, indent=1))


if __name__ == "__main__":
    main()
