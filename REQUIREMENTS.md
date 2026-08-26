# NarrateBI — System Requirements Specification

## 1. Functional Requirements

### FR-1: KPI Engine & Contract Management
- Load KPI metadata, definitions, formulas, and thresholds from `config/kpi_contracts.yaml`.
- Deterministically compute current values, baseline comparisons, and percentage delta:
  $$\Delta\% = \frac{\text{current} - \text{baseline}}{\text{baseline}} \times 100$$
- Flag movements exceeding KPI anomaly threshold as anomalies.
- Detect "Cold Start" KPIs with insufficient history (< 14 days) and abstain from anomaly diagnosis.

### FR-2: Deterministic Driver Analysis
- Quantify relative contribution of parent-child KPI drivers (e.g. For Revenue drop: assess Orders vs. AOV contribution).
- Output ranked drivers with deterministic percentage contributions summing to 100%.

### FR-3: Evidence Synthesis & RAG Integration
- Retrieve structured signals from SQLite (e.g., checkout error rate +42%, payment failures +25%).
- Retrieve unstructured operational documents from ChromaDB vector store (deployments, incident reports, logs, support tickets).
- Merge structured and unstructured signals into a unified chronological evidence list.

### FR-4: Confidence Scoring & Abstention
- Calculate deterministic confidence score (0–100%) based on:
  - Driver strength & clarity
  - Operational evidence availability
  - Temporal correlation / alignment
  - Signal consistency
- Classification:
  - **High ($\ge 70\%$)**: Invoke LLM for persona narrative.
  - **Medium ($45\% - 69\%$)**: Invoke LLM with explicit uncertainty disclaimers.
  - **Low ($< 45\%$)**: Abstain. Output structured "Insufficient evidence to determine root cause".

### FR-5: Role-Based Narratives & Recommendations
- **Executive**: Financial impact, conversion loss, business summary, mitigation strategy.
- **Engineer**: Service version, deployment timestamp, stack trace/error codes, rollback/debugging steps.

### FR-6: Scenarios Support
- Support 5 distinct test scenarios via identical pipeline processing:
  1. Multi-factor diagnosis
  2. Low confidence / missing evidence
  3. New KPI / limited history
  4. Role-based access control (RBAC) demo
  5. Contradictory evidence

### FR-7: System Telemetry & Feedback
- Measure and display runtime latency (ms), token usage, and calculated AI cost ($).
- Collect user diagnostic feedback (👍 / 👎) stored in SQLite.

---

## 2. Non-Functional Requirements
- **Performance**: Sub-second UI updates for cached analysis; deterministic math executes in < 50ms.
- **Resilience**: Graceful fallback if RAG or LLM API is unavailable.
- **Security**: No secrets committed to git; API keys loaded strictly via environment variables.
- **Design Aesthetic**: Modern B2B SaaS layout (clean neutral light background, subtle borders, high contrast, responsive desktop & mobile).
