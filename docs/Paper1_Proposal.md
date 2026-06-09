# Paper 1 — Research Proposal (v2 — Blueprint for Drafting)

**Version**: 2.0 (revised)
**Date**: 2026-05-04
**Supersedes**: `Paper1_Proposal.md` (v1, 2026-03-17)
**Companion documents**: `Paper1_Methodology_Formalization.md`, `Paper1_RelatedWork_Plan.md`

---

## 0. Changelog from v1

| # | Change | Rationale |
|---|--------|-----------|
| 1 | **Title rebalanced** — Dual-Layer is now the lead, Multi-Source the modifier | v1 title gave equal weight; you yourself flagged Dual-Layer as the primary contribution |
| 2 | **Fixed citation**: Sutton 2020 is *npj Digital Medicine*, not *JAMIA* | v1 had wrong journal |
| 3 | **Added §5.3 Baseline Comparison** | v1 had ablation but no external baseline — reviewers will reject without it |
| 4 | **Added §5.7 Sensitivity Analysis** | Confidence formulas use magic numbers; sensitivity analysis defends robustness |
| 5 | **Re-scoped §5.1 Evaluation paradigm**: explicit "no ground-truth diagnosis" acknowledgement + plan to extract any available ICD codes from the dataset | Reviewers will ask "are these inferences correct?" — answer head-on |
| 6 | **Removed "Coverage Analysis" as a standalone experiment**; folded into descriptive statistics | Coverage is not an evaluation metric |
| 7 | **Timeline expanded** from 4 weeks to 5–6 weeks | v1 was unrealistic for journal-quality work |
| 8 | **Added §6.3 Limitations** as a first-class section | Pre-empts reviewer concerns; demonstrates self-awareness |
| 9 | **Added blocker tracking** | Isabel's data-provenance documentation is required before §4 / §5.1 can be finalised |

---

## 1. Title (v2)

> **A Dual-Layer Overt/Subclinical Disease Inference Framework with Multi-Source Guideline Consensus in a Knowledge Graph Clinical Decision Support System**

Alternative shorter form (consider for the journal cover page):

> **Dual-Layer Disease Inference for Knowledge-Graph CDSS: Detecting Overt and Subclinical Patterns under Multi-Source Guideline Consensus**

---

## 2. Research Background

Clinical Decision Support Systems (CDSS) are now a routine component of laboratory-based clinical workflows, but most production systems remain *threshold-alert engines*: when a test value crosses a static cut-off, an alert is fired. This paradigm has three structural limitations that motivate this work.

