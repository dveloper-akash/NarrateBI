# NarrateBI: KPI Diagnostic & Action Intelligence Engine

NarrateBI is an enterprise KPI intelligence platform that bridges the gap between metric movement detection and business execution. While traditional BI dashboards show *what* changed, NarrateBI determines *why* it changed, validates the finding with multi-source evidence, computes a mathematical confidence score, and delivers persona-specific action plans with full lineage.

The system enforces a strict architectural principle: **The LLM is never the source of quantitative truth.** Mathematical decomposition, anomaly detection, confidence calibration, and action prioritization are computed deterministically. The LLM is used solely to synthesize verified facts into persona-tailored natural language narratives.

---

## Key Capabilities & Architecture

```
                                 [ Data Sources ]
                   ERP / Sales  ·  Web Analytics  ·  Payment Gateway
                                        │
                                        ▼
                        [ Semantic & KPI Contract Layer ]
                     Definitions · Formulas · Lineage · ACLs
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             ▼                                                     ▼
 [ Deterministic Driver Engine ]                         [ Hybrid Evidence Layer ]
  Hierarchical Variance Analysis                          ChromaDB Vector Retrieval +
  (Revenue = Orders × AOV)                                Structured Operational Logs
             │                                                     │
             └──────────────────────────┬──────────────────────────┘
                                        ▼
                         [ Confidence Calibration Engine ]
                        History Depth · Anomaly Strength ·
                        Evidence Corroboration · Contradictions
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             ▼                                                     ▼
 [ Persona-Aware Action Engine ]                          [ Grounded Narrative Engine ]
  Driver → Lever → Action →                                Gemini 2.5 Flash / Fallback
  Impact → Owner → Confidence                              Executive vs. Engineer Lens
             │                                                     │
             └──────────────────────────┬──────────────────────────┘
                                        ▼
                          [ Streamlit Enterprise UI ]
                      Telemetry · RBAC · Feedback Loop
```

### 1. Semantic KPI Contracts (`config/kpi_contracts.yaml`)
Every monitored metric is governed by a machine-readable contract defining its formula, grain, source of truth, refresh cadence, anomaly threshold, minimum history baseline, lineage, and access controls.

### 2. Deterministic Driver Decomposition (`engine/driver_engine.py`)
Root-cause analysis begins with exact mathematical variance decomposition across hierarchical parent-child relationships (e.g., $\Delta\text{Revenue} = f(\Delta\text{Orders}, \Delta\text{AOV})$, where $\Delta\text{Orders} = f(\Delta\text{Sessions}, \Delta\text{Conversion Rate})$).

### 3. Corroborating Evidence Retrieval (`rag/` & `engine/evidence.py`)
Analytical findings automatically generate targeted search queries against operational documents, deployment logs, post-mortems, incident reports, and support ticket digests stored in a local vector database.

### 4. Deterministic Confidence & Abstention (`engine/confidence.py`)
Confidence is scored (0–100%) using four weighted factors:
- Baseline history sufficiency
- Driver isolation & ambiguity gap
- Multi-source evidence corroboration
- Signal consistency (penalizing contradictory evidence)

If confidence falls below the calibrated threshold (< 43%), the system **abstains** from guessing and explicitly lists the missing evidence required for diagnosis.

### 5. Grounded Action Recommendations (`engine/action_engine.py`)
Actions follow a governed framework:
$$\text{Driver} \longrightarrow \text{Controllable Lever} \longrightarrow \text{Action} \longrightarrow \text{Expected Impact} \longrightarrow \text{Owner} \longrightarrow \text{Confidence} \longrightarrow \text{Monitoring Plan}$$
Strategic levers are assigned to Executive roles, while technical runbooks are assigned to Engineering roles.

### 6. Role-Based Security & Auditability (RBAC)
Sensitive operational logs, stack traces, and internal server telemetry are masked for executive roles and visible only to authorized engineering personnel.

### 7. Analyst Feedback & Continuous Learning
Built-in rating controls record analyst feedback directly into SQLite, creating an audit trail for continuous diagnostic validation.

### 8. Runtime Telemetry & Cost Control
Every diagnostic cycle displays live execution telemetry: processing latency (ms), token consumption, estimated inference cost ($USD), and execution mode.

---

## Core Monitored KPIs

| KPI Name | Source System | Refresh Cadence | Formula / Grain | Anomaly Threshold |
| :--- | :--- | :--- | :--- | :--- |
| **Revenue** | ERP / Sales DB | Daily | $\text{Orders} \times \text{AOV}$ | $\pm 10.0\%$ |
| **Orders** | ERP / Sales DB | Daily | $\text{Sessions} \times \text{Conversion Rate}$ | $\pm 8.0\%$ |
| **Conversion Rate** | Web Analytics / Logs | Hourly | $(\text{Orders} / \text{Sessions}) \times 100$ | $\pm 8.0\%$ |
| **Sessions** | Web Analytics / CDN | Hourly | Unique visitor sessions | $\pm 10.0\%$ |
| **Average Order Value (AOV)**| ERP / Sales DB | Daily | $\text{Revenue} / \text{Orders}$ | $\pm 5.0\%$ |
| **New Product Conversion** | Product Clickstream | Hourly | $(\text{New Orders} / \text{New Views}) \times 100$ | $\pm 10.0\%$ (Min 14d baseline) |

