# Changelog

## Unreleased (main)
- Reference numbers in spec/ follow the reference list of the published article (references 28, 31 and 32 of the submitted manuscript were removed and the list renumbered).
- Sources of the free T4 and free T3 reference intervals updated to the manufacturer documents cited in the article; the intervals themselves are unchanged.
- No change in results: results/run4/results.json is identical; only the spec hashes in run_manifest.json changed.

## v2.0.0
- Removed creatinine, urea, AST, ALT, GGT and C-reactive protein: none of the guideline authorities states a decision limit for them (the critical limits of the first five had also been stored in the wrong direction).
- Removed the rules for chronic kidney disease, liver disease and chronic low-grade inflammation.
- Corrected the interchange of the vitamin D sufficiency and insufficiency bands.
- Corrected the identical overt hypothyroidism and hyperthyroidism rules so they distinguish raised from suppressed TSH.
- Consolidated the Full and ablation computations into one implementation and one run.
- Added a direction test for every threshold.
- Analysis cohort: all patients in the export aged 18 years or more.
- Replaced the former "95% CI" with a descriptive uncertainty index U(t) and reported k/n.

## v1.0.0
Code as cited in the submitted manuscript.
