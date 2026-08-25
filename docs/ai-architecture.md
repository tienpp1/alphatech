# AI & Machine Learning Subsystem Architecture

## 1. Scope Lock & Core Philosophy

In V1, the AI subsystem is built on **explainability, determinism, and controlled agency**. It is designed to empower human operators rather than operate autonomously.

### V1 AI Roster (Exclusively 4 Pillars)
1. **RAG + LLM**: Grounded question answering on organizational documents and business metrics.
2. **XGBoost Time-Series Forecasting**: Accurate tabular forecasting for revenue, orders, and workload.
3. **Deterministic Business Rules & Recommendations**: Explainable decision support combining forecasts and real-time business telemetry.
4. **Controlled Tool Calling with Human-in-the-Loop Approval & Auditing**: Structured execution of actions with permission and manager review barriers.

---

## 2. Pillar 1: RAG + LLM Subsystem

The RAG pipeline provides context-grounded answers to business users without hallucinations.

```text
[PDF/DOCX/TXT] ──> [Text Extraction] ──> [Recursive Chunking]
                                                  │
                                                  ▼
[pgvector DB] <── [Vector Embedding API] <── [500-Token Text Chunks]
      │
      │ (User Query ──> Query Embedding ──> Cosine Similarity Search)
      ▼
[Top-K Grounded Chunks (Score >= 0.70)]
      │
      ▼
[Prompt Template: Grounded Context + User Query + Workspace Scope]
      │
      ▼
[LLM API (Gemini / OpenAI)] ──> [Grounded Answer + Document Citations]
```

### Key Implementation Invariants
- **Chunk Size**: $500 - 800$ tokens with a $100$-token sliding overlap.
- **Embedding Model**: Text embedding model (e.g., `text-embedding-004` / 768 dimensions).
- **Workspace Isolation**: Vector queries strictly filter on `workspace_id = active_workspace_id`.
- **Fallback Rule**: If similarity score of retrieved chunks is below threshold ($0.70$), the assistant explicitly responds: *"Dữ liệu tài liệu hiện tại không đủ thông tin để trả lời chính xác câu hỏi này"* rather than guessing.

---

## 3. Pillar 2: XGBoost Time-Series Forecasting

XGBoost is selected for its state-of-the-art performance on structured tabular data, fast training convergence, and interpretability.

```text
[Orders / Service Requests DB]
            │
            ▼
[Data Aggregation (Daily / Weekly)] ──> [Feature Engineering]
                                               ├── Lag Features: lag_1, lag_2, lag_7, lag_14
                                               ├── Rolling Statistics: rolling_mean_7, rolling_std_7
                                               └── Calendar Features: day_of_week, month, is_weekend
            │
            ▼
[Time-Based Train/Test Split] (Strictly NO random split across time series)
            │
            ▼
[XGBoost Regressor Training] ──> [Evaluation vs Naive Baseline (MAE, RMSE)]
            │
            ▼
[Forecast Run Saved in DB + Model Serialized in ml_models/]
```

### Evaluation Protocol
- **Metrics**: MAE (Mean Absolute Error), RMSE (Root Mean Squared Error), MAPE.
- **Baseline Comparison**: Every model run must be benchmarked against a Naive Persistence Baseline ($y_t = y_{t-1}$ or $y_t = y_{t-7}$).

---

## 4. Pillar 3: Deterministic Recommendations Engine

Recommendations combine forecast predictions, current operational thresholds, and deterministic business rules.

$$\mathbf{Forecast\ Trend} + \mathbf{Real\text{-}time\ Business\ State} + \mathbf{Business\ Rules} \Longrightarrow \mathbf{Explainable\ Recommendation}$$

### Concrete Domain Examples
1. **Retail Inventory & Sales Alert**:
   - *Forecast*: Branch A daily revenue forecasted to drop by $25\%$ next week due to low customer footfall.
   - *Rule*: If forecasted revenue drop $> 20\%$, trigger promotional campaign recommendation.
   - *Recommendation*: *"Đề xuất áp dụng chương trình Flash Sale cho danh mục Sản phẩm X tại Chi nhánh A từ ngày 01/09 để kích cầu."*
2. **Service Field Dispatch**:
   - *Trigger*: Incident `#SR-104` logged in District 1 with priority `HIGH` (SLA deadline in 4 hours).
   - *Telemetry*: Technician Nam is located 3.2 km away with workload score 40; Technician Tuan is 12 km away with workload score 80.
   - *Rule*: Rank by $\text{Score} = 0.6 \times (1 / \text{Distance}) + 0.4 \times (100 - \text{Workload})$.
   - *Recommendation*: *"Đề xuất phân công Kỹ thuật viên Nam (Khoảng cách: 3.2 km, Tải công việc hiện tại: 40/100). Lý do: Khoảng cách gần nhất và tải công việc tối ưu."*

---

## 5. Pillar 4: Controlled Tool Calling & Approval Flow

AI Agents never execute raw database mutations or arbitrary SQL. All agentic actions pass through predefined, typed tools.

```text
[User Request in AI Chat]
           │
           ▼
[LLM Tool Selection (JSON Schema)]
           │
           ▼
[Backend Permission & Validation Gate]
    ├── 1. Check Caller RBAC Permissions
    ├── 2. Validate Tool Parameter Schema
    └── 3. Check Action Mutation Severity
           │
      ┌────┴──────────────────────────────┐
      │                                   │
[Read-Only Tool (e.g. read_orders)]  [Mutating Tool (e.g. dispatch_technician)]
      │                                   │
      │                                   ▼
      │                             [Generate ApprovalRequest (Status: PENDING)]
      │                                   │
      │                             [Manager Review: APPROVE / REJECT]
      │                                   │
      └───────────────────────────────────┤ (Upon Approval)
                                          ▼
                                   [Execute Tool Action]
                                          │
                                          ▼
                                   [Write to Immutable AuditLog]
```

### Whitelisted Tool Registry (V1)
- `read_sales_summary(start_date, end_date, branch_id)`
- `query_nearby_technicians(incident_location, radius_km, required_skill)`
- `retrieve_policy_documents(query_topic)`
- `get_forecast_trends(domain, horizon_days)`
- `submit_technician_dispatch(service_request_id, employee_id, notes)` *(Requires Approval)*
- `update_order_status(order_number, new_status)` *(Requires Approval)*