---

## Prototype Demo Scenarios

The prototype includes five pre-configured scenarios designed to validate key enterprise edge cases:

1. **Multi-Factor Diagnosis (`scenario_1_multifactor`)**
   - **Condition:** Revenue drops 12.4%.
   - **Diagnosis:** Driver decomposition isolates a 30.8% drop in Conversion Rate as the primary drag (76% contribution), while Sessions increased (+26.6%) due to a marketing campaign.
   - **Corroborating Evidence:** RAG correlates the drop to `Payment Service v2.4.0` deployment introducing a high-latency timeout loop on the checkout gateway.
   - **Outcome:** High confidence (88%). Generates executive commercial recovery plans and engineering hotfix/rollback runbooks.

2. **Low Confidence / Abstention (`scenario_2_low_confidence`)**
   - **Condition:** Metric variance detected, but operational logs and RAG evidence are missing or ambiguous.
   - **Outcome:** Confidence drops to 32% (Low). The system deterministically **abstains** from generating an unverified hallucination and outputs exact missing evidence hints.

3. **Cold Start / Sparse History (`scenario_3_new_kpi`)**
   - **Condition:** Newly launched metric (`New Product Conversion`) with only 3 days of telemetry (< 14-day minimum contract threshold).
   - **Outcome:** Immediate cold-start warning banner. The system prevents premature anomaly alerting on uncalibrated baselines.

4. **Role-Based Access Control (`scenario_4_rbac`)**
   - **Condition:** Comparing Executive vs. Engineer personas.
   - **Outcome:** Executive view masks raw server log dumps and presents commercial levers. Engineer view provides unredacted stack traces, build artifacts, and deployment rollback steps.

5. **Contradictory Signals (`scenario_5_contradiction`)**
   - **Condition:** Marketing claims record conversion and campaign success, while transaction telemetry shows severe checkout failures.
   - **Outcome:** The engine detects signal divergence, highlights the conflicting evidence badge, applies a penalty to the confidence score, and prompts for reconciliation.

---

## Directory Structure

```
narratebi/
├── app/
│   └── streamlit_app.py          # Enterprise B2B SaaS dashboard UI
├── engine/
│   ├── kpi_engine.py             # Semantic contracts & KPI anomaly detection
│   ├── driver_engine.py          # Deterministic parent-child variance decomposition
│   ├── evidence.py               # Merges structured database signals with vector RAG
│   ├── confidence.py             # Mathematical confidence scoring & abstention logic
│   └── action_engine.py          # Structured action recommendation generator
├── ai/
│   ├── narrative.py              # Gemini 2.5 Flash client & schema-validated narratives
│   └── prompts/                  # Persona-specific prompt templates (Executive / Engineer)
├── database/
│   ├── schema.sql                # Relational SQLite schema (sales, payments, logs, feedback)
│   ├── seed.py                   # Deterministic time-series data generator
│   └── narratebi.db              # SQLite instance
├── rag/
│   ├── ingest.py                 # Markdown document chunking & vector indexing
│   ├── retrieve.py               # Hybrid similarity retrieval engine
│   ├── query_builder.py          # Contextual query synthesizer from driver outputs
│   ├── index_manifest.json       # Index metadata & document registry
│   └── documents/                # Operational documents (incidents, deployments, logs)
├── scenarios/                    # JSON scenario definitions for reproducible testing
├── config/
│   └── kpi_contracts.yaml        # Governed semantic contracts & thresholds
├── tests/
│   ├── test_part1_validation.py  # Unit tests for contracts, engines & RBAC
│   ├── test_part2_analytical_correctness.py # Mathematical correctness & driver tests
│   └── test_phase4_end_to_end.py # End-to-end integration tests
├── requirements.txt              # Production dependencies
└── README.md
```

---

## Quick Start

### 1. Prerequisites
- Python 3.10, 3.11, or 3.12
- Git

### 2. Installation & Setup
```bash
# Clone the repository
git clone https://github.com/dveloper-akash/NarrateBI.git
cd NarrateBI

# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the project root:
```ini
GEMINI_API_KEY=your_google_gemini_api_key_here
```
*(Note: If no API key is provided, NarrateBI automatically falls back to its internal deterministic narrative engine without crashing).*

### 4. Database Seeding & Ingestion
```bash
# Initialize SQLite database and seed deterministic time-series data
python database/seed.py

# Ingest operational markdown documents into vector index
python rag/ingest.py
```

### 5. Running the Application
```bash
streamlit run app/streamlit_app.py
```
Open your browser at `http://localhost:8501`.

### 6. Running Automated Verification
```bash
python -m unittest discover -s tests
```
*All 67 test suites cover mathematical correctness, driver decomposition, confidence scoring, RBAC masking, and abstention.*

---

## Technical Highlights

- **Zero LLM Math:** All percentage deltas, anomaly flags, driver contribution percentages, and confidence scores are calculated in pure Python.
- **Strict Error Handling:** If vector search or LLM APIs encounter rate limits or network issues, the application falls back gracefully to deterministic rule-based narratives.
- **Audit-Ready Lineage:** Popover metadata on every KPI card provides direct visibility into raw formulas, system owners, update cadences, and lineage paths.
