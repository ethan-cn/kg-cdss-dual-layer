"""Figures 1-5 of the revised manuscript, drawn only from results.json of the canonical run, its graph export and the spec files.
Usage: python figures/make_figures.py <results.json> <out dir>      (writes FigureN.png at 300 dpi and FigureN.pdf)
Colours: NORMAL / ATTENTION / CRITICAL use the green / amber / red of Figure 2 (status colours, always with a text label).
No number is typed in by hand: every count printed in a figure is read from results.json."""
from __future__ import annotations
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parents[1]
R = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
SPEC = json.loads((HERE / "spec/thresholds.json").read_text(encoding="utf-8")); RULES = json.loads((HERE / "spec/rules.json").read_text(encoding="utf-8"))["rules"]
GREEN, AMBER, RED = "#3B8A4F", "#E3A21A", "#C8402F"
INK, INK2, GRID, SURF = "#1F2328", "#57606A", "#D8DEE4", "#FFFFFF"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": SURF, "axes.facecolor": SURF})
CFG = list(R["configs"]); C = R["configs"]
CFGLBL = {"Config-1": "Config-1\nNICE", "Config-2": "Config-2\n+ ADA, WHO", "Config-3": "Config-3\n+ ETA, ATA, BCSH", "Config-4": "Config-4\n+ SACN, ROS,\nUKKA, NCEP"}
SHORT = {n: n for n in CFGLBL}
fmt = lambda v: f"{v:,}"
def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=300, bbox_inches="tight"); fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight"); plt.close(fig)

# ---------- Figure 1: (A) pipeline, (B) data flow ----------
def box(ax, x, y, w, h, text, fc="#F6F8FA", ec=INK2, bold=False, size=8.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.015", fc=fc, ec=ec, lw=1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, color=INK, fontweight="bold" if bold else "normal", wrap=True)
def arrow(ax, x0, y0, x1, y1):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1))
fig = plt.figure(figsize=(7.2, 8.4))
axA = fig.add_axes([0, 0.62, 1, 0.38]); axA.set_axis_off(); axA.set_xlim(-0.02, 1.02); axA.set_ylim(0, 1.02)
axA.text(0, 0.97, "A", fontsize=12, fontweight="bold", color=INK, va="top")
auths = ", ".join(a for a in ["NICE", "ADA", "WHO", "ETA", "ATA", "BCSH", "SACN", "ROS", "UKKA", "NCEP"])
box(axA, 0.00, 0.35, 0.15, 0.30, "Patient\nlaboratory\nresults\n(test, value)", bold=False, size=8)
box(axA, 0.19, 0.08, 0.34, 0.80, "", fc="#EEF4FB", ec="#4A6FA5")
axA.text(0.36, 0.80, "Stage 1 · consensus (§3.2)", ha="center", fontsize=8.5, fontweight="bold", color=INK)
axA.text(0.36, 0.63, f"Each covering authority votes\nNORMAL / ATTENTION / CRITICAL\n(10 authorities: {', '.join(['NICE','ADA','WHO','ETA','ATA'])},\n{', '.join(['BCSH','SACN','ROS','UKKA','NCEP'])})", ha="center", va="center", fontsize=7.2, color=INK)
axA.text(0.36, 0.38, "Conservative escalation rule (Definition 1)\n→ consensus class c(t)\n+ agreement count k/n\n+ uncertainty index U(t) (Definition 2)", ha="center", va="center", fontsize=7.2, color=INK)
for i, (lbl, col) in enumerate([("NORMAL", GREEN), ("ATTENTION", AMBER), ("CRITICAL", RED)]):
    axA.add_patch(plt.Rectangle((0.22 + i * 0.105, 0.14), 0.02, 0.05, fc=col, ec="none")); axA.text(0.245 + i * 0.105, 0.165, lbl, fontsize=6.8, va="center", color=INK)
