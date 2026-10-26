"""Supporting Information S1: sensitivity of the uncertainty index U(t) to its constants (decision R2-S1, 2026-10-23).
For each of 14 alternative constant sets (each of the six constants x0.5 and x1.5 in turn; all constants x0.5 and x2) the
full pipeline is re-run with --u-params. Reports, per set: whether every output other than U(t) is identical to the default
run; the U(t) of each voting situation; the orderings of SI S5 Appendix F.2; Kendall's tau-b between default and alternative
U(t) over all classified results of Config-4; mean U(t).
Usage: python analysis/s1_constants.py --csv-dir <data> --baseline <run>/results.json --out <file.json>"""
import argparse, copy, json, math, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(HERE))
from cdss.consensus import U_PARAMS, uncertainty_index

N, A, C = "NORMAL", "ATTENTION", "CRITICAL"
CELLS = [("1", "unanimous", [N]), ("2", "unanimous", [N, N]), ("2", "split_or_tie", [N, A]),
         ("3+", "unanimous", [N, N, N]), ("3+", "majority", [N, N, A]), ("3+", "split_or_tie", [N, A, C])]
KEYS = [("sigma_source", "1"), ("sigma_source", "2"), ("sigma_source", "3+"),
        ("sigma_disagree", "unanimous"), ("sigma_disagree", "majority"), ("sigma_disagree", "split_or_tie")]


def as_json(p):
    return {"sigma_source": {"1": p["sigma_source"][1], "2": p["sigma_source"][2], "3+": p["sigma_source"]["3+"]}, "sigma_disagree": dict(p["sigma_disagree"])}


def from_json(u):
    return {"sigma_source": {1: u["sigma_source"]["1"], 2: u["sigma_source"]["2"], "3+": u["sigma_source"]["3+"]}, "sigma_disagree": dict(u["sigma_disagree"])}


def sets():
    base = as_json(U_PARAMS); out = []
    for grp, key in KEYS:
        for f in (0.5, 1.5):
            u = copy.deepcopy(base); u[grp][key] = round(u[grp][key] * f, 6)
            out.append((f"{grp}[{key}] x{f}", u))
    for f in (0.5, 2):
        u = copy.deepcopy(base)
        for grp, key in KEYS: u[grp][key] = round(u[grp][key] * f, 6)
        out.append((f"all x{f}", u))
    return out


def cell_u(u):
    p = from_json(u)
    return [uncertainty_index(lv, p) for _, _, lv in CELLS]


def orderings(v):
    """SI S5 Appendix F.2. v = U of the six cells in CELLS order."""
    u1, u2, t2, u3, m3, s3 = v
    return {"O1 fewer authorities, larger U (unanimous: 1 > 2 > 3+)": u1 > u2 > u3,
            "O2 disagreement larger than lack of corroboration (tie or split > single authority, for 2 and 3+)": t2 > u1 and s3 > u1,
            "O3 majority with dissent among 3+ smaller than single authority": m3 < u1,
            "O4 more disagreement, larger U (unanimous < majority < split, for 3+; unanimous < tie, for 2)": u3 < m3 < s3 and u2 < t2}


def tau_b(w, x, y):
    """Kendall tau-b over results; w = number of results in each cell, x/y = default/alternative U of each cell."""
    nc = nd = tx = ty = 0
    for i in range(len(w)):
        for j in range(i + 1, len(w)):
            pairs = w[i] * w[j]
            dx, dy = (x[i] > x[j]) - (x[i] < x[j]), (y[i] > y[j]) - (y[i] < y[j])
            if dx == 0 and dy == 0: continue
            if dx == 0: tx += pairs
            elif dy == 0: ty += pairs
            elif dx == dy: nc += pairs
            else: nd += pairs
    return (nc - nd) / math.sqrt((nc + nd + tx) * (nc + nd + ty))


def strip_u(res):
    r = copy.deepcopy(res)
    for c in r["configs"].values(): c.pop("uncertainty_index", None)
    return r


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--csv-dir", required=True, type=Path); ap.add_argument("--baseline", required=True, type=Path); ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    base_res = json.loads(a.baseline.read_text(encoding="utf-8")); base_u = cell_u(as_json(U_PARAMS))
    assert len({f"{round(x, 4):.3f}" for x in base_u}) == len(base_u), "default U values of the cells must be distinct"
    lookup = {f"{round(x, 4):.3f}": i for i, x in enumerate(base_u)}   # same rounding as run_all.py
    counts = {cfg: [0] * len(CELLS) for cfg in base_res["configs"]}
    for cfg, c in base_res["configs"].items():
        for val, n in c["uncertainty_index"].items(): counts[cfg][lookup[val]] += n
    w4 = counts["Config-4"]; tot = sum(w4)
    rows = []
    for name, u in [("default", as_json(U_PARAMS))] + sets():
        v = cell_u(u)
        with tempfile.TemporaryDirectory() as td:
            pf = Path(td) / "u.json"; pf.write_text(json.dumps(u), encoding="utf-8")
            subprocess.run([sys.executable, str(HERE / "run_all.py"), "--csv-dir", str(a.csv_dir), "--out", td, "--u-params", str(pf)], check=True, capture_output=True)
            res = json.loads((Path(td) / "results.json").read_text(encoding="utf-8"))
        same = strip_u(res) == strip_u(base_res)
        hist_model = {}
        for i, n in enumerate(w4):
            if n: k = f"{round(v[i], 4):.3f}"; hist_model[k] = hist_model.get(k, 0) + n
        hist_ok = hist_model == res["configs"]["Config-4"]["uncertainty_index"]
        rows.append({"set": name, "constants": u, "cell_U": [round(x, 6) for x in v], "orderings": orderings(v),
                     "kendall_tau_b": round(tau_b(w4, base_u, v), 6), "mean_U": round(sum(n * x for n, x in zip(w4, v)) / tot, 6),
                     "other_outputs_identical": same, "cell_model_reproduces_run": hist_ok})
    out = {"cells": [{"n": n, "pattern": p} for n, p, _ in CELLS], "results_per_cell": counts, "default_cell_U": [round(x, 6) for x in base_u], "sets": rows}
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_bytes(json.dumps(out, indent=1, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    print(json.dumps([(r["set"], r["kendall_tau_b"], r["other_outputs_identical"], r["cell_model_reproduces_run"], [k[:2] for k, ok in r["orderings"].items() if not ok]) for r in rows], indent=0))


if __name__ == "__main__":
    main()