**Single-source thresholding.** Most CDSS rely on a single guideline authority (frequently the local laboratory's reference range or one international body such as NICE or ADA). When two authorities disagree on a threshold — for instance the ADA's HbA1c criterion vs. the WHO's — the system silently inherits one viewpoint without exposing that choice or its uncertainty (Sutton et al., 2020).

**No subclinical surveillance.** Borderline values that fall in the *attention* zone — between strict normality and overt critical thresholds — are routinely flagged at the per-test level but not aggregated into disease-pattern hypotheses. Subclinical hypothyroidism, prediabetes, early CKD, and sub-deficient vitamin D status all sit in this zone and are systematically overlooked by alert-only CDSS.

**Opacity vs. trust.** Machine-learning CDSS deliver high predictive accuracy but degrade clinician trust through opacity (Asan et al., 2020; XAI-CDSS reviews 2024-2025). Rule-based systems with full evidence traceability are an under-explored design point that meets both the accuracy demand and the explainability demand.

This paper introduces a framework that addresses all three limitations within a single knowledge-graph CDSS validated on real laboratory data from a UK clinical laboratory cohort.

---

## 3. Research Gap

| # | Gap | Evidence basis |
|---|-----|---------------|
| **G1** | No systematic, computable mechanism reconciles per-test thresholds across multiple guideline authorities — current consensus efforts (Delphi, ACCORD) operate at the recommendation level, not at the lab-data level | Ozarda et al. 2018; ACCORD 2024 |
| **G2** | No CDSS framework explicitly designs for the *dual-layer* (overt + subclinical) disease inference problem with a formal exclusion mechanism preventing overlapping inferences | Literature search §2 (no positive hits) |
| **G3** | KG-based CDSS exist for medication recommendation and link prediction, but evidence-traceable, guideline-authority-anchored disease inference remains under-explored | KG-CDSS Reasoning Survey 2019; Patient-centric KG Survey 2024 |

---

## 4. Research Objectives

1. **Formalise** a dual-layer disease inference model (Definitions 4–6) with a provable non-overlapping property (Theorem 1, see `Paper1_Methodology_Formalization.md`).
2. **Construct** a multi-source guideline consensus mechanism (Definitions 1–3) integrating 9 international authorities (ADA, WHO, ESC, NICE, KDIGO, ATA, ETA, ICSH, IFCC) with quantified per-test confidence and 95% CI.
3. **Implement** the framework as a Neo4j knowledge graph with patient → test → consensus-classification → disease-risk evidence chains.
4. **Empirically evaluate** on 970 UK clinical-laboratory patients (14,104 test results) against (a) ablation of authority count, (b) NICE-only baseline, (c) sensitivity analysis of confidence hyperparameters, and (d) descriptive comparison against UK epidemiology.

---

## 5. Methodology

Detailed mathematical formalization is delegated to `Paper1_Methodology_Formalization.md` (Definitions 1–7, Theorem 1, Corollary 1, end-to-end algorithm). This proposal summarises only the architecture.

### 5.1 System overview

```
┌──────────────────────────────────────────────────────────────────┐
│ Patient lab record P                                              │
│   ↓                                                               │
│ [Stage 1] Per-test consensus classification (Defs 1–3)            │
│   - 9 authorities vote independently                              │
│   - Consensus class ∈ {NORMAL, ATTENTION, CRITICAL}               │
│   - Confidence + 95% CI                                           │
│   ↓                                                               │
│ [Stage 2] Overt disease inference (Def 5)                         │
│   - 8 overt rules; confidence ∈ [0.70, 0.95]                      │
│   ↓                                                               │
│ [Stage 3] Hidden disease inference (Defs 6, 7)                    │
│   - 7 hidden rules; confidence ∈ [0.50, 0.75]                     │
│   - Exclusion mechanism enforces Theorem 1                        │
│   ↓                                                               │
│ Patient-level KG: NormalTest / AttentionTest / CriticalTest       │
│  + OvertDiseaseRisk / HiddenDiseaseRisk + BASED_ON_TEST chains    │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 Knowledge-graph schema

- **Patient** ⟶ {NormalTest | AttentionTest | CriticalTest}
- **Patient** ⟶ {OvertDiseaseRisk | HiddenDiseaseRisk}
- **DiseaseRisk** ⟶ BASED_ON_TEST ⟶ Test (evidence chain — basis for explainability)
- **Test** ⟶ CLASSIFIED_BY ⟶ GuidelineAuthority (provenance — basis for traceability)

Each disease-risk node carries: rule ID, confidence, 95% CI, inferred timestamp, exclusion-passed flag (for hidden risks), and a serialized list of supporting test IDs. Every authority node carries: name, evidence level (Oxford CEBM grade), authority weight, sensitivity, source publication DOI.

### 5.3 Why this design

The KG substrate is chosen for three reasons: (i) traceability of evidence is structural rather than reconstructed post-hoc, (ii) the consensus voting and exclusion mechanism map naturally onto graph-pattern queries (Cypher), and (iii) future extensions (Paper 2 NLP symptom extraction, Paper 3 PageRank/PPR reasoning) compose on the same schema.

---

## 6. Evaluation Plan

### 6.1 Dataset

970 patients × 14,104 test results from a UK clinical laboratory (data provenance pending Isabel — see §10 Blockers). 23 lab test types covered. **No formal diagnosis labels** are available in the raw extract; if any ICD codes or coded conditions can be extracted from accompanying patient summaries, they will be used as a supplementary partial-truth set in §6.4.

### 6.2 Evaluation paradigm and honest framing

Because no exhaustive ground-truth diagnosis is available, this paper does **not** claim diagnostic accuracy. It claims:
- (a) **Construct validity** — the framework produces inferences whose distributions are clinically plausible against UK epidemiology;
- (b) **Methodological value** — multi-source consensus and dual-layer inference each contribute over single-source / single-layer alternatives;
- (c) **Robustness** — conclusions are stable under perturbation of confidence hyperparameters;
- (d) **Explainability** — every inference has a complete, traceable evidence chain.

This framing is reflected throughout §6.3–§6.7.

### 6.3 §5.3 Baseline comparison ★ NEW vs. v1

| Baseline | Description | What it stress-tests |
|----------|-------------|---------------------|
| **B1: NICE-only threshold alert** | Classify tests using NICE thresholds only; flag any patient with ≥1 critical test | Without consensus, do we miss/over-call patients? |
| **B2: Local lab reference range alert** | Use the lab's published reference ranges only | This is what most production CDSS actually do |
| **B3: Single-layer (overt-only) version of our system** | Drop Layer 2 entirely | Quantifies the *unique* contribution of subclinical detection |

Reported metrics (since no full ground truth): per-baseline distribution of flagged patients; agreement matrix vs. our system; subset analysis on whatever partial-truth labels exist.

### 6.4 Ablation: authority count

Incrementally activate authorities — Config-1 (NICE only) → Config-3 (+ADA, WHO) → Config-6 (+ESC, KDIGO, ATA) → Config-9 (full). Measured outputs: (i) consensus class distribution shifts, (ii) confidence-CI width as authority count grows, (iii) marginal contribution of each authority added.

### 6.5 Disease inference distribution

Compare per-disease inferred frequency against UK epidemiology (Health Survey for England 2022, UK Biobank, BJGP cohort studies — see `Paper1_RelatedWork_Plan.md` §7). Differences quantified as ratios, not as accuracy claims.

### 6.6 Overt-Hidden co-occurrence

Per-patient analysis: how many patients have only overt, only hidden, both (different diseases), or neither? This validates Theorem 1 empirically and demonstrates the dual-layer's clinical added value.

### 6.7 §5.7 Sensitivity analysis ★ NEW vs. v1

Perturb each hyperparameter (α, β, $k^{\max}_{\text{cons}}$, $k^{\max}_{\text{src}}$, overt floor/ceiling/step, hidden floor/ceiling/step — see formalization §3.6) by ±20% and report the percentage shift in disease-inference distributions. Robust if shifts < 5% on aggregate metrics.

### 6.8 Case studies

Two to three representative patients with full evidence trails, presented as figures: KG sub-graph showing test → consensus → disease inference → guideline authorities. Selected to illustrate (a) overt-only, (b) hidden-only, (c) coexisting overt + hidden (different diseases) cases.

---

## 7. Expected Contributions

1. **Formalised dual-layer disease inference model** (Definitions 4–7, Theorem 1) — novel in the CDSS literature; provides a theoretical foundation that other rule-based CDSS can adopt.
2. **Multi-source guideline consensus algorithm with quantified uncertainty** (Definitions 1–3) — applicable beyond this specific system to any setting where multiple authoritative thresholds disagree.
3. **Empirical demonstration on a 970-patient UK cohort** with explicit acknowledgement of validation limits, contributing realistic evidence on what such a framework can and cannot claim without diagnostic ground truth.
4. **Open KG schema** (Neo4j) with traceable evidence chains, supporting third-party reproducibility.

---

## 8. Target Journals (revised)

| Journal | 2024 IF (verify) | Fit | Notes |
|---------|------------------|-----|-------|
| **Journal of Biomedical Informatics** | ~4.0 | High — strong KG + CDSS history | First-choice; reviewers expect rigorous evaluation, so §6.3 and §6.7 are essential |
| **BMC Medical Informatics and Decision Making** | ~3.5 | High — open access, methodology-friendly | Good fallback; faster review |
| **Artificial Intelligence in Medicine** | ~7.0 | Medium — but possible if framed as KG+rules+XAI | Consider if §6.7 robustness is strong |
| **Applied Sciences (MDPI)** | ~2.8 | Lower fit but fastest | Last resort; only if revisions extend timeline |

Recommendation: submit to JBI first; if rejected without major revision, redirect to BMC MIDM. AIM is a stretch but reachable if the methodology section is tight.

---

## 9. Timeline (revised, realistic)

| Phase | Days | Deliverable |
|-------|------|-------------|
| **W1: Methodology + Literature** | 5 | §3 Methodology written using formalization doc; §2 Related Work first draft |
| **W2: Implementation + Baselines** | 5 | Baseline B1-B3 implemented; ablation script; sensitivity-analysis script |
| **W3: Results + Figures** | 5 | All §5 results computed, figures generated |
| **W4: Discussion + Abstract + integration** | 5 | §6 Discussion, §1 Intro, Abstract, §7 Conclusion all drafted |
| **W5: Internal review + revision** | 5 | Supervisor / co-author feedback incorporated |
| **W6: Polish + submission package** | 3 | Cover letter, figures finalised, language polish, submission |
| **Total** | **~28 working days (~5–6 calendar weeks)** | Submission-ready manuscript |

This is **2 weeks longer** than v1's plan and reflects the real overhead of (a) baseline implementation, (b) sensitivity analysis, (c) supervisor turnaround time.

---

## 10. Blockers & Outstanding Items

| # | Blocker | Owner | Impact if unresolved |
|---|---------|-------|---------------------|
| **B1** | **Data provenance documentation from Isabel** — dataset source, ethics approval, TDL reference range source, data usage agreement | Isabel | §4 / §5.1 cannot be finalised; ethical-statement section blank → desk reject risk |
| **B2** | DOI verification on candidate references in `Paper1_RelatedWork_Plan.md` | Ethan | §2 must use only verified citations |
| **B3** | Confirmation of which ADA / WHO / NICE *editions* (year) the threshold tables use | Ethan | Methodology authority weights need exact source publications |
| **B4** | Whether any ICD codes / coded conditions can be extracted from the patient records (any partial-truth labels?) | Ethan + Isabel | Determines whether §6.3 can include a precision/recall sub-table |

---

## 11. Risk Register & Mitigation

| Risk | Severity | Mitigation |
|------|----------|------------|
| Reviewer demands ground-truth diagnostic accuracy | High | §6.2 honest framing; explicit Limitations §6.3 in manuscript; cite analogous CDSS methodology papers that use construct-validity framing |
| Confidence formula hyperparameters seen as ad hoc | Medium-High | §6.7 sensitivity analysis demonstrates robustness; §3.6 hyperparameter table makes them explicit |
| Authority weights $w_i$ argued as subjective | Medium | Calibrate from prior CDSS surveys; report sensitivity to $w_i$ alongside $\alpha, \beta$; acknowledge in Limitations |
| Dataset size (970 patients) seen as small | Low-Medium | Frame as proof-of-concept methodology paper; cite comparable-size CDSS validation papers |
| Theorem 1 dismissed as "trivial" | Low | Defend in cover letter as a *correctness guarantee* for the exclusion mechanism — the value is in the formal statement, not the proof difficulty |

---

## 12. Decision Points Before Drafting Begins

Before committing to the manuscript, these three decisions must be made:

1. **Is there any partial ground-truth available** (ICD codes, coded conditions, GP notes, follow-up tests)? If yes, even on a 100-patient subset, §6.3 acquires precision/recall. Resolves Blocker B4.
2. **Single-paper or paper-series framing?** v2 stands alone; if framed as Part 1 of a 3-paper series (with Paper 2 NLP and Paper 3 KG reasoning per `README.md`), the Discussion can defer some limitations to "future work in Paper 2/3". Recommend single-paper standing for Paper 1 — keep the series framing only in §6 and Conclusion.
3. **Journal-first or venue-flexible?** If JBI is the firm target, the manuscript should be tuned to JBI's structure (longer Methods, shorter Background). If venue-flexible, write generic IMRAD and adapt at submission.

---

*Proposal v2 supersedes v1. Begin drafting against this document; consult `Paper1_Methodology_Formalization.md` for §3 content and `Paper1_RelatedWork_Plan.md` for §2 reference selection.*