box(axA, 0.57, 0.08, 0.27, 0.80, "", fc="#FBF1EF", ec="#A5524A")
nO = sum(r["layer"] == "overt" for r in RULES); nH = sum(r["layer"] == "hidden" for r in RULES)
axA.text(0.705, 0.80, "Stage 2 · inference (§3.3)", ha="center", fontsize=8.5, fontweight="bold", color=INK)
box(axA, 0.59, 0.50, 0.105, 0.25, f"Overt layer\n{nO} rules\nCRITICAL-\nanchored", fc="#F7DCD8", ec=RED, size=7.3)
box(axA, 0.725, 0.50, 0.105, 0.25, f"Hidden layer\n{nH} rules\nATTENTION-\nanchored", fc="#FBEBC8", ec=AMBER, size=7.3)
box(axA, 0.59, 0.14, 0.24, 0.28, "Exclusion clause (Theorem 1):\nif the overt counterpart fires,\nthe hidden rule is suppressed;\nno label in both layers", fc=SURF, ec=INK2, size=7.2)
box(axA, 0.875, 0.30, 0.125, 0.40, "Disease-risk\nnodes\n(overt and\nhidden)\nwith provenance\nto guideline\nDOI or\nweb address", fc="#EEF6EF", ec=GREEN, size=6.8)
arrow(axA, 0.15, 0.50, 0.19, 0.50); arrow(axA, 0.53, 0.50, 0.57, 0.50); arrow(axA, 0.84, 0.50, 0.88, 0.50)
# (B) flow
f = R["flow"]; nn = sum(v for k, v in f.items() if k.startswith("excluded_non_numeric")); cens = sum(v for k, v in f.items() if k.startswith("censored"))
axB = fig.add_axes([0, 0, 1, 0.60]); axB.set_axis_off(); axB.set_xlim(0, 1); axB.set_ylim(0, 1)
axB.text(0, 0.99, "B", fontsize=12, fontweight="bold", color=INK, va="top")
main = [f"Export: {fmt(f['raw_rows'])} result rows",
        f"{fmt(f['rows_with_valid_patient_id'])} rows with a valid patient identifier\n{fmt(f['patients_with_valid_id'])} patients",
        f"{fmt(f['numeric_results_in_cohort'])} numeric results of adults with a recorded age\n({cens} censored values kept at their endpoint)",
        f"{fmt(f['patient_code_pairs_after_dedup'])} results (one per patient and test)\n{f['codes_in_cohort_after_dedup']} test codes · {fmt(f['patients_with_any_result'])} patients",
        f"Analysis cohort: {fmt(f['patients_with_any_voted_result'])} patients\n{fmt(f['cohort_results_voted'])} results on the {len({r['analyte'] for r in SPEC['rows']})} guideline-covered tests\n+ {fmt(f['cohort_results_reference_tier'])} free T4 / free T3 results (thyroid rules)"]
side = [f"Excluded: {fmt(f['excluded_malformed_patient_id'])} rows without a valid patient identifier",
        f"Excluded: {fmt(f['patients_age_missing'])} patients without a recorded age ({fmt(f['excluded_rows_age_missing'])} rows);\n{fmt(f['patients_age_under_min'])} patients aged under 18 ({fmt(f['excluded_rows_age_under_min'])} rows);\n{fmt(f['excluded_blank_code'])} rows without a test code; {fmt(nn)} non-numeric results",
        f"Excluded: {fmt(f['duplicates_replaced_or_dropped'])} earlier duplicates (most recent result kept)",
        f"Not used: {fmt(f['results_on_other_codes_not_used'])} results on {f['codes_in_cohort_after_dedup'] - f['codes_analysed']} codes without a guideline\ndecision limit (e.g. creatinine, liver enzymes, CRP);\npatients with no guideline-covered result"]
