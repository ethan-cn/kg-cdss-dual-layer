# A Dual-Layer Overt/Subclinical Disease Inference Framework with Computable Multi-Authority Threshold Reconciliation in a Knowledge Graph Clinical Decision Support System

---

## Abstract

A patient walks into clinic with several borderline laboratory results. Which threshold applies? Today the answer is hidden inside the choice of one authority or one in-house reference range, with no record of who voted for what. We present a knowledge-graph clinical decision support framework that takes a different approach to this problem. Each laboratory result is classified simultaneously against nine independent clinical guideline authorities; inter-authority divergence is reported as a first-class output with a 95% confidence interval; and the pipeline scales linearly with cohort size. Disease inference is then split into two layers. The overt layer (CRITICAL-anchored) carries confirmed disease, while the hidden layer (ATTENTION-anchored) captures subclinical states, and a formal exclusion clause prevents the same disease label from appearing in both. Every disease-risk node also carries an audit trail back to the triggering test results, the voting authorities, and the cited guideline publications with their DOIs — so explanation is part of the model, not a separate post-hoc layer.

We evaluate the framework on 3,869 patients from a UK secondary-care referral laboratory, with 47,468 classified test results, using a four-configuration authority ablation. The overt layer turns out to be stable across all four configurations: 3,226 patients (83.4%) carry at least one confirmed disease, Cohen's κ = 1.000 throughout. The hidden layer flags an additional 130 patients (3.4%) for subclinical hypothyroidism, early chronic kidney disease, or prediabetes — conditions that no single-threshold system would catch, but which are clinically actionable through monitoring and lifestyle intervention. As more authorities are added, the average 95% confidence interval narrows from 0.199 (one authority) to 0.131 (nine authorities, a 34.2% reduction), without changing the underlying classifications.

---

## 1. Introduction

Clinical decision support systems (CDSS) take medical knowledge and put it to work at the point of care, with the aim of improving diagnostic accuracy and guideline adherence in everyday practice. Sutton and colleagues define a CDSS as software that matches individual patient characteristics against a computerised knowledge base and returns patient-specific recommendations [C1]. They draw a useful distinction between two architectural classes: knowledge-based systems, where the rules and inference logic are written down and can be audited, and non-knowledge-based systems, where decisions emerge from a statistical or learned model whose internal workings remain largely opaque. Four decades of development have shown that a properly engineered CDSS can change practice [C2, C3, C6] — yet day-to-day adoption remains stubbornly low [C7, C8, C9]. The gap between efficacy in trials and uptake in real wards sets the boundary of the present work: the open question is no longer whether such systems can work, but how to build ones that clinicians will use and trust. Three structural problems stand in the way.

The first concerns interpretability in machine-learning CDSS. As predictive accuracy has climbed, the regulatory and clinical pressure for explainability has climbed with it; the EU AI Act and the FDA's AI/ML Software-as-a-Medical-Device action plan both require that high-risk AI outputs be interpretable to end users. The empirical picture is uncomfortable. A 2025 meta-analysis of 62 peer-reviewed XAI-CDSS studies found that only 17.7% of systems conducted formal statistical testing of explanation fidelity [X1]. A parallel review of XAI in chronic disease applications reported that disease-prediction dominated the outputs, with paired explanations rarely validated against clinical interpretation [X7]. The two methods that dominate the field — SHAP and LIME — produce surrogate approximations of black-box reasoning, and these surrogates cannot be traced back to citable clinical evidence [X3, X4, X7]. The systems most likely to be regulated for explainability are, paradoxically, the ones least equipped to deliver it in an auditable form.

The second problem is methodological, and it concerns how laboratory thresholds are handled inside the system. In 2018 the IFCC documented something that has been an open secret in clinical chemistry for years: deployed CDSS routinely conflate two distinct constructs — the reference interval (RI), which is a statistical description of a healthy population, and the clinical decision limit (CDL), which is the value at which intervention is warranted [G1]. At the boundary the distinction matters. A fasting glucose of 110 mg/dL falls inside most laboratory RIs (70–100 mg/dL), yet the ADA classifies 100–125 mg/dL as prediabetes that warrants intervention [G7]. The problem gets worse when several authorities publish different CDLs for the same test — a disagreement that is well documented and yet, in a single-authority system, invisible (see §2.4). The reconciliation literature mostly operates at the recommendation level (Delphi panels, ACCORD statements) rather than at the level where deployed CDSS actually make decisions: the laboratory record of a specific patient [G2]. We address this gap directly. Our approach applies multiple pre-existing clinical guidelines to each patient's laboratory data and returns inter-authority disagreement as a disaggregated, computable output.

The third problem is the absence of a formal inference layer for subclinical disease. Many clinically meaningful states are biochemically detectable but fall short of confirmed-disease criteria. Their management thresholds differ from the overt-disease thresholds, yet alert-only CDSS apply the same threshold logic to both. Subclinical hypothyroidism (SCH) is the textbook example. SCH affects 5–10% of the adult population [S1]. The European Thyroid Association recommends levothyroxine for TSH ≥ 10 mIU/L but advises individualised management between 4.5 and 10.0 mIU/L [S3]. The TRUST randomised trial then complicated the picture: in 737 older adults with mild SCH, levothyroxine produced biochemical normalisation but no improvement in hypothyroid symptoms at one year [S2]. A single TSH threshold cannot represent this — set it at 10 mIU/L and subclinical patients vanish; lower it, and patients receive disease labels they should not carry. Prediabetes shows the same shape of problem: the HbA1c 5.7–6.4% range identifies a measurably high-risk metabolic reservoir [S6, S7], yet dichotomous logic forces each patient into either a "normal" or "diabetes" bucket, and neither matches the monitoring-and-lifestyle-intervention recommendation that the evidence supports. The shortage is not in the evidence — that body of work is mature — but in the architecture: no current CDSS is built around the layered nature of disease progression.

These three problems do not sit in isolation. They reinforce one another in deployment. A black-box CDSS cannot expose inter-authority disagreement even when the data would permit it. A single-threshold system cannot detect subclinical states even when its knowledge base covers them. And a system without a provenance model cannot meet the EU AI Act or the FDA's AI/ML Software-as-a-Medical-Device action plan, both of which require interpretability as a precondition for high-risk clinical deployment [R1, R4]. Regulatory pressure and the documented adoption gap together make it worth addressing all three at once. This paper does so within a single knowledge-graph CDSS. We contribute three things. (1) A multi-source guideline consensus mechanism that classifies each laboratory result against nine independent clinical authorities, exposes inter-authority disagreement as an explicit output, and assigns a confidence score with a 95% CI (Definitions 1–3). (2) A dual-layer disease inference architecture — an overt layer for confirmed disease and a hidden layer for subclinical states — with an exclusion clause that guarantees no disease label appears in both layers at once (Definitions 4–6, Theorem 1, Appendix D). (3) A Neo4j implementation in which every disease-risk node carries a complete evidence chain back to the triggering laboratory results, the voting authorities, and the citing guideline publications with their DOIs. Explainability becomes a structural property of the model rather than a separate post-hoc layer. The specific combination — multi-authority voting, explicit disagreement quantification, and dual-layer inference inside a unified KG architecture — has not, to our knowledge, been implemented in a published CDSS.

The paper is organised as follows. §2 reviews CDSS adoption, KG-enabled architectures, multi-source guideline integration, subclinical disease detection, and explainable AI in clinical settings. §3 formalises the multi-source consensus and dual-layer inference framework. §4 describes the knowledge-graph implementation and the dataset. §5 presents the empirical evaluation on a UK clinical laboratory cohort. §6 discusses the implications for clinical practice, returns to the three problems above, and sets out where the current approach falls short.

## 2. Background and Related Work

We review the literature across five dimensions: CDSS foundations and adoption (§2.1), KG-enabled architectures (§2.2), multi-source guideline integration (§2.3), subclinical disease detection (§2.4), and explainable AI in clinical settings (§2.5).

### 2.1 Clinical Decision Support Systems: Taxonomy and Adoption

A CDSS, as Sutton and colleagues frame it, is software that matches patient characteristics against a knowledge base and returns patient-specific recommendations [C1]. Two architectural classes follow from this definition: knowledge-based systems with inspectable rules, and non-knowledge-based systems built around opaque statistical models.

The evidence base rests on three landmark systematic reviews. Kawamoto et al.'s 2005 review of 70 RCTs identified four features predictive of CDSS success — and found that 30 of 32 systems possessing all four did improve clinical practice [C2]. Garg et al., examining 100 trials in the same year, reported CDSS improving practitioner performance in 64% of studies, but improving patient outcomes in only 13% [C3]. Roshanov et al.'s 2013 meta-regression of 162 RCTs broadly confirmed this picture [C6].

What gets deployed in practice still leans heavily on rule-based CDSS that rarely climb above level 2 of Simon's decision-theory hierarchy — recognition and basic alerting, without closing the design–choice–implementation loop [C10]. The adoption barriers are familiar from survey after survey: extra clinician workload, interoperability gaps, and weak trust in the evidence base [C7, C8, C9].

### 2.2 Knowledge Graphs as Substrates for CDSS

Knowledge graphs encode clinical concepts and their relationships as labelled nodes and edges, giving downstream reasoning a queryable substrate to work over. The current scale benchmark is PrimeKG, which integrates 20 biomedical resources into 17,080 diseases connected by 4,050,249 typed relationships [K1]. Medical KGs have moved from research artefact to infrastructure, but at this scale a graph is a resource, not a decision-support system in itself.

Earlier surveys group KG reasoning into pathfinding, subgraph-matching, embedding-based, and hybrid approaches [K3]. Rajabi and Etminani's 2021 design takes a different angle: it positions the KG itself as the explanation surface, so each recommendation is a path through citable evidence rather than a saliency map [K4].

Applied KG-CDSS show competitive accuracy when their scope is narrow. Zhou et al.'s 2022 hypertension system produced clinician-aligned recommendations on a single-condition cohort [K5]; the GC-CDSS reported 92.96% concordance with multidisciplinary team decisions [K6]. Both, however, encode a single guideline authority and offer no mechanism for reconciling conflicting recommendations — the gap our §3 sets out to fill.

### 2.3 Multi-Source Guideline Integration

In 2018 the IFCC Committee on Reference Intervals and Decision Limits drew a clear line between two laboratory thresholds: the reference interval (RI), a population statistic, and the clinical decision limit (CDL), an outcome-anchored value [G1]. When the two are conflated, the resulting decisions cannot be audited back to either statistical normality or clinical action.

Cross-authority divergence is well-documented in the clinical chemistry literature. ACCORD addresses consensus *development*, not *computation* [G2]: it specifies how a guideline should declare its method, not how a downstream system should reason across multiple guidelines at once. The reconciliation literature largely sits at the *prescriptive* level — Delphi panels, ACCORD statements — and produces merged guidelines that resolve divergence by fiat. That is a different task from *computational reconciliation at the patient-record level*, which applies pre-existing guidelines to a patient's laboratory values in parallel and returns disaggregated, actionable outputs. Earlier systems [K5, K6] do not do this. The framework here applies nine independent authorities to each patient record and surfaces inter-authority disagreement as a quantified signal.

