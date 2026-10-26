"""Supporting Information S4: proportion of tested patients with each disease-risk label, overall and by age group
(decision R2-S4, 2026-10-23: descriptive only, no comparison with population prevalence). Reads the graph export and
results.json of the canonical run; 'tested' is defined as in run_all.py (Table 2: patients with the results the rule needs).
Usage: python analysis/s4_descriptive.py --run <run dir with results.json and graph/> --out <file.json>"""
import argparse, csv, json, sys
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]


def testable(r, have):   # same as run_all.py
    return all(c["analyte"] in have for c in r.get("all", [])) and (not r.get("any") or any(c["analyte"] in have for c in r["any"]))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--run", required=True, type=Path); ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(); G = a.run / "graph"
    rd = lambda f: list(csv.DictReader(open(G / f, encoding="utf-8", newline="")))
    R = json.loads((a.run / "results.json").read_text(encoding="utf-8")); rules = json.loads((HERE / "spec/rules.json").read_text(encoding="utf-8"))["rules"]
    age = {p["patient_id"]: int(p["age"]) for p in rd("patients.csv")}
    have = defaultdict(set)
    for t in rd("tests.csv"): have[t["patient_id"]].add(t["code"])
    lab = defaultdict(set)
    for d in rd("disease_risks.csv"): lab[d["risk_uid"].split(":")[0]].add((d["layer"], d["disease"]))
    groups = {"all": lambda x: True, "18-65": lambda x: x <= 65, ">65": lambda x: x > 65}
    rows = []
    for r in rules:
        key = (r["layer"], r["disease"]); row = {"rule": r["id"], "layer": r["layer"], "disease": r["disease"]}
        for g, keep in groups.items():
            ps = [p for p in age if keep(age[p])]
            row[g] = {"tested": sum(1 for p in ps if testable(r, have[p])), "labelled": sum(1 for p in ps if key in lab[p])}
        rows.append(row)
    summary = {}
    for g, keep in groups.items():
        ps = [p for p in age if keep(age[p])]
        summary[g] = {"patients": len(ps), "any_overt": sum(1 for p in ps if any(l == "overt" for l, _ in lab[p])),
                      "any_hidden": sum(1 for p in ps if any(l == "hidden" for l, _ in lab[p])), "any_label": sum(1 for p in ps if lab[p])}
    c4 = R["configs"]["Config-4"]
    checks = {"tested = results.json patients_tested_per_label": all(row["all"]["tested"] == R["patients_tested_per_label"][f"{row['layer']}:{row['disease']}"] for row in rows),
              "labelled = Config-4": all(row["all"]["labelled"] == (c4["overt_patients"] if row["layer"] == "overt" else c4["hidden_patients"]).get(row["disease"], 0) for row in rows),
              "any overt = Config-4": summary["all"]["any_overt"] == c4["any_overt"],
              "age groups add up": all(row["18-65"][k] + row[">65"][k] == row["all"][k] for row in rows for k in ("tested", "labelled"))}
    out = {"rows": rows, "summary": summary, "indeterminate_all_ages": c4.get("indeterminate_patients", {}), "checks": checks}
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_bytes(json.dumps(out, indent=1, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    print(json.dumps(checks)); print(json.dumps(summary))
    for row in rows: print(row["rule"], row["all"], row["18-65"], row[">65"])
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
