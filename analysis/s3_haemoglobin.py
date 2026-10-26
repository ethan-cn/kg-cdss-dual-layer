"""Supporting Information S3: sensitivity to the sex- and age-specific haemoglobin limits (decision R2-S3, 2026-10-23).
WHO 2024 sets the anaemia cut-off at haemoglobin < 12.0 g/dL for non-pregnant women and < 13.0 g/dL for men (ages 15-65);
the dataset has no sex field, so the paper applies 12.0 g/dL to all results (lower bound). This script re-runs the full
pipeline with 13.0 g/dL for all results (upper bound) on a temporary copy of the code and spec in which only that one limit
is changed, and reports both runs overall and by age group (18-65, >65) from their graph exports.
Usage: python analysis/s3_haemoglobin.py --csv-dir <data> --baseline-run <run dir with results.json and graph/> --out <file.json>"""
import argparse, csv, json, shutil, subprocess, sys, tempfile
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
UPPER = 13.0


def patient_view(graph: Path):
    rd = lambda f: list(csv.DictReader(open(graph / f, encoding="utf-8", newline="")))
    age = {p["patient_id"]: int(p["age"]) for p in rd("patients.csv")}
    hb = {t["patient_id"]: float(t["value"]) for t in rd("tests.csv") if t["code"] == "HGB"}
    overt = defaultdict(set); hidden = defaultdict(set)
    for d in rd("disease_risks.csv"):
        (overt if d["layer"] == "overt" else hidden)[d["risk_uid"].split(":")[0]].add(d["disease"])
    return age, hb, overt, hidden


def summarise(graph: Path):
    age, hb, overt, hidden = patient_view(graph)
    groups = {"all": lambda a: True, "18-65": lambda a: a <= 65, ">65": lambda a: a > 65}
    out = {}
    for g, keep in groups.items():
        ps = [p for p in age if keep(age[p])]
        out[g] = {"patients": len(ps), "haemoglobin_tested": sum(1 for p in ps if p in hb),
                  "anaemia_overt": sum(1 for p in ps if "Anaemia" in overt[p]),
                  "any_overt": sum(1 for p in ps if overt[p]),
                  "overt_by_disease": {d: sum(1 for p in ps if d in overt[p]) for d in sorted({x for s in overt.values() for x in s})},
                  "hidden_by_disease": {d: sum(1 for p in ps if d in hidden[p]) for d in sorted({x for s in hidden.values() for x in s})}}
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--csv-dir", required=True, type=Path); ap.add_argument("--baseline-run", required=True, type=Path); ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as td:
        code = Path(td) / "code"; shutil.copytree(HERE / "cdss", code / "cdss"); shutil.copytree(HERE / "spec", code / "spec"); shutil.copy(HERE / "run_all.py", code / "run_all.py")
        spec = json.loads((code / "spec/thresholds.json").read_text(encoding="utf-8")); rows = spec["rows"] if "rows" in spec else spec
        hgb = [r for r in rows if r.get("analyte") == "HGB"]
        assert len(hgb) == 1 and hgb[0]["low_critical"] == 12.0 and hgb[0]["authority"] == "WHO", "expected one WHO haemoglobin row with limit 12.0"
        hgb[0]["low_critical"] = UPPER
        (code / "spec/thresholds.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False), encoding="utf-8")
        out = Path(td) / "run"
        subprocess.run([sys.executable, str(code / "run_all.py"), "--csv-dir", str(a.csv_dir), "--out", str(out), "--graph-out", str(out / "graph")], check=True, capture_output=True)
        upper_res = json.loads((out / "results.json").read_text(encoding="utf-8")); upper = summarise(out / "graph")
    base_res = json.loads((a.baseline_run / "results.json").read_text(encoding="utf-8")); lower = summarise(a.baseline_run / "graph")
    c_lo, c_up = base_res["configs"]["Config-4"], upper_res["configs"]["Config-4"]
    changed_overt = sorted(d for d in set(c_lo["overt_patients"]) | set(c_up["overt_patients"]) if c_lo["overt_patients"].get(d) != c_up["overt_patients"].get(d))
    changed_hidden = sorted(d for d in set(c_lo["hidden_patients"]) | set(c_up["hidden_patients"]) if c_lo["hidden_patients"].get(d) != c_up["hidden_patients"].get(d))
    res = {"limit_lower_g_dL": 12.0, "limit_upper_g_dL": UPPER, "lower": lower, "upper": upper,
           "config4_overt_changed": changed_overt, "config4_hidden_changed": changed_hidden,
           "config4_any_overt": {"lower": c_lo["any_overt"], "upper": c_up["any_overt"]},
           "config4_anaemia": {"lower": c_lo["overt_patients"].get("Anaemia"), "upper": c_up["overt_patients"].get("Anaemia")},
           "table3": {"lower": base_res["table3"], "upper": upper_res["table3"]},
           "graph_matches_results": {"lower": lower["all"]["anaemia_overt"] == c_lo["overt_patients"].get("Anaemia") and lower["all"]["any_overt"] == c_lo["any_overt"],
                                     "upper": upper["all"]["anaemia_overt"] == c_up["overt_patients"].get("Anaemia") and upper["all"]["any_overt"] == c_up["any_overt"]},
           "theorem1_checked_patients": {"lower": base_res.get("theorem1_checked_patients"), "upper": upper_res.get("theorem1_checked_patients")}}
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_bytes(json.dumps(res, indent=1, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    print(json.dumps({k: res[k] for k in ("config4_overt_changed", "config4_hidden_changed", "config4_any_overt", "config4_anaemia", "graph_matches_results")}, indent=1))
    for side in ("lower", "upper"):
        print(side, {g: {k: v for k, v in d.items() if not k.endswith("disease")} for g, d in res[side].items()})


if __name__ == "__main__":
    main()
