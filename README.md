# Paper 1: Dual-Layer Disease Inference Framework

A clinical decision support system implementing a dual-layer (overt/subclinical) disease inference architecture with multi-authority threshold reconciliation in a Neo4j knowledge graph.

## System Overview

This framework addresses the challenge of reconciling divergent clinical guidelines from multiple authoritative bodies by:

1. **Multi-Authority Consensus Classification**: Aggregating thresholds from 9 clinical guideline organizations (NICE, ADA, WHO, ESC, KDIGO, ATA, ETA, WHO-Hb, IFCC) with a weighted voting mechanism and 95% confidence intervals.

2. **Dual-Layer Disease Inference**: Detecting both overt (clinically apparent) and hidden (subclinical) disease conditions using a two-tier rule system with suppression mechanisms.

3. **Knowledge Graph Implementation**: Full traceability from raw laboratory values through classification decisions to disease inference outcomes in Neo4j.

## Project Structure

```
git_upload/
├── src/
│   ├── __init__.py
│   ├── config.py              # Database configuration
│   ├── classification.py       # Multi-authority consensus classification
│   ├── disease_inference.py    # Dual-layer disease rules
│   └── evaluation.py          # Baseline comparison and ablation studies
├── docs/
│   ├── Paper1_Manuscript.md   # Full manuscript
│   └── Paper1_Proposal.md     # Research proposal
├── figures/
│   ├── Figure1_Pipeline_Workflow.svg
│   └── Figure2_Neo4j_Schema.svg
└── visualizations/
    └── paper_flowcharts.html
```

## Core Components

### Classification Module (`classification.py`)

- 9 authoritative guideline thresholds (23 laboratory tests)
- Consensus voting algorithm with confidence scoring
- 95% confidence interval calculation

### Disease Inference Module (`disease_inference.py`)

- 8 overt disease rules (CRITICAL threshold triggers)
- 7 hidden disease rules (ATTENTION threshold triggers)
- Suppression mechanism (Theorem 1) for hierarchical exclusion

### Evaluation Module (`evaluation.py`)

- B1/B2/B3/Full baseline comparison
- Config-1/3/6/9 authority ablation studies

## Installation

```bash
pip install neo4j
```

## Configuration

Set up your Neo4j connection credentials:

```python
# credentials.py
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your_password"
```

## Usage

```bash
# Runs the baseline comparison (B1/B2/B3/Full) and the authority
# ablation (Config-1/3/6/9) in one pass, printing the result tables:
python -m src.evaluation
```

> Requires a populated Neo4j database and a `credentials.py` (see Configuration).

## Data Requirements

- Neo4j database with Patient, TestResult nodes
- Phase 2 classification nodes (NormalTest, AttentionTest, CriticalTest)
- Phase 2 disease risk nodes (OvertDiseaseRisk, HiddenDiseaseRisk)

## License

MIT License