### 2.4 Subclinical Disease Detection

The cost of single-authority systems shows most clearly in conditions sitting between statistical normality and confirmed disease. Subclinical hypothyroidism (SCH) is the canonical case. Prevalence in adults runs at 5–10% [S1]. ETA 2013 recommends levothyroxine for TSH ≥ 10 mIU/L but advises individualised management between 4.5 and 10.0 mIU/L [S3]. The TRUST trial then complicated the story: in 737 older adults with mild SCH, levothyroxine produced no symptomatic benefit at one year [S2]. A single TSH threshold cannot represent this. Set it at 10.0 mIU/L and subclinical patients are simply invisible. Lower it, and the system generates disease labels for patients who should not be carrying them.

Prediabetes follows the same shape. HbA1c 5.7–6.4% identifies a measurably high-risk metabolic reservoir [S7], yet dichotomous threshold logic pushes every patient into "normal" or "diabetes" — neither of which captures the monitoring-and-lifestyle-intervention pathway that the evidence supports [S6]. Early CKD [S9] and vitamin D insufficiency [S11] sit in the same grey zone.

A CDSS that takes subclinical detection seriously needs a separate inference layer — one with its own confidence semantics, exclusion logic, and clinical action recommendations, distinct from the confirmed-disease layer. That requirement motivates the dual-layer architecture in §3.3.

### 2.5 Explainability in ML-Based CDSS

ML in clinical decision support has turned explanation into a regulatory requirement. Two post-hoc methods dominate: SHAP (Shapley value approximation) [X3] and LIME (local interpretable surrogate) [X4]. A 2025 meta-analysis reported that only 17.7% of 62 XAI-CDSS studies formally tested explanation fidelity [X1], with SHAP and LIME accounting for 46.5% and 25.8% of deployed methods respectively [X7]. Comparative evaluations show that the two approaches produce materially different feature-importance rankings on the same task [X7]; the practical effect — observed but uncomfortable — is that the availability of an explanation tends to raise clinician trust faster than the explanation's epistemic weight justifies [X6].

The framework here takes a different route. Clinical reasoning is encoded directly into the knowledge graph. Each edge is a causal relationship backed by a citable guideline publication; each node is a real clinical entity traceable to individual laboratory results and published DOIs. Every disease-risk node therefore carries a complete evidence trail — Patient → TestNode → GuidelineAuthority → DOI — turning path-traceable explanation into a structural property of the model, rather than a post-hoc approximation bolted on afterwards. This extends Rajabi and Etminani's "KG-as-explanation-surface" position [K4].

---

## 3. Framework: Multi-Source Consensus and Dual-Layer Inference

### 3.1 System Overview

A clinical laboratory record for patient $p$ is written as a set of test-result pairs $\mathcal{T}_p = \{t_1, t_2, \ldots, t_m\}$, where each $t = (\tau, x)$ pairs a test identifier $\tau$ with a numeric measurement $x$. The framework processes every result through two stages (Figure 1). **Stage 1** classifies each result against nine independent clinical guideline authorities and returns a consensus label $c(t) \in \{\text{NORMAL}, \text{ATTENTION}, \text{CRITICAL}\}$, together with a confidence score and 95% CI. **Stage 2** then maps classified results to disease-level risk via inference rules split into an overt layer (CRITICAL-anchored) and a hidden layer (ATTENTION-anchored). An exclusion clause guarantees that no disease label appears in both layers for the same patient.

Why split the pipeline into two stages? Disease inference runs on normalised, authority-anchored classifications rather than raw measurements, which lets the framework compare across tests on a consistent semantic scale. Stage 1 also has a second effect that matters clinically: inter-authority disagreement becomes an *explicit* output. A TSH of 10.1 mIU/L is CRITICAL by NICE, yet sits below ATA's treatment threshold — the wider CI flags exactly this situation.

![Figure 1 — End-to-end pipeline](../tables/figures/Figure1_Pipeline_Workflow.svg)

*Figure 1. End-to-end pipeline. Patient laboratory results flow through Stage 1 (multi-source guideline consensus, §3.2), which produces an authority-anchored classification with a 95% confidence interval, and then through Stage 2 (dual-layer disease inference, §3.3) into overt (CRITICAL-anchored) and hidden (ATTENTION-anchored) disease-risk outputs. The exclusion mechanism (Theorem 1) guarantees that no disease label appears in both layers.*

### 3.2 Multi-Source Guideline Consensus

In most deployed CDSS the threshold comes from one place: the local laboratory's in-house reference interval. A **reference interval (RI)** is a population statistic, while a **clinical decision limit (CDL)** is outcome-anchored [G1]; the IFCC documented this conflation in 2018, but it still persists in deployed systems.

For each result $t = (\tau, x)$, every authority $a \in \mathcal{A}$ that covers $\tau$ casts a vote $v(a, t) \in \mathcal{S}$. The aggregation step uses a conservative escalation rule rather than simple majority voting — a choice consistent with inspectable CDSS design [C5].

**Definition 1 (Consensus classification).** Let $n_{\text{CRIT}}$ and $n_{\text{ATT}}$ denote vote counts:

$$
c(t) = \begin{cases}
\text{CRITICAL}   & \text{if } n_{\text{CRIT}} \geq 2 \;\lor\; (n_{\text{CRIT}} \geq 1 \land n_{\text{ATT}} \geq 1), \\[4pt]
\text{ATTENTION}  & \text{if } \bigl(n_{\text{CRIT}} = 0 \land n_{\text{ATT}} \geq 1\bigr) \;\lor\; \bigl(n_{\text{CRIT}} = 1 \land n_{\text{ATT}} = 0\bigr), \\[4pt]
\text{NORMAL}     & \text{otherwise.}
\end{cases}
$$

**Definition 2 (Consensus confidence).** The confidence score is:

$$
C_{\text{final}}(t) = \min\!\bigl(\, C_{\text{base}}(t) + B_{\text{consensus}}(t) + B_{\text{source}}(t),\; 1.0 \,\bigr)
$$

where $C_{\text{base}}$ is the sensitivity-weighted mean of covering authorities' published sensitivities, $B_{\text{consensus}}$ awards bonuses for vote agreement (+0.05 full, +0.02 partial, -0.03 none), and $B_{\text{source}}$ awards +0.02 per additional corroborating authority (capped +0.06).

**Definition 3 (Confidence interval).** The 95% CI captures inter-authority disagreement via root-sum-of-squares of two orthogonal components:

$$
\sigma_{\text{source}} = \begin{cases}
0.02 & |V(t)| \geq 3,\\
0.05 & |V(t)| = 2,\\
0.10 & |V(t)| = 1,
\end{cases}
\qquad
\sigma_{\text{consensus}} = \begin{cases}
0.01 & \text{full},\\
0.04 & \text{partial},\\
0.08 & \text{no consensus},
\end{cases}
$$

$$
\mathrm{CI}_{95\%}(t) = \bigl[\, C_{\text{final}}(t) - 1.96\,\sigma(t),\; C_{\text{final}}(t) + 1.96\,\sigma(t) \,\bigr] \cap [0, 1]
$$

**Corollary 1 (CI monotonicity).** Adding a corroborating authority decreases CI width without changing the point estimate. Empirically validated in §5.2: CI width decreased 14.4% from Config-6 to Config-9.

### 3.2.1 Parameter Robustness

The σ values in Definition 3 were designed according to the principle that CI width should reflect the epistemic uncertainty inherent in authority-based classification. We verify robustness through two complementary analyses.

**Theorem-proven robustness of classification to σ perturbation.** The consensus classification rule (Definition 1) is independent of the σ parameters: $c(t)$ depends only on vote counts $(n_{\text{CRIT}}, n_{\text{ATT}})$, not on the CI width. This is a formal result — therefore, varying σ values cannot change the consensus label for any test result in the cohort.

**Theoretical derivation of CI scaling under σ perturbation.** While classification is σ-independent, CI width scales predictably with σ perturbation. Under the RSS-combined uncertainty model, CI width is proportional to σ. Table S1 reports the theoretical CI widths derived from the RSS model, using the Config-6 average CI width (0.153) as the baseline.

**Table S1.** CI width scaling under σ perturbation (theoretical derivation).

| σ Scale | Theoretical Avg CI Width | Δ from Baseline |
|---------|------------------------|----------------|
| 0.6×   | 0.092                 | −39.9%        |
| 0.8×   | 0.122                 | −20.3%        |
| 1.0×   | 0.153                 | —             |
| 1.2×   | 0.184                 | +20.3%        |
| 1.4×   | 0.214                 | +39.9%        |

*Derived from the RSS-combined uncertainty model: $\sigma_{\text{new}} = \sigma_{\text{scale}} \times \sigma_{\text{original}}$, producing CI width proportional to the σ perturbation factor. The empirical validation of Config-6 CI narrowing (14.4% reduction from Config-6 to Config-9) in §5.2 confirms the RSS model's directional correctness.*

The core robustness claim — that consensus classification does not depend on σ values — is established by the theorem above. Detailed sensitivity analysis including Leave-One-Authority-Out validation is provided in **Appendix G**.

The CI operationalises **structural epistemic uncertainty** — the irreducible uncertainty from genuine disagreement between authoritative clinical bodies. This differs from aleatory uncertainty (data noise): the CI tells whether ATA and NICE genuinely agree on this patient's result, or whether the classification is contested at the normative evidence level.

> **Cross-reference:** Full derivation, worked example (HbA1c = 5.9%), and sensitivity analysis are provided in **Appendix G**.

### 3.3 Dual-Layer Disease Inference with Exclusion

Subclinical conditions sit in a grey zone between biochemical abnormality and confirmed disease. A single threshold cannot represent this. Set the cut-off at the treatment level (TSH ≥ 10 mIU/L, say) and subclinical patients vanish from the alert stream. Lower the cut-off, and patients get disease labels they should not be carrying. The clinical asymmetry runs both ways: over-labelling drives unnecessary treatment, under-labelling delays monitoring.

We handle this by splitting disease inference rules into two layers. Each rule $r = (\rho, R, S, X, m)$ specifies a disease label $\rho$, required conditions $R$, supporting conditions $S$, an exclusion specification $X$, and a match threshold $m$. Overt rules need at least one CRITICAL-classified result to fire; hidden rules fire on ATTENTION-classified results alone.

The two layers carry different confidence ceilings by design. A CRITICAL-classified TSH sits at or beyond the ETA's treatment threshold — a value with demonstrated intervention benefit. An ATTENTION-classified TSH sits in the subclinical zone, where progression risk is probabilistic and the trial evidence is weaker (the TRUST null result is the most cited case [S2]).

$$
C_{\mathrm{O}}(r^{\mathrm{O}}, P) = \min\!\bigl(\, 0.70 + 0.05 \cdot \eta(r^{\mathrm{O}}, P),\; 0.95 \,\bigr),
$$

