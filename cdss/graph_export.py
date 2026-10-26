"""Neo4j export of the full-panel run (decision R2-M1, 2026-10-22): the graph is written from the same run that produces
results.json, so every node and edge can be checked against it. Output: CSV files for LOAD CSV plus load_graph.cypher.

Node labels (8): Patient; NormalTest, AttentionTest, CriticalTest (one node per patient and test, label = consensus class);
GuidelineAuthority (name, guideline documents with reference number and DOI or web address); ReferenceInterval (free T4,
free T3: interval, source, link); OvertDiseaseRisk, HiddenDiseaseRisk (disease, rule, confidence, eta, guideline source).
Relationship types (5): HAS_TEST (Patient -> test), VOTED_BY (test -> GuidelineAuthority, {vote, refs, links, limit_source}: the guideline document(s) of SI Table A.1 and their DOI or web address),
CLASSIFIED_BY (test -> ReferenceInterval, for free T4 / free T3, which no authority votes on), HAS_DISEASE_RISK
(Patient -> disease-risk node), BASED_ON_TEST (disease-risk node -> each matched test).
"""
from __future__ import annotations
import csv, json
from pathlib import Path
from .classify import classify
from .rules import _holds, confidence, evidence_count, matches

LABEL = {"NORMAL": "NormalTest", "ATTENTION": "AttentionTest", "CRITICAL": "CriticalTest"}


def _w(path: Path, header: list[str], rows: list[list]):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(header); w.writerows(rows)


def export(out: Path, patients, values, units, cons_of, out_of, rules, rows_by_analyte, authorities, ri_rows, ages):
    out.mkdir(parents=True, exist_ok=True)
    DOC = {x["ref"]: x["link"] for d in authorities.values() for x in d["documents"]}   # reference number -> DOI or web address
    pat, tests, voted, classified, risks, has_risk, based, auth, ri = [], [], [], [], [], [], [], [], []
    for a, d in sorted(authorities.items()):
        auth.append([a, d["name"], json.dumps(d["documents"], ensure_ascii=False)])
    for code, r in sorted(ri_rows.items()):
        if code in ("T4L", "T3L"):
            ri.append([code, r["unit"], r.get("low_attention", ""), r.get("high_attention", ""), r["source"], r["ref"]])
    for p in patients:
        cons, o = cons_of[p], out_of[p]
        pat.append([p, ages.get(p, "")])
        for code, c in sorted(cons.items()):
            uid = f"{p}:{code}"; unit = next(iter(units.get(code, {"": 0})))
            tests.append([uid, p, code, values[p][code], unit, c["label"], c["direction"], c.get("k", ""), c.get("n", ""), c.get("U", ""), c["source"]])
            if c["source"] == "authority":
                for r in rows_by_analyte[code]:
                    if r["authority"] in c["votes"]:
                        A = authorities[r["authority"]]; refs = A["refs_by_analyte"][code]
                        links = [DOC[x] for x in refs]
                        voted.append([uid, r["authority"], c["votes"][r["authority"]], "|".join(map(str, refs)), "|".join(links), r.get("source", "")])
            else:
                classified.append([uid, code])
        for r in rules:
            if r["disease"] in o[r["layer"]] and matches(r, cons):
                rid = f"{p}:{r['id']}"
                m = sorted({x["analyte"] for x in r.get("all", []) + r.get("any", []) + r.get("support", []) if _holds(x, cons)})
                risks.append([rid, r["layer"], r["disease"], r["id"], confidence(r, cons), evidence_count(r, cons), "|".join(m), r.get("source", "")])
                has_risk.append([p, rid])
                based += [[rid, f"{p}:{a}"] for a in m]
    _w(out / "patients.csv", ["patient_id", "age"], pat)
    _w(out / "tests.csv", ["test_uid", "patient_id", "code", "value", "unit", "label", "direction", "k", "n", "U", "classified_by"], tests)
    _w(out / "authorities.csv", ["authority", "name", "documents_json"], auth)
    _w(out / "reference_intervals.csv", ["code", "unit", "low", "high", "source", "ref"], ri)
    _w(out / "disease_risks.csv", ["risk_uid", "layer", "disease", "rule", "confidence", "eta", "matched_tests", "guideline_source"], risks)
    _w(out / "rel_has_test.csv", ["patient_id", "test_uid"], [[t[1], t[0]] for t in tests])
    _w(out / "rel_voted_by.csv", ["test_uid", "authority", "vote", "refs", "links", "limit_source"], voted)
    _w(out / "rel_classified_by.csv", ["test_uid", "code"], classified)
    _w(out / "rel_has_disease_risk.csv", ["patient_id", "risk_uid"], has_risk)
    _w(out / "rel_based_on_test.csv", ["risk_uid", "test_uid"], based)
    (out / "load_graph.cypher").write_bytes(CYPHER.encode("utf-8"))   # LF only: byte-identical across platforms (write_text on Windows writes CRLF)
    return {"patients": len(pat), "tests": len(tests), "voted_by": len(voted), "classified_by": len(classified), "disease_risks": len(risks), "based_on_test": len(based)}


