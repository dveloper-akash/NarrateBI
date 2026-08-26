# NarrateBI — Multi-Agent & Developer Collaboration Rules

## 1. Modular Boundaries
To allow multiple developers/agents to work simultaneously without conflicts:
- **UI Layer (`app/`)**: Only consumes engine outputs. Contains zero business logic, KPI math, or confidence calculations.
- **KPI & Driver Engine (`engine/`)**: Pure deterministic Python functions with clean type annotations. No Streamlit dependencies.
- **Data Layer (`database/`)**: Manages SQLite schema and deterministic synthetic seed generation.
- **RAG Layer (`rag/`)**: Isolated document indexing and retrieval using ChromaDB.
- **AI Layer (`ai/`)**: Handles LLM prompting and schema validation. Never invents math or overrides confidence.

## 2. Coding Conventions
- **Simplicity First**: Write readable, small functions over complex class inheritance hierarchies.
- **Type Annotations**: Use Python type hints (`dataclasses`, `pydantic`, or standard typing) for clear contracts.
- **Error Handling**: Gracefully handle missing dependencies, network failures, or offline LLMs without crashing the app.
- **No Hardcoded Secrets**: Secrets must only come from `.env` / environment variables.

## 3. Git Workflow
- Commit after completing discrete, verified logical units.
- Always verify the app runs (`streamlit run app/streamlit_app.py`) before committing.