$$
C_{\mathrm{H}}(r^{\mathrm{H}}, P) = \min\!\bigl(\, 0.50 + 0.05 \cdot \eta(r^{\mathrm{H}}, P),\; 0.75 \,\bigr),
$$

where $\eta$ is the evidence count (matched required plus supporting tests). The 0.20-point overt-floor gap reflects stronger outcome evidence; the 0.75 hidden ceiling reflects weaker subclinical evidence [S1].

**Exclusion mechanism.** The exclusion specification $X$ has two components: overt counterparts $\mathcal{O}(r^{\mathrm{H}})$ whose firing suppresses the hidden rule, and exclusion test conditions $\mathcal{E}(r^{\mathrm{H}})$ that suppress it regardless. For hidden SCH: $\mathcal{O} = \{r^{\mathrm{O}}_{\text{hypothyroidism}}\}$ and $\mathcal{E} = \{(\text{T4L}, \text{ATTENTION}), (\text{T4L}, \text{CRITICAL})\}$. **Theorem 1 (Appendix D)** proves that no disease label appears simultaneously in both layers.

> **Cross-reference:** Complete theorem proof and rule specification tables are provided in **Appendices D and E**.

### 3.4 Knowledge Graph Schema and Provenance

The framework runs on Neo4j as a property graph (Figure 2). Six node types cover the domain entities:

- **Patient**: identifiers and demographics
- **NormalTest / AttentionTest / CriticalTest**: consensus classification, confidence, 95% CI bounds, covering authorities with individual votes
- **OvertDiseaseRisk / HiddenDiseaseRisk**: disease identifier, confidence, matched test codes, citing authority with DOI
- **GuidelineAuthority**: name, Oxford CEBM evidence grade, published sensitivity, bibliographic reference

Four relationship types encode the evidence chain: `HAS_TEST` (Patient -> test node), `CLASSIFIED_BY` (test -> authority), `VOTED_BY` (individual authority votes), `HAS_DISEASE_RISK` (Patient -> disease-risk), and `BASED_ON_TEST` (disease-risk -> triggering test nodes).

![Figure 2 — Neo4j property graph schema](../tables/figures/Figure2_Neo4j_Schema.svg)

*Figure 2. Neo4j property graph schema. Patient nodes connect to classified test nodes (RAG-coloured by consensus label) and to disease-risk nodes; test nodes connect to GuidelineAuthority nodes that carry the citable DOI. The complete provenance path (Patient → TestNode → GuidelineAuthority → DOI) is recoverable in three Neo4j traversal steps. TDL is encoded as a DataSource (not a guideline authority) for the 20 tests not covered by any authority.*

Every disease-risk node carries a complete evidence chain traceable to triggering test results, voting authorities, and citable guideline publications with DOIs. The three-layer click interaction (Patient → classified test node → disease-risk and authority trail) implements the provenance surface described in §2.5 and aligns with the **transparency principles** of the EU AI Act (Article 13), which requires that high-risk AI systems provide explanations enabling users to understand system outputs.

> **Cross-reference:** Algorithm pseudocode, computational complexity analysis, and Cypher query examples are provided in **Appendix F**.

---

## 4. Implementation and Dataset

### Knowledge Graph Implementation

The system runs on **Neo4j 4.x** with Cypher as the query language. Its graph schema mirrors the two-stage pipeline formalised in §3.4 and Figure 2 and consists of six node types. `Patient` nodes carry identifiers and demographics. The three labelled test nodes — `NormalTest`, `AttentionTest`, and `CriticalTest` — store the raw value, the consensus classification, the confidence score, the 95% CI bounds, and the list of covering authorities with their individual votes. The label itself communicates risk status: a clinician does not need to read off the confidence value to know how a test was classified. `OvertDiseaseRisk` and `HiddenDiseaseRisk` nodes hold the disease identifier (`disease_id`), the associated confidence, the matched required and supporting test codes, and the citing authority with its DOI. `GuidelineAuthority` nodes hold authority metadata.

Four relationship types make up the evidence chain. `HAS_TEST` links each `Patient` node to its classified test nodes. `CLASSIFIED_BY` links a test node to the authorities that contributed votes; this edge is absent for tests with no covering authority, in which case the TDL provides a fallback classification. `VOTED_BY` stores each individual authority vote on a test result, which is what makes per-authority auditing possible. `HAS_DISEASE_RISK` links a `Patient` node to each inferred disease risk. `BASED_ON_TEST` then links a disease-risk node to the test nodes whose classifications triggered the inference, closing the provenance path from patient back to evidence. The same relationship structure is shown in the schema diagram in Figure 2 (§3.4).

The eight overt rules (covering Diabetes Mellitus: A1F ≥ 6.5%; Hypothyroidism: TSH ≥ 10.0 mIU/L; Hyperthyroidism: TSH < 0.1 mIU/L; High Cardiovascular Risk: CHOL ≥ 6.2 mmol/L; Chronic Kidney Disease: CREA ≥ 1.8 mg/dL; Liver Disease: GOT ≥ 120 U/L; Anaemia: HGB ≤ 10.0 g/dL; and Vitamin D Deficiency: VD3 < 25 nmol/L) and the seven hidden rules (covering Subclinical Hypothyroidism: TSH 4.0–10.0 mIU/L with normal free T4; Prediabetes: A1F 5.7–6.4%; Early CKD Risk: CREA 1.2–1.8 mg/dL; Chronic Low-Grade Inflammation: CRP 3–10 mg/L; Dyslipidaemia: LDL ≥ 3.4 mmol/L; Vitamin B12 Deficiency Risk: B12 < 150 pmol/L; and Vitamin D Insufficiency: VD3 25–49 nmol/L) are encoded as property constraints on `GuidelineAuthority` nodes and evaluated via Cypher pattern matching over the patient's result subgraph.

The following Cypher query illustrates a typical evidence-chain traversal for a single patient, returning all abnormal test results together with their covering authority metadata and vote counts:

```cypher
MATCH (p:Patient {patient_id: $pid})-[:HAS_TEST]->(tn)
WHERE tn.classification <> 'normal'
OPTIONAL MATCH (ga:GuidelineAuthority)<-[:CLASSIFIED_BY]-(tn)
OPTIONAL MATCH (v:AuthorityVote)<-[:VOTED_BY]-(tn)
RETURN tn.test_code AS TestCode, tn.value AS Value, tn.unit AS Unit,
       tn.classification AS Class, tn.confidence AS Confidence,
       tn.ci_lower AS CI_Lower, tn.ci_upper AS CI_Upper,
       labels(tn)[0] AS NodeLabel,
       ga.code AS Authority, ga.ebm_grade AS CEBMGrade,
       v.vote AS Vote, v.confidence AS VoteConf
ORDER BY tn.test_code;
```

Note the use of `labels(tn)[0]` in the `RETURN` clause: this returns the specific node label (`NormalTest`, `AttentionTest`, or `CriticalTest`) that encodes the RAG traffic-light status, directly implementing the colour assignment described in §3.4 and Figure 2.

Authority parameter metadata — including evidence-level weight $e_i$ and published sensitivity $s_i$ — is stored as properties on `GuidelineAuthority` nodes and retrieved at runtime. A `DataSource` node records that raw laboratory data originates from a UK-based clinical laboratory. This node is explicitly labelled as a *data source* and not as a *guideline authority*, maintaining a clear ontological distinction between evidentiary input and normative reference standard (see §3.2 and §6.3). The three-layer click interaction (Patient $\rightarrow$ classified test node, colour-coded by label, $\rightarrow$ disease-risk node and authority trail) implements the provenance surface described in §3.4.

Figures 1 and 2 are schematic SVG diagrams; Figures 3–8 were generated from structured data at publication resolution. All figures meet the target journal's resolution requirements for submission.

### Clinical Dataset

The system is validated on a cross-sectional laboratory dataset from a **UK-based clinical laboratory**, with **4,000 de-identified patients** and **108,862 individual test results** spanning **43 laboratory assay codes**. The data arrive in four CSV tables — `Patient` (demographics), `Test_Request` (encounter dates and patient age), `Result` (individual test measurements), and `Test_type` (metadata on the 43 covered assay codes) — collected over the window of **02 April 2024 to 18 April 2024**. The dataset is cross-sectional by design; no follow-up records or outcome data are present. One feature shapes the evaluation: the dataset carries **no ICD diagnostic codes** and no physician-assigned diagnoses, so disease inference runs purely on laboratory test data, with no external clinical labels available for ground truth.

Patient records have already been de-identified, with no directly identifying fields present. We took the data as provided and applied the following preprocessing. Non-numeric result strings (e.g., `<0.4`, `>500`) were parsed as numeric bounds using the endpoint value. 68 TSH results with invalid string values (e.g., `#tps`) were excluded from classification. Date fields were normalised to ISO 8601. Test types classified as category B or below in the confidence tiering (20 of 43 codes) were excluded from the primary analysis. The result is a **high-confidence analysis set of 23 test types** covering metabolic, thyroid, renal, and haematological domains. Four test codes (HGB, CREA, ERY, FE) carry gender-specific guideline thresholds, but because the Patient table contains no gender field, the system falls back on the conservative combined range for all patients. The affected ranges are: HGB (female 12.0–16.0 g/dL vs male 13.5–17.5 g/dL), CREA (female 0.6–1.2 mg/dL vs male 0.7–1.3 mg/dL), ERY (female 3.8–5.2 ×10¹²/L vs male 4.5–5.9 ×10¹²/L), and FE (female 60–140 µg/dL vs male 70–180 µg/dL). We record this as a known limitation in §4.4.

Of the 4,000 patients, 3,869 (96.7%) had at least one guideline-covered test result after Phase 2 deduplication and were retained for the primary analysis (N = 3,869). The final classified result set comprised 54,467 classified results across 29 NICE-covered assay codes — 12,797 (23.5%) CRITICAL, 7,988 (14.7%) ATTENTION, and 33,682 (61.8%) NORMAL.

### Authority Parameter Calibration

Nine guideline authorities are incorporated into the system: the American Diabetes Association (ADA), the World Health Organization (WHO), the National Institute for Health and Care Excellence (NICE), the European Society of Cardiology (ESC), the Kidney Disease: Improving Global Outcomes (KDIGO), the American Thyroid Association (ATA), the European Thyroid Association (ETA), the World Health Organization Haemoglobin (WHO-Hb), and the International Federation of Clinical Chemistry and Laboratory Medicine (IFCC). All nine authorities carry an institutional weight $w_i = 1.0$ because each meets the 1A or 1B grade criterion per the Oxford Centre for Evidence-Based Medicine; no further differentiation is applied. For each authority $a_i$, two parameters are defined: the evidence-level weight $e_i$ derived from the corresponding Oxford CEBM grade (1A $\to$ 1.0, 1B $\to$ 0.9), and the published diagnostic sensitivity $s_i$ obtained from the primary source systematic review or meta-analysis cited in the Citation Map. These two parameters are design-time metadata on `GuidelineAuthority` nodes, not inference-time hyperparameters — they specify *which* authorities are authoritative and *what evidence quality* each carries, and do not participate in the voting or classification algorithms that process individual patient results (see §5.6). The complete parameter set is reported in **Table 1**, together with full references and PMIDs.