def _cypher() -> str:
    """load_graph.cypher (Neo4j 5, no plugins; revised for SI S2, 2026-10-23): one uniqueness constraint per node label,
    nodes created per label, relationships matched through the indexed label of each test or disease-risk node, numeric
    properties typed, MERGE throughout so the script can be run again on the same database."""
    TEST = [("NORMAL", "NormalTest"), ("ATTENTION", "AttentionTest"), ("CRITICAL", "CriticalTest")]
    RISK = [("overt", "OvertDiseaseRisk"), ("hidden", "HiddenDiseaseRisk")]
    def pick(var, key, labels):   # CALL subquery returning the node with this id, whichever of the labels it carries
        return ("CALL { WITH row MATCH (" + var + ":" + labels[0] + " {" + key + ": row." + key + "}) RETURN " + var
                + "".join("\n       UNION WITH row MATCH (" + var + ":" + l + " {" + key + ": row." + key + "}) RETURN " + var for l in labels[1:]) + " }")
    L = ["// Load the graph exported by run_all.py --graph-out into Neo4j 5 (no plugins needed).",
         "// Copy the CSV files into the import folder of the database first. MERGE is used throughout, so the script can be run again.",
         "// Example queries and their expected results: Supporting Information S2."]
    for name, label, key in ([("patient_id", "Patient", "patient_id"), ("authority_id", "GuidelineAuthority", "authority"), ("reference_interval_id", "ReferenceInterval", "code")]
                             + [(l[0].lower() + "_test_id", l[1], "test_uid") for l in TEST] + [(l[0] + "_risk_id", l[1], "risk_uid") for l in RISK]):
        L.append(f"CREATE CONSTRAINT {name} IF NOT EXISTS FOR (n:{label}) REQUIRE n.{key} IS UNIQUE;")
    L += ["LOAD CSV WITH HEADERS FROM 'file:///patients.csv' AS row",
          "MERGE (p:Patient {patient_id: toInteger(row.patient_id)}) SET p.age = toInteger(row.age);",
          "LOAD CSV WITH HEADERS FROM 'file:///authorities.csv' AS row",
          "MERGE (a:GuidelineAuthority {authority: row.authority}) SET a.name = row.name, a.documents = row.documents_json;",
          "LOAD CSV WITH HEADERS FROM 'file:///reference_intervals.csv' AS row",
          "MERGE (r:ReferenceInterval {code: row.code})",
          "SET r.unit = row.unit, r.low = toFloat(row.low), r.high = toFloat(row.high), r.source = row.source, r.ref = toInteger(row.ref);"]
    for value, label in TEST:
        L += ["LOAD CSV WITH HEADERS FROM 'file:///tests.csv' AS row", f"WITH row WHERE row.label = '{value}'",
              f"MERGE (t:{label} {{test_uid: row.test_uid}})",
              "SET t.code = row.code, t.value = toFloat(row.value), t.unit = row.unit, t.label = row.label, t.direction = row.direction,",
              "    t.k = toInteger(row.k), t.n = toInteger(row.n), t.U = toFloat(row.U);"]
    for value, label in RISK:
        L += ["LOAD CSV WITH HEADERS FROM 'file:///disease_risks.csv' AS row", f"WITH row WHERE row.layer = '{value}'",
              f"MERGE (d:{label} {{risk_uid: row.risk_uid}})",
              "SET d.disease = row.disease, d.rule = row.rule, d.confidence = toFloat(row.confidence), d.eta = toInteger(row.eta),",
              "    d.matched_tests = row.matched_tests, d.guideline_source = row.guideline_source;"]
    tl = [l for _, l in TEST]; rl = [l for _, l in RISK]
    L += ["LOAD CSV WITH HEADERS FROM 'file:///rel_has_test.csv' AS row", "MATCH (p:Patient {patient_id: toInteger(row.patient_id)})",
          pick("t", "test_uid", tl), "MERGE (p)-[:HAS_TEST]->(t);",
          "LOAD CSV WITH HEADERS FROM 'file:///rel_voted_by.csv' AS row", "MATCH (a:GuidelineAuthority {authority: row.authority})",
          pick("t", "test_uid", tl), "MERGE (t)-[v:VOTED_BY]->(a)",
          "SET v.vote = row.vote, v.refs = row.refs, v.links = row.links, v.limit_source = row.limit_source;",
          "LOAD CSV WITH HEADERS FROM 'file:///rel_classified_by.csv' AS row", "MATCH (r:ReferenceInterval {code: row.code})",
          pick("t", "test_uid", tl), "MERGE (t)-[:CLASSIFIED_BY]->(r);",
          "LOAD CSV WITH HEADERS FROM 'file:///rel_has_disease_risk.csv' AS row", "MATCH (p:Patient {patient_id: toInteger(row.patient_id)})",
          pick("d", "risk_uid", rl), "MERGE (p)-[:HAS_DISEASE_RISK]->(d);",
          "LOAD CSV WITH HEADERS FROM 'file:///rel_based_on_test.csv' AS row", pick("d", "risk_uid", rl), pick("t", "test_uid", tl),
          "MERGE (d)-[:BASED_ON_TEST]->(t);"]
    return "\n".join(L) + "\n"


CYPHER = _cypher()
