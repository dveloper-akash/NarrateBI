# NarrateBI

**AI-Powered Business Intelligence Prototype**

> *Deterministic analysis finds the truth. RAG finds contextual evidence. The LLM explains the verified result.*

---

## Overview

Traditional dashboards display **what** changed (e.g., Revenue ↓ 12%), leaving analysts to manually dig through logs, deployments, and alerts to find the cause.

**NarrateBI** automates the entire root-cause journey:
1. **Detects** significant KPI movements using deterministic math against configured contracts.
2. **Identifies & ranks** causal drivers (e.g., Conversion Rate vs. AOV).
3. **Retrieves** corroborating structured metrics and unstructured operational evidence (deployments, incident reports, logs).
4. **Calculates** diagnostic confidence scores.
5. **Generates** persona-tailored explanations (Executive vs. Engineer) or **abstains** when evidence is insufficient.

---

## Quick Start

### 1. Prerequisites
- Python 3.11+
- Git

### 2. Environment Setup
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Initialize Database & RAG Index
```powershell
# Seed the SQLite database
python database/seed.py

# Ingest operational documents into ChromaDB
python rag/ingest.py
```

### 4. Run the Application
```powershell
streamlit run app/streamlit_app.py
```

---

## Repository Structure

```
narratebi/
├── app/
│   └── streamlit_app.py          # Clean B2B SaaS dashboard UI
├── engine/
│   ├── kpi_engine.py             # Deterministic KPI & anomaly calculations
│   ├── driver_engine.py          # Parent-child driver contribution ranking
│   ├── evidence.py               # Merges structured signals & RAG evidence
│   └── confidence.py             # Multi-factor confidence scoring & abstention
├── database/
│   ├── schema.sql                # SQLite database schema
│   ├── seed.py                   # Realistic deterministic dataset generator
│   └── narratebi.db              # Local SQLite database
├── rag/
│   ├── ingest.py                 # Document chunking & embedding ingestion
│   ├── retrieve.py               # Vector similarity search
│   └── documents/                # Markdown operational docs (incidents, deployments, logs)
├── ai/
│   ├── narrative.py              # LLM client & structured response generation
│   └── prompts/                  # Persona-specific prompt templates
├── scenarios/                    # Scenario input configurations for demo testing
├── config/
│   └── kpi_contracts.yaml        # Source of truth for KPI definitions & thresholds
├── requirements.txt
├── PROJECT_CONTEXT.md
├── REQUIREMENTS.md
├── CURRENT_STATUS.md
└── AGENTS.md
```

---

## Key Features & Demo Scenarios
- **Multi-Factor Root Cause**: Full diagnosis connecting revenue drop to conversion loss and payment gateway deployment.
- **Low Confidence / Abstention**: Intelligent abstention when operational evidence is unavailable.
- **Cold Start**: Graceful handling of newly introduced KPIs with insufficient history (< 14 days).
- **Role-Based Views**: Instant switching between Executive (business impact) and Engineer (technical telemetry).
- **Architecture Transparency**: Clear visual separation of deterministic calculations vs. AI generative narrative.