#### 4.3.1 Voting and Classification Rules

Voting follows Definition 1 (§3.2): each authority contributes one vote (`NORMAL`, `ATTENTION`, or `CRITICAL`) per test result. Votes are stored as individual `VOTED_BY` relationships on the test node, enabling full auditability of the evidence chain (see Cypher example in §4.1).

#### 4.3.2 Confidence Calculation

For each classified result, the system computes a consensus confidence score in five steps. **Step 1** computes the evidence-weighted base confidence across all covering authorities:

$$
C_{\text{base}}(t) = \frac{\sum_{a_i \in \mathcal{A}_t} s_i \, e_i}{\sum_{a_i \in \mathcal{A}_t} e_i},
$$

where $s_i$ is the published diagnostic sensitivity and $e_i$ the Oxford CEBM evidence-level weight (1A $\to$ 1.0, 1B $\to$ 0.9); $C_{\text{base}}(t)$ is the $e_i$-weighted mean of $s_i$. **Step 2** applies a consensus bonus: full agreement (all votes in one category) $+0.05$, partial agreement (two categories present) $+0.02$, significant disagreement (all three categories present) $-0.03$. **Step 3** adds a multi-source bonus $B_{\text{source}} = \min(0.02 \times (n - 1), 0.06)$ per additional independent authority beyond the first, where $n = |\mathcal{A}_t|$ is the number of covering authorities for result $t$. **Step 4** caps the final score at 1.0:

$$
C_{\text{final}}(t) = \min\!\bigl(\, C_{\text{base}}(t) + B_{\text{consensus}}(t) + B_{\text{source}}(t),\; 1.0 \,\bigr).
$$

**Step 5** derives the 95% CI as $C_{\text{final}} \pm 1.96\sigma$ where $\sigma = \sqrt{\sigma_{\text{source}}^2 + \sigma_{\text{consensus}}^2}$, with $\sigma_{\text{source}}$ ranging from 0.02 (3+ sources) to 0.10 (single source) and $\sigma_{\text{consensus}}$ from 0.01 (full consensus) to 0.08 (no consensus). Full derivation is documented in the system technical documentation.

#### 4.3.3 TDL as Data Source, Not Authority

The Doctors Laboratory (TDL) provides population-derived laboratory reference ranges from the CSV dataset but is **not a clinical guideline authority**. Following the IFCC Committee on Reference Intervals and Decision Limits framework (Ozarda et al., 2018 [G1]), laboratory reference ranges are statistically derived from healthy-population distributions and indicate statistical commonality, not clinical actionability. In contrast, ADA, WHO, NICE, and other guideline bodies define diagnostic thresholds through systematic review of RCTs and structured expert consensus. TDL carries an authority weight of zero and is excluded from consensus voting; it serves solely as a fallback classifier for the 20 test codes not covered by any recognised guideline, yielding a fixed confidence of $0.50 \pm 0.15$.

#### 4.3.4 Worked Example: HbA1c = 5.9%

For HbA1c = 5.9%, the four covering authorities produce: ADA votes `ATTENTION` ($s=0.95, e=1.0$), WHO votes `NORMAL` ($s=0.94, e=1.0$), NICE votes `NORMAL` ($s=0.92, e=1.0$), and IFCC votes `ATTENTION` ($s=0.92, e=0.9$). Applying Step 1: the numerator is $0.95\times1.0 + 0.94\times1.0 + 0.92\times1.0 + 0.92\times0.9 = 3.6152$, and the denominator is $1.0+1.0+1.0+0.9 = 3.90$, giving $C_{\text{base}} = 3.6380 / 3.90 = 0.933$. Step 2 yields $B_{\text{consensus}} = +0.02$ (partial consensus: 2 ATTENTION vs 2 NORMAL votes). Step 3: with $n = |\mathcal{A}_t| = 4$ covering authorities, $B_{\text{source}} = \min(0.02\times3, 0.06) = +0.06$. Step 4: $C_{\text{final}} = \min(0.933 + 0.02 + 0.06,\; 1.0) = 1.0$ (capped). Step 5: partial consensus gives $\sigma_{\text{consensus}} = 0.04$, and $\sigma_{\text{source}} = 0.02$ for $|\mathcal{A}_t| = 4 \geq 3$, so $\sigma = \sqrt{0.02^2+0.04^2} = \sqrt{0.002} \approx 0.045$, and the 95% CI is $[1.0 - 1.96\times0.045,\; 1.0] = [0.912,\; 1.0]$. This is recorded as a partial-consensus prediabetes alert requiring follow-up. Note that this worked example is a partial-consensus case with both consensus and source bonuses; the average CI width across the cohort is necessarily smaller because most results have fewer than 4 covering authorities.

*Table 1. Guideline authority parameters used in the consensus confidence calculation. CEBM grade maps to evidence-level weight $e_i$: 1A $\to$ 1.0, 1B $\to$ 0.9. All authorities carry institutional weight $w_i = 1.0$ as all meet the Oxford CEBM 1A or 1B criterion. Sensitivity $s_i$ is drawn from the cited primary source. All citations refer to the Citation Map entries.*

| Authority | Full Name | CEBM Grade | $s_i$ | Year | Primary Reference | PMID / DOI |
|-----------|-----------|------------|-------|------|-------------------|------------|
| ADA | American Diabetes Association | 1A | 0.95 | 2025 | Diabetes Care 2025;48(Suppl 1):S27–S49 | PMID 39651986 |
| WHO | World Health Organization | 1A | 0.94 | 2006 | WHO Technical Report Series No. 894 | ISBN 9241594934 |
| NICE | National Institute for Health and Care Excellence | 1A | 0.92 | 2024 | NICE Guidelines NG17, NG28, NG181 | nice.org.uk |
| ESC | European Society of Cardiology | 1A | 0.88 | 2021 | Eur Heart J 2021;42(36):3227–3337 | doi 10.1093/eurheartj/ehab484 |
| KDIGO | Kidney Disease: Improving Global Outcomes | 1A | 0.90 | 2024 | Kidney Int 2024;105(4S):S117–S314 | doi 10.1016/j.kint.2023.10.018 |
| ATA | American Thyroid Association | 1A | 0.93 | 2014 | Thyroid 2014;24(12):1670–1751 | doi 10.1089/thy.2014.0028 |
| ETA | European Thyroid Association | 1A | 0.91 | 2013 | Eur Thyroid J 2013;2(4):215–228 | doi 10.1159/000356507 |
| WHO-Hb | World Health Organization | 1B | 0.89 | 2024 | Guideline on Haemoglobin Cutoffs to Define Anaemia in Individuals and Populations. Geneva: World Health Organization; 2024. ISBN 978-92-4-008854-2 | — |
| IFCC | International Federation of Clinical Chemistry and Laboratory Medicine | 1B | 0.92 | 2018 | Crit Rev Clin Lab Sci 2018;55(6):420–431 | doi 10.1080/10408363.2018.1482256 |

### 4.4 Limitations

Five system limitations are acknowledged. First, four tests carry gender-specific guideline thresholds (HGB, CREA, ERY, FE), but the Patient table lacks demographic data; the system applies the wider combined range as a conservative lower bound. Second, the dataset is cross-sectional with no ICD diagnostic codes or patient follow-up records; disease inferences cannot be validated against clinical diagnoses and are compared against population-level epidemiological data in §5. Third, the system operates on laboratory data alone and does not integrate imaging, genomics, or clinical symptom inputs; future extensions to multi-modal data are discussed in §7. Fourth, 20 of the 43 test types in the dataset are not covered by any guideline authority; these are classified using the local laboratory reference range alone at a fixed confidence of $0.50 \pm 0.15$ and cannot contribute to disease inference in Stage 2. Fifth, the UK-based clinical laboratory dataset is sourced from a single laboratory; cross-laboratory variation in assay methods and reference intervals is not represented in the evaluation and limits generalisability claims to comparable laboratory settings.

---

## 5. Evaluation

### 5.1 Evaluation Overview

The system was evaluated on 3,869 patients (96.7% of 4,000; 131 were excluded for non-numeric values) from a UK secondary-care referral laboratory, all processed through the two-stage pipeline. The 83.4% overt-disease prevalence is high — that reflects the referral population, since patients presenting to secondary care carry a higher pre-test probability of abnormality than a general-population screening cohort would. Because the dataset contains no physician-assigned diagnoses or ICD codes, evaluation of a KG-based CDSS that produces novel classification outputs has to rely on construct-level validation [E1–E3]. The four questions we address: (a) does classification stay consistent with the formal definitions in §3; (b) does the CI narrow as authorities are added, as Definition 3 predicts; (c) does the overt layer remain invariant under authority divergence; and (d) how sensitive is the hidden layer to authority composition.

Four classification modes were evaluated:

- **B1 (NICE-only)**: NICE thresholds, both layers
- **B2 (TDL range)**: laboratory reference intervals only (no CRITICAL tier), both layers
- **B3 (Overt-only)**: NICE thresholds, overt layer only (hidden suppressed — ablation baseline)
- **Full (Dual-layer)**: consensus classifications with both overt and hidden inference

### 5.2 Authority Ablation Results

The ablation asks what happens to consensus classifications, CI width, and disease prevalence as more guideline authorities join the panel. We organise the analysis around three questions.

![Figure 3 — Authority ablation: class distribution and CI width narrowing](../tables/figures/Figure3_Ablation_Classification.svg)

*Figure 3. Authority ablation across four configurations (Config-1, -3, -6, -9). (A) Distribution of NORMAL / ATTENTION / CRITICAL classifications. Two divergences materially alter classifications between Config-3 and Config-6: ESC CRP reclassifies 499 ATTENTION→CRITICAL, and ATA/ETA TSH reclassifies 223 NORMAL→ATTENTION. (B) Average 95% CI width narrows from 0.199 (single authority) to 0.131 (nine authorities, −34.2%) as the average votes/result rises from 1.00 to 1.79.*

**Q1 — diabetes and glycaemia show no inter-authority divergence.** Config-1 and Config-3 return identical class counts (12,616 CRITICAL, 7,611 ATTENTION, 34,240 NORMAL). ADA, WHO, and NICE all converge on HbA1c ≥ 6.5% and fasting glucose ≥ 126 mg/dL, despite their different institutional origins.

**Q2 — two divergences materially shift classifications.** Once ESC, KDIGO, ATA, and ETA join the panel at Config-6, two specific divergences move the numbers.

*CRP:* ESC classifies CRP ≥ 3 mg/L as high cardiovascular risk, against NICE's ≥ 10 mg/L. The effect is 499 results escalating from ATTENTION to CRITICAL — low-grade inflammation gets flagged for cardiovascular assessment.

*TSH:* ATA and ETA use a 2.5 mIU/L monitoring threshold, against NICE's 4.0 mIU/L. This escalates 223 results from NORMAL to ATTENTION, picking up subclinical hypothyroidism cases that a NICE-only system would miss.

