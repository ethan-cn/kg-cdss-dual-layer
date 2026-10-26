# Knowledge Graph Clinical Decision Support System

The code for "A Knowledge Graph Clinical Decision Support System for Multi-Authority Guideline Reconciliation and Dual-Layer Overt/Subclinical Disease Inference" (Learning Health Systems, manuscript 5428192, revised version).

Version 2.0.0 replaces version 1.0.0.

Errors in version 1.0.0, corrected in version 2.0.0:
- Critical limits for creatinine, urea, AST, ALT and GGT were stored in the position reserved for low values and applied in the wrong direction.
- Vitamin D sufficiency and insufficiency bands were interchanged.
- The overt hypothyroidism and hyperthyroidism rules were identical and did not distinguish raised from suppressed TSH.
- The submitted Full results and ablation results came from two computations that did not apply the same disease rules.

Creatinine, urea, AST, ALT, GGT and C-reactive protein are no longer used, because none of the guideline authorities states a decision limit for them, and the rules for chronic kidney disease, liver disease and chronic low-grade inflammation have been removed for the same reason (Supporting Information S5, Appendices A and B). The analysis cohort is now all patients in the export aged 18 years or more.

Version 2.0.0 is a single implementation, with a direction test for every threshold; the counts, tables and figures in Sections 3.5 and 4 of the revised manuscript come from one run of it (`results/run4`). It includes ten guideline authorities: American Diabetes Association, World Health Organization, National Institute for Health and Care Excellence, European Thyroid Association, American Thyroid Association, British Committee for Standards in Haematology, Scientific Advisory Committee on Nutrition, Royal Osteoporosis Society, UK Kidney Association, and National Cholesterol Education Program. The former "95% CI" is a descriptive inter-authority uncertainty index U(t); the agreement count k/n is also reported.

## Directories
- `cdss/`: classification, consensus, data loading and disease-inference code.
- `analysis/`: Supporting Information S1, S3 and S4 analyses.
- `spec/`: threshold, rule and reference-interval specifications.
- `tests/`: core tests.
- `figures/`: figure-generation script.
- `results/run4/`: aggregate results and run manifests.

## Requirements
Python 3.12.3. The code uses only the Python standard library, except `figures/make_figures.py`, which needs matplotlib (tested with 3.9.2; `pip install -r requirements.txt`).

## Data
The dataset is not included. It is from Synlab Belgium and may be requested from the corresponding author. `run_all.py` reads `Result_with_uid.csv`, `Patient.csv` and `Test_Request_with_uid.csv` from the data directory.

## Reproduce
Run core tests:

    python tests/test_core.py

Run the analysis:

    python run_all.py --csv-dir <folder with the three CSV files> --out <dir>

Using the authors' data, `results.json` should have SHA256 `39acdeb215307e1867755470a1ccd8dc9eb909908da9e2ce45a66ebe2dcd5a29`, matching `results/run4/results.json`.

Supporting Information analyses:

    python analysis/s1_constants.py --csv-dir <data> --baseline <run>/results.json --out <file.json>
    python analysis/s3_haemoglobin.py --csv-dir <data> --baseline-run <run dir with results.json and graph/> --out <file.json>
    python analysis/s4_descriptive.py --run <run dir with results.json and graph/> --out <file.json>

Generate figures:

    python figures/make_figures.py <results.json> <out dir>

## Neo4j
`python run_all.py --csv-dir <data> --out <dir> --graph-out <dir>/graph` also writes the graph export (CSV files and `load_graph.cypher`), which loads without plugins; it was tested on Neo4j 2026.02.2 Enterprise (Supporting Information S2). The export contains patient-level data and is therefore not included in this repository.

## Citation
See `CITATION.cff`. Zenodo DOI: TBD.
