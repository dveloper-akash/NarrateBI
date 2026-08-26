# NarrateBI — Project Status & Roadmap

## Current Phase: Phase 0 (Foundation & Scaffold)

### Status Summary
- [x] Repository structure created according to specification.
- [x] Dependencies defined in `requirements.txt`.
- [x] Master KPI contracts declared in `config/kpi_contracts.yaml`.
- [x] SQLite database schema prepared in `database/schema.sql`.
- [x] Modular seed script initialized in `database/seed.py`.
- [x] Core engine and RAG stubs created with clear interfaces.
- [x] Scenario templates initialized in `scenarios/`.
- [x] Minimal runnable Streamlit app created in `app/streamlit_app.py`.
- [x] Git repository initialized and tracking baseline.

---

## Roadmap

### Phase 1: Database & Deterministic Engines (Immediate Next Step)
- [ ] Implement full synthetic data generation in `database/seed.py` for all 5 scenarios.
- [ ] Implement `engine/kpi_engine.py` (calculations, anomaly detection, cold-start checks).
- [ ] Implement `engine/driver_engine.py` (parent-child driver contribution calculations).
- [ ] Unit test Phase 1 deterministic logic.

### Phase 2: Evidence & RAG Layer
- [ ] Build vector ingestion in `rag/ingest.py` with ChromaDB.
- [ ] Implement vector search & filtering in `rag/retrieve.py`.
- [ ] Implement consolidated evidence engine in `engine/evidence.py`.
- [ ] Implement multi-factor confidence engine in `engine/confidence.py`.

### Phase 3: AI Narrative & Persona Prompts
- [ ] Implement `ai/narrative.py` integrating LLM with structured output parsing.
- [ ] Build persona prompt templates (`executive.txt`, `engineer.txt`).
- [ ] Implement fallback resilience when LLM is offline.

### Phase 4: Full Streamlit Dashboard & Telemetry
- [ ] Connect Streamlit UI to end-to-end engine pipeline.
- [ ] Interactive KPI definition popovers & lineage view.
- [ ] Telemetry tracking (latency, tokens, AI cost calculation).
- [ ] Feedback collection (👍/👎) persisted to SQLite.

### Phase 5: Polish & Cloud Deployment Readiness
- [ ] Responsive layout verification (Desktop & Mobile).
- [ ] Complete scenario test suite.
- [ ] Final deployment documentation.