ys = [0.88, 0.70, 0.50, 0.30, 0.08]; hs = [0.07, 0.09, 0.09, 0.09, 0.13]
for y, h, t in zip(ys, hs, main): box(axB, 0.04, y, 0.46, h, t, fc="#F6F8FA", size=7.6)
for k in range(4):
    arrow(axB, 0.27, ys[k], 0.27, ys[k + 1] + hs[k + 1])
    ymid = (ys[k] + ys[k + 1] + hs[k + 1]) / 2; arrow(axB, 0.27, ymid, 0.54, ymid)
    box(axB, 0.54, ymid - 0.055, 0.45, 0.11, side[k], fc=SURF, ec=GRID, size=7)
save(fig, "Figure1")

# ---------- Figure 2: graph schema of the Neo4j export (cdss/graph_export.py) ----------
G = Path(sys.argv[1]).parent / "graph"
gm = json.loads((G / "graph_manifest.json").read_text(encoding="utf-8"))["counts"] if (G / "graph_manifest.json").exists() else None
fig = plt.figure(figsize=(7.2, 4.6)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
def node(x, y, w, h, title, attrs, fc, ec):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.006,rounding_size=0.02", fc=fc, ec=ec, lw=1.2))
    ax.text(x, y + h / 2 - 0.035, title, ha="center", va="top", fontsize=7.8, fontweight="bold", color=INK)
    ax.text(x, y - h / 2 + 0.025, attrs, ha="center", va="bottom", fontsize=6.3, color=INK2, linespacing=1.25)
def edge(x0, y0, x1, y1, lbl, dx=0, dy=0.015, ls="-"):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1, linestyle=ls))
    ax.text((x0 + x1) / 2 + dx, (y0 + y1) / 2 + dy, lbl, ha="center", fontsize=6.3, color=INK, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.15", fc=SURF, ec="none"))
node(0.09, 0.62, 0.15, 0.20, "Patient", "patient_id\nage", "#F6F8FA", INK2)
# test nodes: one node per result, carrying exactly one of three labels; every test-level edge applies to all three
ax.add_patch(FancyBboxPatch((0.295, 0.395), 0.25, 0.555, boxstyle="round,pad=0.006,rounding_size=0.02", fc="none", ec=INK2, lw=0.9, linestyle=(0, (4, 3))))
ax.text(0.42, 0.965, "Test node (one per result; exactly one label)", ha="center", va="center", fontsize=6.6, color=INK, fontweight="bold")
for i, (lbl, col, fc) in enumerate([("NormalTest", GREEN, "#E6F2E9"), ("AttentionTest", AMBER, "#FBF0D5"), ("CriticalTest", RED, "#F7DCD8")]):
    node(0.42, 0.84 - i * 0.165, 0.20, 0.13, lbl, "code · value · unit\nconsensus class · k/n · U(t)", fc, col)
node(0.82, 0.80, 0.27, 0.19, "GuidelineAuthority", "name · guideline documents\n(reference number,\nDOI or web address)", "#EEF4FB", "#4A6FA5")
node(0.82, 0.47, 0.27, 0.15, "ReferenceInterval", "free T4, free T3\ninterval · source · link", "#F3F4F6", INK2)
node(0.25, 0.12, 0.22, 0.15, "OvertDiseaseRisk", "disease · rule · confidence\nη · guideline source", "#F7DCD8", RED)
node(0.62, 0.12, 0.22, 0.15, "HiddenDiseaseRisk", "disease · rule · confidence\nη · guideline source", "#FBF0D5", AMBER)
edge(0.165, 0.67, 0.295, 0.72, "HAS_TEST", dx=-0.005, dy=0.03)
edge(0.545, 0.80, 0.685, 0.80, "VOTED_BY\n{vote, refs, links}", dy=0.025)
edge(0.545, 0.47, 0.685, 0.47, "CLASSIFIED_BY\n(free T4 / free T3)", dy=0.025, ls="--")
edge(0.10, 0.52, 0.20, 0.195, "HAS_DISEASE_RISK", dx=-0.035, dy=0.0)
edge(0.29, 0.195, 0.38, 0.395, "", dx=0, dy=0)
edge(0.58, 0.195, 0.46, 0.395, "", dx=0, dy=0)
ax.text(0.42, 0.29, "BASED_ON_TEST\n(each matched test)", ha="center", va="center", fontsize=6.3, color=INK, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.15", fc=SURF, ec="none"))
ax.text(0.82, 0.285, "Provenance of every disease-risk node:\nrisk → BASED_ON_TEST → test\n→ VOTED_BY {refs, links} → GuidelineAuthority\n(DOI or web address)", ha="center", va="center", fontsize=6.3, color=INK,
        bbox=dict(boxstyle="round,pad=0.4", fc="#FFFFFF", ec=GRID))
save(fig, "Figure2")

# ---------- Figure 3: (A) classes per configuration, (B) agreement ----------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 3.6), gridspec_kw=dict(wspace=0.35))
x = range(len(CFG))
for ax in (a1, a2): ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
bottom = [0] * len(CFG)
for lbl, col in [("NORMAL", GREEN), ("ATTENTION", AMBER), ("CRITICAL", RED)]:
    vals = [C[n]["class_counts"][lbl] for n in CFG]
    a1.bar(x, vals, 0.6, bottom=bottom, color=col, edgecolor=SURF, linewidth=1, label=lbl)
    for i, (v, b) in enumerate(zip(vals, bottom)):
        if v > 900: a1.text(i, b + v / 2, fmt(v), ha="center", va="center", fontsize=6.8, color=INK if lbl == "ATTENTION" else SURF)
    bottom = [b + v for b, v in zip(bottom, vals)]
for i, n in enumerate(CFG): a1.text(i, bottom[i] + 400, fmt(C[n]["results_covered"]), ha="center", fontsize=7, color=INK)
st = R["stepwise_reclassification"]
for i, k in [(1, "Config-1=>Config-2"), (2, "Config-2=>Config-3"), (3, "Config-3=>Config-4")]:
    ch = sum(st[k]["changed"].values()); top = max(sum(C[n]["class_counts"].values()) for n in CFG)
    a1.annotate(f"{ch}\nreclass.", xy=(i - 0.5, top * 1.04), ha="center", va="bottom", fontsize=6.3, color=INK2)
a1.set_xticks(list(x)); a1.set_xticklabels([SHORT[n] for n in CFG], fontsize=7.5)
a1.set_ylabel("Classified results"); a1.set_title("A  Consensus classification", loc="left", fontsize=9, fontweight="bold", color=INK)
a1.legend(frameon=False, fontsize=6.8, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3); a1.set_ylim(0, max(bottom) * 1.22)
cats = [("One covering authority", "#8C959F"), ("≥ 2 authorities, unanimous (k = n)", "#4A6FA5"), ("≥ 2 authorities, disagreement (k < n)", "#B4562B")]
def split(kn):
    one = sum(v for k, v in kn.items() if k.split("/")[1] == "1"); dis = sum(v for k, v in kn.items() if k.split("/")[0] != k.split("/")[1])
    return [one, sum(kn.values()) - one - dis, dis]
parts = [split(C[n]["agreement_kn"]) for n in CFG]; bottom = [0] * len(CFG)
for j, (lbl, col) in enumerate(cats):
    vals = [100 * p[j] / sum(p) for p in parts]
    a2.bar(x, vals, 0.6, bottom=bottom, color=col, edgecolor=SURF, linewidth=1, label=lbl)
    for i, (v, b) in enumerate(zip(vals, bottom)):
        if v >= 6: a2.text(i, b + v / 2, f"{v:.0f}%", ha="center", va="center", fontsize=6.8, color=SURF)
    bottom = [b + v for b, v in zip(bottom, vals)]
for i, n in enumerate(CFG): a2.text(i, 102, f"mean {C[n]['mean_covering_authorities']:.2f}", ha="center", fontsize=6.6, color=INK)
a2.set_xticks(list(x)); a2.set_xticklabels([SHORT[n] for n in CFG], fontsize=7.5); a2.set_ylim(0, 110); a2.set_ylabel("Share of classified results (%)")
a2.set_title("B  Covering authorities and agreement", loc="left", fontsize=9, fontweight="bold", color=INK)
a2.legend(frameon=False, fontsize=6.5, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=1)
save(fig, "Figure3")

# ---------- Figures 4 and 5: label × configuration tables ----------
auth_of = {n: C[n]["authorities"] for n in CFG}
lab = set(SPEC["lab_reference_tier"]["use_for_rules"])
def covered(n): return {r["analyte"] for r in SPEC["rows"] if r["authority"] in auth_of[n]} | lab
def heat(layer, key, title, name, cmap, total_row):
    rules = [r for r in RULES if r["layer"] == layer]
    order = sorted(rules, key=lambda r: -C[CFG[-1]][key].get(r["disease"], 0))
    nm = lambda d: (lambda t: t[0].upper() + t[1:].lower())(d.replace("_", " ")).replace("b12", "B12").replace("Vitamin d", "Vitamin D")
    rows_ = [nm(r["disease"]) for r in order]
    M = []; cov = []
    for r in order:
        req = {c["analyte"] for c in r.get("all", []) + r.get("any", [])}
        cov.append([req <= covered(n) for n in CFG]); M.append([C[n][key].get(r["disease"], 0) for n in CFG])
    if total_row:
        rows_.append("≥ 1 overt label (patients)"); M.append([C[n]["any_overt"] for n in CFG]); cov.append([True] * len(CFG))
    vmax = max(max(m) for m in M[:len(order)]) or 1
    fig, ax = plt.subplots(figsize=(6.4, 0.42 * len(rows_) + 1.3))
    cm = plt.get_cmap(cmap)
    for i, (row, cv) in enumerate(zip(M, cov)):
        for j, (v, c) in enumerate(zip(row, cv)):
            last = total_row and i == len(rows_) - 1
            if not c:
                ax.add_patch(plt.Rectangle((j, i), 1, 1, fc="#F3F4F6", ec=SURF, lw=2, hatch="////", fill=True)); ax.text(j + 0.5, i + 0.5, "not covered", ha="center", va="center", fontsize=6.5, color=INK2)
            else:
                t = 0.15 + 0.75 * (v / vmax if not last else 0.0)
                ax.add_patch(plt.Rectangle((j, i), 1, 1, fc=cm(t) if not last else "#E8EBEF", ec=SURF, lw=2))
                ax.text(j + 0.5, i + 0.5, fmt(v), ha="center", va="center", fontsize=8, color=SURF if t > 0.6 else INK, fontweight="bold" if last else "normal")
    ax.set_xlim(0, len(CFG)); ax.set_ylim(len(rows_), 0)
    ax.set_xticks([j + 0.5 for j in range(len(CFG))]); ax.set_xticklabels([CFGLBL[n] for n in CFG], fontsize=7); ax.xaxis.tick_top()
    ax.set_yticks([i + 0.5 for i in range(len(rows_))]); ax.set_yticklabels(rows_, fontsize=8)
    for s in ax.spines.values(): s.set_visible(False)
    ax.tick_params(length=0)
    save(fig, name)
heat("hidden", "hidden_patients", "Hidden-layer labels (patients) by configuration", "Figure4", "YlOrBr", False)
heat("overt", "overt_patients", "Overt-layer labels (patients) by configuration", "Figure5", "Reds", True)
import hashlib, matplotlib as _m
man = {"results_json": str(Path(sys.argv[1]).name), "results_sha256": hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest(),
       "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "matplotlib": _m.__version__, "dpi": 300,
       "figures": {n: hashlib.sha256((OUT / f"{n}.png").read_bytes()).hexdigest() for n in ("Figure1", "Figure2", "Figure3", "Figure4", "Figure5")},
       "graph_manifest_sha256": hashlib.sha256((G / "graph_manifest.json").read_bytes()).hexdigest() if (G / "graph_manifest.json").exists() else None}
(OUT / "FIGURES_MANIFEST.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
print("figures written to", OUT)
