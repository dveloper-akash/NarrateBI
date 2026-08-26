# NarrateBI — Master Development Context

## 1. Project Overview
NarrateBI is an AI-powered Business Intelligence prototype. It takes structured business KPI data and unstructured operational evidence, detects significant KPI movements, identifies the most likely root cause drivers, synthesizes supporting evidence, computes diagnostic confidence, and generates role-tailored explanations and recommendations for different personas (Executive vs. Engineer).

### Core Philosophy
> **Deterministic analysis finds the truth. RAG finds contextual evidence. The LLM explains the verified result.**

The LLM must **never** calculate KPI values, percentage changes, driver contributions, or confidence scores.

---

## 2. Pipeline Architecture
```
                  BUSINESS DATA (SQLite)
                           │
                           ▼
                    KPI CALCULATION (Deterministic)
                           │
                           ▼
                  ANOMALY DETECTION (Deterministic)
                           │
                           ▼
                   DRIVER ANALYSIS (Deterministic)
                           │
                           ▼
                  EVIDENCE RETRIEVAL (RAG / ChromaDB)
                           │
                           ▼
                 CONFIDENCE SCORING (Deterministic)
                           │
                  ┌────────┴────────┐
                  │                 │
               HIGH (>=70%)      LOW (<45%)
                  │                 │
                  ▼                 ▼
                 LLM             ABSTAIN
                  │            (No Hallucination)
                  ▼
           PERSONA-SPECIFIC
              NARRATIVE
                  │
                  ▼
            RECOMMENDATION
```

---

## 3. Five Connected KPI Model
- **Sessions** (Website traffic)
- **Conversion Rate** = `Orders / Sessions`
- **Orders** = `Sessions × Conversion Rate`
- **AOV (Average Order Value)** = `Revenue / Orders`
- **Revenue** = `Orders × AOV`

Relationships are explicitly modeled in code and configuration (`config/kpi_contracts.yaml`), not buried inside LLM prompts.

---

## 4. Key Personas
- **Executive**: Business-oriented narrative, revenue impact, high-level root cause, strategic action items.
- **Engineer/Ops**: Technical signals, deployment logs, timestamps, error codes, infrastructure recommendations.

---

## 5. Non-Negotiable Rules
1. **Never guess on low confidence**: If confidence < 45%, state insufficient evidence and abstain.
2. **Cold start detection**: If a KPI has insufficient baseline history (< 14 days), flag "Limited baseline data".
3. **No hard-coded answers**: Scenarios only supply data; the identical pipeline processes every scenario.
4. **Deterministic vs. Generative separation**: Explicitly badge which pipeline elements are deterministic vs. AI-generated.