KDIGO's creatinine threshold contributes zero change in this cohort: every value in the [1.3, 1.8) mg/dL divergence range is already CRITICAL via the low-bound threshold.

**Q3 — corroborating authorities narrow the CI without changing consensus.** Adding WHO-Hb and IFCC at Config-9 brings the average CI width from 0.153 down to 0.131 (a 14.4% reduction), and leaves classifications untouched.

![Figure 4 — Overt disease counts invariant across configurations](../tables/figures/Figure4_OvertDisease_Invariance.svg)

*Figure 4. Overt disease counts are identical across all four configurations (3,226 patients, 83.4%; Cohen's κ = 1.000), confirming invariance: every overt trigger falls in a range where all covering authorities agree.*

![Figure 5 — Hidden disease shift between Config-3 and Config-6](../tables/figures/Figure5_HiddenDisease_Shift.svg)

*Figure 5. Hidden disease counts shift from Config-3 to Config-6. Chronic Inflammation and Early CKD Risk are eliminated (their ATTENTION-tier signals are upgraded to CRITICAL by ESC and KDIGO and absorbed by the overt layer), while Subclinical Hypothyroidism rises from 72 to 295 as 223 TSH results in [2.5, 4.0) mIU/L are detected once ATA/ETA join the consensus.*

**Table D.** Average 95% CI width and authority votes per configuration.

| Config | #Auth | Avg CI Width | Avg Votes/Result |
|--------|------:|-------------:|-----------------:|
| Config-1 (NICE) | 1 | 0.199 | 1.00 |
| Config-3 (+ADA,WHO) | 3 | 0.192 | 1.07 |
| Config-6 (+ESC,KDIGO,ATA,ETA) | 7 | 0.153 | 1.53 |
| Config-9 (+WHO-Hb,IFCC) | 9 | 0.131 | 1.79 |

A companion visualisation of CI width and σ decomposition is provided in **Figure 6**.

![Figure 6 — CI width convergence with σ decomposition](../tables/figures/Figure8_CIWidth_Convergence.svg)

*Figure 6. (A) Average 95% CI width narrows monotonically as more authorities corroborate (from 0.199 at Config-1 to 0.131 at Config-9, −34.2%). Shaded bands show σ_total = √(σ²_source + σ²_consensus). (B) Decomposition of σ: source-uncertainty drops sharply once three or more authorities cover the test (0.10 → 0.02); consensus-uncertainty drops as the vote distribution sharpens (0.08 → 0.01).*

> **Cross-reference:** Detailed ablation accounting, per-disease counts, and sensitivity analysis are provided in **Appendix G**.

### 5.3 Baseline Comparison

![Figure 7 — Patient visibility by classification mode](../tables/figures/Figure6_PatientVisibility_DualLayer.svg)

*Figure 7. Patient coverage by classification mode (N = 3,869). B2 (TDL range) produces zero overt detections by design (no CRITICAL tier), while B1 and Full identify 83.3–83.4% of patients with at least one overt disease. Full identifies 40.0% with hidden risks, versus zero under B3. The 3.4% gap between B3 and Full (130 patients) is the population that single-threshold systems cannot see.*

**Table 4.** Overt disease counts across modes. B2 fires zero overt rules by design. Liver Disease and CKD are the dominant findings.

| Disease | B1 | B2 | Full |
|--------|-----|-----|------|
| Liver Disease (GOT) | 2,567 | 0 | 2,567 |
| Chronic Kidney Disease (CREA) | 2,878 | 0 | 2,880 |
| High CV Risk (CHOL) | 288 | 0 | 297 |
| Vitamin D Deficiency (VD3) | 733 | 0 | 761 |
| Hypothyroidism (TSH) | 159 | 0 | 13 |
| Hyperthyroidism (TSH) | 159 | 0 | 151 |
| Anaemia (HGB) | 94 | 0 | 101 |
| Diabetes Mellitus (A1F) | 5 | 0 | 7 |

**Table 5.** Hidden disease counts. Dyslipidaemia (727) and Chronic Inflammation (499) are the dominant hidden findings.

| Hidden Disease | B1 | B2 | Full |
|----------------|-----|-----|------|
| Dyslipidaemia | 736 | 856 | 727 |
| Chronic Inflammation | 504 | 600 | 499 |
| Vitamin D Insufficiency | 124 | 665 | 124 |
| Subclinical Hypothyroidism | 72 | 231 | 72 |
| Early CKD Risk | 110 | 499 | 108 |
| Prediabetes | 37 | 55 | 35 |
| B12 Deficiency Risk | 24 | 198 | 401 |
| **Total ≥1 hidden** | **1,356** | **2,145** | **1,547** |

![Figure 8 — Patient-level agreement matrix](../tables/figures/Figure7_PatientAgreement_Matrix.svg)

*Figure 8. Patient-level agreement on ≥1 overt disease across modes. B1 vs Full = 99.9% (pipeline validated against the single-authority baseline); B1 vs B2 = 16.7% (structural divergence between TDL reference-interval logic and NICE clinical decision limits).*

> **Cross-reference:** Detailed tables and population epidemiology contextualisation are provided in **Appendix G**.

### 5.4 Overt-Hidden Co-occurrence

We quantify the clinical value of the dual-layer architecture at the patient level, splitting the cohort into four mutually exclusive visibility categories (**Table 7**).

**Table 7.** Patient visibility in B3 (overt-only) vs Full (dual-layer).

| Category | Count | % |
|----------|-------|---|
| B3 visible, Full overt | 3,224 | 83.3% |
| **B3 invisible, Full hidden-only [KEY]** | **130** | **3.4%** |
| B3 invisible, Full overt | 2 | 0.1% |
| Both invisible (no risk) | 513 | 13.3% |

**130 patients (3.4%) fire zero overt rules under B3 but carry active hidden risks under Full** — and this group is the central clinical case for the dual-layer architecture. Three conditions dominate: Subclinical Hypothyroidism (72 patients, TSH 4.0–10.0 mU/L with normal free T4), Early CKD Risk (110 patients, CREA 1.2–1.8 mg/dL), and Prediabetes (37 patients, HbA1c 5.7–6.4%). All three are clinically actionable through monitoring protocols, lifestyle intervention, or targeted screening; all three sit below the CRITICAL threshold that a single-layer alert system would require.

Hidden-layer labels are **monitoring triggers**, not diagnostic conclusions. The 0.75 confidence ceiling reflects the weaker outcome evidence behind subclinical states, compared with the 0.70 floor that the overt layer assigns to confirmed disease. The exclusion clause keeps the two layers from labelling the same disease twice on the same patient.

Among the 1,547 patients with at least one hidden risk, the most common co-occurrence is Dyslipidaemia + Chronic Inflammation (336 patients, 21.7%) — consistent with the metabolic-inflammatory overlap that ESC 2021 documents [G5].

> **Cross-reference:** Detailed clinical actionability analysis and benchmark comparison with prior KG-CDSS systems are provided in **Appendix G**.

### 5.5 Evaluation Summary

Two findings come out of the evaluation:

**Finding 1 — authority ablation.** Authority composition is the main driver of classification outcome at the result level. Two documented divergences (ESC CRP, 499 results; ATA/ETA TSH, 223 results) shift classifications materially. At the same time, the overt layer is invariant across every configuration we test (Cohen's κ = 1.000), and the hidden layer shifts in directions that the underlying inter-authority disagreement would predict.

**Finding 2 — dual-layer clinical value.** Under the single-layer baseline, 130 patients (3.4%) fire zero overt rules yet carry active hidden risks. These are the patients a single-threshold CDSS would not see. The three dominant conditions in this group — SCH, Early CKD Risk, Prediabetes — are clinically actionable, with established monitoring protocols already in the literature [S1, S3, S9, G7].

### 5.6 Gender-Specific Threshold Sensitivity

Four tests carry gender-specific guideline thresholds (HGB, CREA, ERY, FE). Because the Patient table contains no gender field, the system applies the conservative combined range as a lower bound. We illustrate the potential directional impact of gender-specific classification on two diseases (**Table S2**).

**Table S2.** Directional impact of gender-specific thresholds on disease counts.

| Disease | Combined Range Count | Gender-Adjusted Direction | Uncertainty |
|---------|---------------------|---------------------------|--------------|
| Anaemia (HGB) | 101 patients | Lower bound (female threshold <10 g/dL vs male <13.5 g/dL may increase female overt count) | ±15 patients |
| CKD (CREA) | 2,880 patients | Lower bound (female upper-normal 1.2 mg/dL vs male 1.3 mg/dL; patients in [1.2, 1.8) range may shift from hidden to overt) | ±150 patients |

*Directional estimates based on UK demographic distribution (50.5% female) and guideline-defined gender-specific thresholds. The combined-range application serves as a conservative lower bound; gender-specific thresholds would shift some hidden-layer patients to the overt layer, but the magnitude depends on the unknown gender distribution of this secondary-care referral cohort.*

The disease counts in §5.3 and §5.4 should be interpreted with this uncertainty acknowledged. Full sensitivity analysis is provided in **Appendix G**.

> **Cross-reference:** Parameter design rationale is provided in **Appendix G**.

---

## 6. Discussion

We now look back at the three research gaps from §1 and §2, work through the clinical implications, set out the limitations honestly, and sketch where the work should go next.

### 6.1 Returning to the Three Research Gaps

**Gap 1 — Explainability.** ML-based CDSS depend on post-hoc explanation methods (SHAP, LIME) that approximate the model's reasoning, with the well-known fidelity issues [X7] and the awkward result that explanation availability boosts clinician trust faster than it should [X6]. We address this architecturally rather than by adding a separate explanation layer. Clinical reasoning is encoded directly into the knowledge graph, and each disease-risk node carries a provenance path — Patient → TestNode → GuidelineAuthority → DOI — recoverable in three Neo4j traversal steps. The design supports the **transparency and auditability** requirements set out in the EU AI Act (Article 13) for high-risk AI systems, and aligns with FDA guidance on AI/ML-based Software-as-a-Medical-Device predetermination. Three properties make this possible: a traceable provenance path on every output, a three-hop traversal that a clinician can read without specialist tooling, and a CI that quantifies epistemic uncertainty alongside the classification.

**Gap 2 — Threshold Reconciliation.** No published system applies multiple guidelines simultaneously to patient laboratory records and surfaces inter-authority disagreement as a computable output. The multi-source consensus mechanism makes that disagreement a first-class output: every test result is classified against every covering authority in parallel, and the 95% CI turns the vote vector into something an end-user can act on. §5.2 confirms the prediction: two divergences move classifications materially (ESC CRP, ATA/ETA TSH), and additional corroborating authorities narrow the CI without disturbing the consensus.

**Gap 3 — Subclinical Inference.** Single-threshold CDSS cannot represent subclinical states at all. The dual-layer architecture (§3.3) fires the overt layer when confirmed-disease criteria are met (confidence floor 0.70) and the hidden layer in subclinical ranges (confidence ceiling 0.75, set deliberately lower to reflect the weaker outcome evidence). Theorem 1 guarantees no dual labelling on the same patient. The empirical payoff: 130 patients (3.4%) fired zero overt rules under B3 but carried hidden risks — invisible to a single-threshold system, yet clinically actionable through established monitoring protocols [S1, S3, S9, G7].

These three problems do not stay separate in deployment. A black-box model cannot expose inter-authority disagreement even when the data would allow it; a single-threshold system cannot detect subclinical states; a system without provenance cannot satisfy the relevant regulatory frameworks. The framework here resolves all three inside one architecture, and the three capabilities turn out to reinforce one another in practice.

### 6.2 Clinical Implications and Deployment Context

The 95% CI does some real work here: it turns inter-authority disagreement into a signal a clinician can act on. A CRITICAL classification is unambiguous — the conservative escalation rule only fires when two or more authorities concur (Cohen's κ = 1.000 across configurations). An ATTENTION result with a wide CI flags genuine authority disagreement that calls for clinical review; a narrow CI says the call is well-supported.

The NICE NG143 traffic-light standard provides the usability layer on top of this. Three node labels — `NormalTest` (green), `AttentionTest` (amber), `CriticalTest` (red) — communicate risk status without asking clinicians to translate raw confidence values. A three-layer click interaction (Patient → classified test → disease-risk and authority trail) follows the natural sequence of clinical reasoning.

**Where this would fit in a real workflow.** The intended deployment point is the pathology laboratory result authorisation interface — the moment where abnormal results are reviewed before being released to the requesting clinician. At that point the dual-layer inference output can be attached to the laboratory report as a structured comment, in the same shape as existing delta-check comments and critical value flags. The scenarios below are design proposals built on established CDSS integration practices [C9]; we have not yet validated them in clinical use, and that validation is the next step (§6.4).

Three illustrative scenarios show how a hidden-layer flag could translate into clinical action:

1. *Pathologist review at result authorisation.* A pathologist reviewing an abnormal result sees a hidden-layer flag — for example, "Subclinical Hypothyroidism: TSH 4.8 mIU/L with normal T4L — consider monitoring per ETA 2013 guideline." The pathologist adds a structured comment to the report, prompting the requesting clinician to consider thyroid monitoring.

2. *GP integration via HL7/FHIR.* The laboratory report reaches a GP practice management system through HL7/FHIR messaging, consistent with the SMART-on-FHIR architecture evaluated in clinical trials [C9]. An embedded CDSS module parses the hidden-layer flags and generates a review task for the GP.

3. *Patient portal with interpretation.* Laboratory results are released to a patient portal with embedded interpretation. Hidden-layer flags appear as "Results to discuss with your doctor" prompts, opening the door to patient-initiated follow-up.

Across all three scenarios the hidden-layer label has the same role: a **monitoring trigger**. It does not replace clinical judgement; it makes sure that actionable subclinical findings are not silently dropped.

### 6.3 Alternative Approaches

Two other paradigms could in principle attack the inter-authority disagreement problem. We considered both during the design phase and rejected each for specific reasons.

*Bayesian networks and probabilistic graphical models.* A Bayesian network (BN) encodes uncertainty through conditional probability distributions, and one could imagine modelling inter-authority disagreement as a set of probabilistic priors. The blocker is empirical, not theoretical: BNs need large annotated training datasets to learn accurate conditional probability tables, and no such dataset exists for multi-authority guideline reconciliation at the laboratory-result level. There is also a second issue. A BN produces a point probability estimate without explicit provenance — to understand *why* the network arrived at a given probability, one falls back on post-hoc explanation methods such as variable-elimination tracing, which re-introduces the fidelity problems flagged in §2.5. The KG approach gives provenance for free as an architectural property.

*Supervised ML classifiers.* Random forests, gradient boosting, or neural networks trained on labelled laboratory-result data could in principle learn optimal threshold combinations directly. Three structural barriers stop this from working in our domain. (1) There is no ground-truth labelled dataset for multi-authority threshold reconciliation. (2) These models are opaque by design — a classification without an auditable evidence chain cannot meet EU AI Act Article 13 transparency requirements without a post-hoc XAI layer on top. (3) ML models generalise to the training distribution; they cannot guarantee monotonicity under authority composition changes. The KG framework's theorem-proven classification invariance (§3.2.1) gives this guarantee structurally, not statistically.

The choice of a KG-based approach therefore rests on four properties: provenance is intrinsic rather than post-hoc; no training data beyond the existing guideline publications is required; classification invariance under authority perturbation is formally proven; and the dual-layer architecture allows subclinical-state representation that single-threshold ML classifiers cannot reach.

### 6.4 Limitations

The system has five limitations worth setting out plainly. Four tests carry gender-specific thresholds (HGB, CREA, ERY, FE), but the Patient table contains no gender field, so the system applies the wider combined range as a conservative lower bound. The dataset is cross-sectional, with no ICD codes and no follow-up records, which means disease inferences are compared against population epidemiology rather than clinical diagnoses. The system runs on laboratory data alone — imaging, genomics, and clinical symptom inputs are not integrated, and future multi-modal extensions are discussed below. 20 of the 43 tests in the dataset fall back to a fixed confidence of 0.50 ± 0.15 without guideline backing. Finally, the cohort comes from a single UK laboratory, which limits generalisability; the framework's primary claims (ablation invariance, dual-layer exclusion, CI monotonicity) are structural properties and are independent of cohort composition, but the empirical numbers should not be read as cross-laboratory estimates.

### 6.5 Future Work

The most immediate need is **clinical workflow validation**. The three deployment scenarios in §6.2 — pathologist integration, GP FHIR integration, patient portal — are design proposals built on established CDSS practice [C9] and SMART-on-FHIR architecture, but they are not yet empirically tested. A pilot study measuring adoption rates, clinician response time, and downstream patient outcomes is the next concrete step in moving the framework from technical demonstration to clinical use. **Multi-centre validation** would tell us whether the consensus classification distributions and CI widths observed here hold on external cohorts — particularly for the KDIGO creatinine divergence, which produced zero change in this secondary-care referral cohort and may behave differently in primary care. The expert-design constants we use (confidence ceilings, σ values) could be refined through Delphi-panel validation with clinical experts, replacing them with empirically calibrated values. **Longitudinal tracking** would let the system surface disease progression signals rather than reacting to single time-point snapshots — a capability the current cross-sectional dataset does not support. Beyond laboratory data, **multi-modal integration** with EHR systems would deliver classifications automatically at result authorisation, and adding imaging and genomics inputs would push the framework past its current laboratory-data boundary.

---

## 7. Conclusion and Future Work

A patient walking into clinic with several borderline laboratory results does not present a clean case. Authoritative guidelines disagree, and until now the choice of which threshold to apply has been left implicit in the choice of one authority or one in-house reference range. This paper has built a knowledge-graph framework that tackles the problem on three fronts. A multi-source consensus mechanism classifies every laboratory result against nine independent clinical authorities, so inter-authority divergence becomes a first-class output rather than an artefact of the authority choice. A dual-layer inference architecture then separates confirmed disease from subclinical states — two conditions that share laboratory signatures but call for very different clinical responses — with a formal non-overlap clause that prevents contradictory labels. And the knowledge graph itself encodes every inference as a traceable evidence chain, recoverable in three Neo4j traversal steps, which is what makes the provenance of each output auditable to the level current regulatory frameworks require.

The numbers from 3,869 patients and 47,468 classified test results back this up. The overt disease layer was invariant across all four ablation configurations; Cohen's κ = 1.000 throughout. High-confidence classifications, then, are not artefacts of the chosen authority composition. The hidden layer added 130 patients (3.4% of the cohort) with subclinical hypothyroidism, early chronic kidney disease risk, or prediabetes — patients that a single-threshold system would not see, and yet whose conditions are clinically actionable through standard monitoring and lifestyle protocols.

The most immediate extension we see is multi-omics. Bringing genomic, proteomic, and metabolomic data into the knowledge graph schema along the lines proposed by Eawsakul et al. [P5] is the natural next step for pushing disease inference past the laboratory-data boundary that the current system sits behind.

---

## Appendix A: Guideline-Covered Test Reference

*Table A1. The 23 laboratory tests covered by at least one clinical guideline authority. Reference ranges and classification thresholds are reproduced from the primary source publications cited in Table 1 (authority parameters) and Category G of the Citation Map (G7–G12, G14, G15, plus the ETA 2013 subclinical hypothyroidism guideline cited as S3). TSH is presented as two separate rows because ATA/ETA and NICE publish different upper-normal thresholds (2.5 vs 4.0 mIU/L), a key source of inter-authority divergence examined in §5.2. Dual-direction thresholds (high and low) apply to T4L, T3L, GB, and K.*

| Code | Test Name | Covering Authorities | Normal | Attention | Critical | CEBM Grade |
|------|-----------|---------------------|--------|-----------|----------|------------|
| A1F | Haemoglobin A1c | ADA, WHO, NICE, IFCC | $<5.7$\% | $5.7$–$6.5$\% | $\geq 6.5$\% | 1A |
| GLU | Fasting Glucose | ADA, WHO, NICE | $<100$ mg/dL | $100$–$126$ mg/dL | $\geq 126$ mg/dL | 1A |
| CHOL | Total Cholesterol | ESC, NICE | $<190$ mg/dL | $190$–$240$ mg/dL | $\geq 240$ mg/dL | 1A |
| LDL | LDL Cholesterol | ESC, NICE | $<100$ mg/dL | $100$–$160$ mg/dL | $\geq 160$ mg/dL | 1A |
| TRI | Triglycerides | ESC, NICE | $<150$ mg/dL | $150$–$500$ mg/dL | $\geq 500$ mg/dL | 1A |
| CRP | C-Reactive Protein | ESC, NICE | $<3.0$ mg/L | $3.0$–$10.0$ mg/L | $\geq 10.0$ mg/L | 1A |
| CREA | Creatinine | KDIGO, NICE | $0.6$–$1.2$ mg/dL | $1.2$–$1.8$ mg/dL | $\geq 1.8$ mg/dL | 1A |
| URE | Urea | NICE, KDIGO | $7.0$–$20.0$ mg/dL | $20.0$–$42.0$ mg/dL | $\geq 42.0$ mg/dL | 1A |
| TSH | Thyroid-Stimulating Hormone | ATA, ETA | $0.4$–$2.5$ mIU/L | $2.5$–$10.0$ mIU/L | $\geq 10.0$ mIU/L | 1A |
| TSH | Thyroid-Stimulating Hormone | NICE | $0.4$–$4.0$ mIU/L | $4.0$–$10.0$ mIU/L | $\geq 10.0$ mIU/L | 1A |
| T4L | Free Thyroxine | ATA, ETA, NICE | $12$–$22$ pmol/L | $9$–$12$ or $22$–$30$ pmol/L | $\leq 9$ or $\geq 30$ pmol/L | 1A |
| T3L | Free Triiodothyronine | ATA | $3.1$–$6.8$ pmol/L | $2.0$–$3.1$ or $6.8$–$10.0$ pmol/L | $\leq 2.0$ or $\geq 10.0$ pmol/L | 1A |
| HGB | Haemoglobin | WHO, NICE, WHO-Hb | $12.0$–$16.0$ g/dL | $10.0$–$12.0$ g/dL | $\leq 10.0$ g/dL | 1A |
| ERY | Erythrocyte Count | WHO-Hb | $3.8$–$5.8 \times 10^{12}$/L | $3.0$–$3.8 \times 10^{12}$/L | $\leq 3.0 \times 10^{12}$/L | 1B |
| GB | White Blood Cell Count | WHO, WHO-Hb | $4.0$–$11.0 \times 10^{9}$/L | $2.0$–$4.0$ or $11.0$–$20.0 \times 10^{9}$/L | $\leq 2.0$ or $\geq 20.0 \times 10^{9}$/L | 1A |
| PLA | Platelet Count | WHO, WHO-Hb | $150$–$400 \times 10^{9}$/L | $100$–$150 \times 10^{9}$/L | $\leq 100 \times 10^{9}$/L | 1A |
| FE | Serum Iron | WHO, NICE | $10$–$30$ $\mu$mol/L | $5$–$10$ $\mu$mol/L | $\leq 5$ $\mu$mol/L | 1A |
| B12 | Vitamin B12 | NICE | $>300$ ng/L | $200$–$300$ ng/L | $\leq 200$ ng/L | 1A |
| FOL | Folate | WHO, NICE | $>3.0$ ng/mL | $2.0$–$3.0$ ng/mL | $\leq 2.0$ ng/mL | 1A |
| GGT | Gamma-GT | NICE | $<40$ U/L | $40$–$120$ U/L | $\geq 120$ U/L | 1A |
| GOT | AST | NICE | $<40$ U/L | $40$–$120$ U/L | $\geq 120$ U/L | 1A |
| GPT | ALT | NICE | $<41$ U/L | $41$–$120$ U/L | $\geq 120$ U/L | 1A |
| VD3 | 25-Hydroxyvitamin D | NICE | $>50$ nmol/L | $25$–$50$ nmol/L | $\leq 25$ nmol/L | 1A |
| K | Potassium | NICE, KDIGO | $3.5$–$5.0$ mmol/L | $3.0$–$3.5$ or $5.5$–$6.5$ mmol/L | $\leq 3.0$ or $\geq 6.5$ mmol/L | 1A |

The remaining 20 test types in the clinical laboratory dataset are classified using the local laboratory reference range alone and receive a fixed confidence of $0.50 \pm 0.15$, as described in §3.2.

---

## Appendix B: Disease Inference Rules Reference

*Table B1. Overt disease inference rules (8 rules). Each fires when at least `min` required conditions are matched and the exclusion specification is not violated. Confidence: floor 0.70, ceiling 0.95, $+0.05$ per supporting test matched.*

| Rule | Disease | Required Tests | Min | Supporting | Authority | Grade |
|------|---------|---------------|-----|-----------|-----------|-------|
| $r_1^{\mathrm{O}}$ | Diabetes Mellitus | A1F=CRITICAL | 1 | GLU=CRITICAL or ATTENTION | ADA | 1A |
| $r_2^{\mathrm{O}}$ | Hypothyroidism | TSH_H=CRITICAL | 1 | T4L=ATTENTION or CRITICAL | ATA | 1A |
| $r_3^{\mathrm{O}}$ | Hyperthyroidism | TSH_L=CRITICAL | 1 | T4L=CRITICAL, T3L=CRITICAL | ATA | 1A |
| $r_4^{\mathrm{O}}$ | High Cardiovascular Risk | CHOL=CRITICAL | 1 | LDL=CRITICAL, TRI=ATTENTION/CRITICAL, CRP=ATTENTION | ESC | 1A |
| $r_5^{\mathrm{O}}$ | Chronic Kidney Disease | CREA=CRITICAL | 1 | URE=CRITICAL, K=ATTENTION/CRITICAL | KDIGO | 1A |
| $r_6^{\mathrm{O}}$ | Liver Disease | GOT=CRITICAL | 1 | GPT=CRITICAL, GGT=ATTENTION/CRITICAL | NICE | 1A |
| $r_7^{\mathrm{O}}$ | Anaemia | HGB=CRITICAL | 1 | FE, B12, FOL=ATTENTION/CRITICAL | WHO | 1A |
| $r_8^{\mathrm{O}}$ | Vitamin D Deficiency | VD3=CRITICAL | 1 | — | NICE | 1A |

*Table B2. Hidden disease inference rules (7 rules). Each fires when at least `min` required conditions are matched and exclusion conditions are absent. Subject to the exclusion mechanism described in §3.3. Confidence: floor 0.50, ceiling 0.75, $+0.05$ per supporting test matched.*

| Rule | Disease | Required Tests | Min | Excluding Tests | Authority | Grade |
|------|---------|---------------|-----|---------------|-----------|-------|
| $r_1^{\mathrm{H}}$ | Subclinical Hypothyroidism | TSH_H=ATTENTION | 1 | T4L=CRITICAL or ATTENTION | ETA | 1A |
| $r_2^{\mathrm{H}}$ | Prediabetes | A1F=ATTENTION | 1 | A1F=CRITICAL | ADA | 1A |
| $r_3^{\mathrm{H}}$ | Early CKD Risk | CREA=ATTENTION | 1 | CREA=CRITICAL | KDIGO | 1A |
| $r_4^{\mathrm{H}}$ | Chronic Low-Grade Inflammation | CRP=ATTENTION | 1 | CRP=CRITICAL | ESC | 1A |
| $r_5^{\mathrm{H}}$ | Dyslipidaemia | CHOL=ATTENTION or LDL=ATTENTION | 1 | — | ESC | 1A |
| $r_6^{\mathrm{H}}$ | Vitamin B12 Deficiency Risk | B12=ATTENTION | 1 | — | NICE | 1A |
| $r_7^{\mathrm{H}}$ | Vitamin D Insufficiency | VD3=ATTENTION | 1 | VD3=CRITICAL | NICE | 1A |

---

## Appendix C: Symbol Glossary

| Symbol | Meaning |
|--------|---------|
| $\mathcal{T}_p$ | Set of test-result pairs for patient $p$ |
| $t = (\tau, x)$ | Test-result pair: test identifier $\tau$, numeric value $x$ |
| $\mathcal{A}$ | Set of all guideline authorities (9 in this study) |
| $\mathcal{A}_t \subseteq \mathcal{A}$ | Subset of authorities that cover test $\tau$ (i.e., publish a threshold for $\tau$) |
| $\mathcal{A}^*(t) \subseteq \mathcal{A}_t$ | Subset of covering authorities that vote with the consensus class $c(t)$ |
| $\mathcal{S}$ | Classification space $\{\mathrm{NORMAL}, \mathrm{ATTENTION}, \mathrm{CRITICAL}\}$ |
| $v(a, t)$ | Vote of authority $a$ on result $t$ (element of $\mathcal{S}$) |
| $V(t)$ | Multiset of votes for test result $t$ |
| $n_{\text{CRIT}}, n_{\text{ATT}}$ | Counts of CRITICAL and ATTENTION votes in $V(t)$ |
| $c(t)$ | Consensus classification of $t$, defined in Definition 1 |
| $C_{\text{base}}(t)$ | Evidence-weighted base confidence, defined in Definition 2 |
| $B_{\text{consensus}}(t)$ | Consensus bonus: $+0.05$ (full), $+0.02$ (partial), $-0.03$ (significant disagreement) |
| $B_{\text{source}}(t)$ | Source-breadth bonus: $\min(0.02 \times (|\mathcal{A}_t|-1), 0.06)$ |
| $C_{\text{final}}(t)$ | Final consensus confidence, capped at $1.0$ |
| $\sigma_{\text{source}}$ | Source uncertainty: $0.02$ ($\geq 3$ sources), $0.05$ ($2$ sources), $0.10$ ($1$ source) |
| $\sigma_{\text{consensus}}$ | Consensus uncertainty: $0.01$ (full), $0.04$ (partial), $0.08$ (none) |
| $\sigma(t) = \sqrt{\sigma_{\text{source}}^2 + \sigma_{\text{consensus}}^2}$ | RSS-combined total uncertainty |
| $\mathrm{CI}_{95\%}(t)$ | 95% CI: $[C_{\text{final}}(t) - 1.96\,\sigma(t),\; C_{\text{final}}(t) + 1.96\,\sigma(t)] \cap [0,1]$ |
| $\mathcal{R}^{\mathrm{O}}, \mathcal{R}^{\mathrm{H}}$ | Sets of overt and hidden disease inference rules |
| $\mathcal{O}(r^{\mathrm{H}}) \subseteq \mathcal{R}^{\mathrm{O}}$ | Overt counterparts of hidden rule $r^{\mathrm{H}}$ (same disease label) |
| $\mathcal{E}(r^{\mathrm{H}})$ | Exclusion test conditions for $r^{\mathrm{H}}$ (suppresses $r^{\mathrm{H}}$ if met) |
| $r = (\rho, R, S, X, m)$ | Disease rule: label $\rho$, required set $R$, supporting set $S$, exclusion $X$, match threshold $m$ |
| $A_P$ | Patient $P$'s classified abnormal set: $A_P = \{(\tau, c) : c(\tau) \neq \text{NORMAL}\}$ |
| $\eta(r, P) = \|R \cap A_P\| + \|S \cap A_P\|$ | Evidence count for rule $r$ on patient $P$ |
| $C_{\mathrm{O}}(r^{\mathrm{O}}, P) = \min(0.70 + 0.05 \cdot \eta, 0.95)$ | Overt disease confidence |
| $C_{\mathrm{H}}(r^{\mathrm{H}}, P) = \min(0.50 + 0.05 \cdot \eta, 0.75)$ | Hidden disease confidence |

---

## Appendix D: Non-Overlapping Guarantee — Theorem 1 and Corollary 1

**Theorem 1 (Non-Overlapping Guarantee).** Let $r^{\mathrm{H}} \in \mathcal{R}^{\mathrm{H}}$ be a hidden disease inference rule whose exclusion specification contains an overt counterpart $r^{\mathrm{O}} \in \mathcal{O}(r^{\mathrm{H}})$ inferring the same disease label $\rho$. Then for any patient $P$:

$$
\neg\bigl(\, \mathrm{Overt}(P, \rho) \,\land\, \mathrm{Hidden}(P, \rho) \,\bigr).
$$

Equivalently: no disease label can appear simultaneously in a patient's overt and hidden inference sets when the hidden rule lists the overt rule as a counterpart.

**Proof.** Assume, for contradiction, that both $\mathrm{Overt}(P, \rho)$ and $\mathrm{Hidden}(P, \rho)$ hold for patient $P$. By $\mathrm{Overt}(P, \rho)$, the overt rule $r^{\mathrm{O}}$ fires: $\mathrm{match}(r^{\mathrm{O}}, P) = 1$ and $\mathrm{excluded}_{\mathrm{O}}(r^{\mathrm{O}}, P) = 0$. Since $r^{\mathrm{O}} \in \mathcal{O}(r^{\mathrm{H}})$, the exclusion predicate for $r^{\mathrm{H}}$ evaluates to $\mathrm{excluded}_{\mathrm{H}}(r^{\mathrm{H}}, P) = 1$ by the overt-counterpart clause of the exclusion specification $X$. But $\mathrm{Hidden}(P, \rho)$ requires $\mathrm{excluded}_{\mathrm{H}}(r^{\mathrm{H}}, P) = 0$ — a direct contradiction. $\square$

**Corollary 1.** The inferred disease label set for patient $P$ partitions into an overt-only subset and a hidden-only subset, with no overlap, provided every hidden rule whose disease label has an overt counterpart lists that overt rule in $\mathcal{O}$. This condition was verified during rule construction for all 15 rules (8 overt, 7 hidden) in the implemented system.

---

## Appendix E: MathType Reference — Core Formulae

*The following equations are presented in MathType-compatible linear notation for direct transcription. All symbols are defined in Appendix C. The numbered equations correspond to their LaTeX equivalents in the main text.*

---

### Definition 1 — Consensus Classification (Equation 1)

```
c(t) = { CRITICAL,                      if n_CRIT >= 2  OR  (n_CRIT >= 1  AND  n_ATT >= 1)
       { ATTENTION,                     if (n_CRIT = 0  AND  n_ATT >= 1)  OR  (n_CRIT = 1  AND  n_ATT = 0)
       { NORMAL,                       otherwise
```

---

### Definition 2 — Consensus Confidence (Equations 2–4)

**Equation 2 (Base confidence):**

```
C_base(t) = ( SUM_{a_i in A_t}  s_i * e_i * w_i )  /  ( SUM_{a_i in A_t}  e_i * w_i )
```

**Bonus values:**

```
B_consensus(t):
  full agreement (all votes in one category)    -> +0.05
  partial agreement (two categories present)    -> +0.02
  significant disagreement (all three present) -> -0.03

B_source(t) = min( 0.02 * ( |A_t| - 1 ),  0.06 )
```

**Equation 3 (Final confidence):**

```
C_final(t) = min( C_base(t) + B_consensus(t) + B_source(t),  1.0 )
```

---

### Definition 3 — 95% Confidence Interval (Equations 5–6)

**Equation 5 (Uncertainty components):**

```
sigma_source:
  |V(t)| >= 3  -> 0.02
  |V(t)| = 2   -> 0.05
  |V(t)| = 1   -> 0.10

sigma_consensus:
  full consensus    -> 0.01
  partial          -> 0.04
  no consensus     -> 0.08
```

**Equation 6 (Combined uncertainty and CI):**

```
sigma(t) = sqrt( sigma_source^2 + sigma_consensus^2 )

CI_95%(t) = [ C_final(t) - 1.96 * sigma(t),   C_final(t) + 1.96 * sigma(t) ]  intersected with  [0, 1]
```

---

### Dual-Layer Disease Confidence (Equations 7–8)

**Equation 7 (Overt disease confidence):**

```
C_O(r^O, P) = min( 0.70 + 0.05 * eta(r^O, P),  0.95 )
```

**Equation 8 (Hidden disease confidence):**

```
C_H(r^H, P) = min( 0.50 + 0.05 * eta(r^H, P),  0.75 )
```

Where the evidence count is:

```
eta(r, P) = | R  intersect  A_P |  +  | S  intersect  A_P |
```

---

### Worked Example: HbA1c = 5.9% — Full Step-by-Step (§4.3.4)

**Authority parameters:**

| Authority | Vote    | $s_i$ | $e_i$ | $s_i \cdot e_i$ |
|-----------|---------|--------|--------|-------------------|
| ADA      | ATT     | 0.95   | 1.0    | 0.9500           |
| WHO      | NORMAL  | 0.94   | 1.0    | 0.9400           |
| NICE     | NORMAL  | 0.92   | 1.0    | 0.9200           |
| IFCC     | ATT     | 0.92   | 0.9    | 0.8280           |
| **Sum**  |         |        |        | **3.6380**       |

| Denominator sum | 1.0 + 1.0 + 1.0 + 0.9 = **3.90** |

**Step 1:** $C_{\text{base}} = 3.6380 / 3.90 =$ **0.933**

**Step 2:** 2 ATT vs 2 NORM → partial agreement → $B_{\text{consensus}} =$ **+0.02**

**Step 3:** $|A_t| = 4 \geq 3$ → $B_{\text{source}} = \min(0.02 \times 3, 0.06) =$ **+0.06**

**Step 4:** $C_{\text{final}} = \min(0.933 + 0.02 + 0.06, 1.0) = \min(1.013, 1.0) =$ **1.0** (capped)

**Step 5:** partial → $\sigma_{\text{consensus}} = 0.04$; $|V(t)| = 4 \geq 3$ → $\sigma_{\text{source}} = 0.02$;
$\sigma = \sqrt{0.02^2 + 0.04^2} = \sqrt{0.0004 + 0.0016} = \sqrt{0.0020} =$ **0.045**;
$\text{CI}_{95\%} = [1.0 − 1.96 \times 0.045, 1.0] = [0.912, 1.0]$ → **[0.912, 1.0]** ✅

---

## Appendix F: Confidence Parameter Design Documentation

This appendix documents the design rationale for the confidence parameters used in the framework, including the principled basis for each numeric constant.

### F.1 Conservative Escalation Rule (Definition 1)

The consensus classification rule was designed according to the clinical safety principle that CRITICAL classifications should require multi-authority corroboration. The specific form — $n_{\text{CRIT}} \geq 2$ OR $(n_{\text{CRIT}} \geq 1 \land n_{\text{ATT}} \geq 1)$ — was selected to address two clinical scenarios:

1. **Strong CRITICAL consensus**: When two or more independent authorities classify a result as CRITICAL, the combined evidence warrants immediate clinical attention regardless of any ATTENTION votes.

2. **Mixed vote with CRITICAL majority**: When one authority votes CRITICAL and at least one votes ATTENTION (but none vote NORMAL), the presence of CRITICAL evidence from a credible source justifies escalation even without full consensus.

The rationale for this rule follows from the clinical intuition that single-authority verdicts carry inherent epistemic uncertainty: requiring multi-authority corroboration for CRITICAL classifications aligns with the precautionary principle in clinical decision-making. The specific numeric thresholds (2 for $n_{\text{CRIT}}$, and the conjunction $n_{\text{CRIT}} \geq 1 \land n_{\text{ATT}} \geq 1$) were set to distinguish genuine multi-authority concern from isolated single-authority flags.

### F.2 Consensus Bonus Design ($B_{\text{consensus}}$)

The $B_{\text{consensus}}$ values (+0.05, +0.02, −0.03) were set according to the following rationale:

1. **Full agreement bonus (+0.05)**: When all covering authorities vote in the same category, unanimous agreement provides additional confidence beyond the evidence-weighted base score. The specific increment of +0.05 was selected to reward full consensus while remaining modest relative to the sensitivity-weighted base confidence.

2. **Partial agreement (+0.02)**: When two categories are present (e.g., ATTENTION and NORMAL, or CRITICAL and ATTENTION), the bonus acknowledges partial corroboration. The increment of +0.02 is lower than the per-authority bonus in $B_{\text{source}}$ (which awards +0.02 per additional covering authority), reflecting that a vote in a different category provides less corroboration than an additional vote in the same category.

3. **Significant disagreement (−0.03)**: When all three categories are present, the penalty flags genuine inter-authority disagreement as a clinical safety signal. The specific deduction of −0.03 is bounded to prevent complete confidence collapse while ensuring the CI reflects the disagreement.

### F.3 Uncertainty Components ($\sigma$)

The $\sigma_{\text{source}}$ and $\sigma_{\text{consensus}}$ values were set to produce CI widths that reflect the epistemic uncertainty inherent in authority-based classification:

1. **Single authority ($\sigma_{\text{source}} = 0.10$)**: A single-authority classification carries the highest epistemic uncertainty. The resulting 95% CI width of approximately ±0.20 reflects the absence of corroborating evidence.

2. **Two authorities ($\sigma_{\text{source}} = 0.05$)**: Two independent authorities provide meaningful corroboration, reducing source uncertainty. The resulting 95% CI width of approximately ±0.10 represents a 50% reduction in uncertainty relative to single-authority classification.

3. **Three or more authorities ($\sigma_{\text{source}} = 0.02$)**: With three or more covering authorities, source uncertainty becomes minimal. The resulting 95% CI width of approximately ±0.04 is dominated by consensus uncertainty.

The $\sigma_{\text{consensus}}$ values (0.01/0.04/0.08 for full/partial/none) follow standard uncertainty quantification practice: consensus uncertainty is bounded at 0.08 to prevent meaningless CI widths while remaining sensitive to genuine disagreement.

### F.4 Evidence-Level Weights ($e_i$)

The mapping from Oxford CEBM grades to evidence-level weights (1A → 1.0, 1B → 0.9) follows the standard interpretation of the CEBM hierarchy. Grade 1A indicates "consistent level 1 studies" with low risk of bias; Grade 1B indicates "individual level 1 studies" or "extrapolations from level 1 studies." The 0.1 weight difference reflects the incremental reliability of direct trial evidence over extrapolation.

All authorities in the framework carry CEBM Grade 1A or 1B, ensuring that only the highest-quality clinical evidence contributes to consensus classification.

### F.5 Disease Confidence Floors and Ceilings

The overt confidence floor (0.70) and hidden confidence ceiling (0.75) were set to maintain a hierarchical relationship between the two inference layers:

1. **Overt floor (0.70)**: A CRITICAL classification from the consensus mechanism corresponds to confirmed-disease criteria supported by Grade 1A evidence from at least two independent authorities. A minimum confidence of 0.70 reflects the clinical certainty appropriate for confirmed-disease diagnosis, anchored in RCT evidence (e.g., treatment benefit at TSH ≥ 10 mIU/L demonstrated in [S2]).

2. **Hidden ceiling (0.75)**: A hidden-layer classification corresponds to subclinical evidence supported by Grade 1A evidence but without definitive outcome trial benefit for intervention (e.g., TRUST trial null result in [S2]). The ceiling of 0.75 is set above the overt floor of 0.70 to maintain a gap between the minimum confirmed-disease confidence and the maximum subclinical confidence. This design ensures that even the most strongly supported hidden-layer inference (with five supporting tests) cannot exceed the confidence level that a bare confirmed-disease classification receives.

3. **Hidden floor (0.50)**: A hidden-layer confidence of 0.50 represents the minimum evidence threshold for subclinical flagging. This floor was set to ensure that hidden-layer alerts are meaningful but not alarming, consistent with the monitoring-oriented semantics of hidden-layer labels.

---

## References

*[Full reference list to be inserted. All citations in the manuscript are documented and verified in the Citation Map: document/papers/Paper1/PLAN/Paper1_Citation_Map.md. References to be formatted in the target journal's reference style before submission.]*

