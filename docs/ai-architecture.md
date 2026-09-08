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
[PDF/DOCX/TXT] ──> [Text Extraction] ──> [Recursive Chunking (chunk_size, chunk_overlap)]
                                                              │
                                                              ▼
[pgvector DB] <── [Vector Embedding API] <── [Text Chunks (dim derived from model)]
      │
      │ (User Query ──> Query Embedding ──> Cosine Similarity Search)
      ▼
[Top-K Grounded Chunks (Similarity >= similarity_threshold)]
      │
      ▼
[Prompt Template: Grounded Context + User Query + Workspace Scope]
      │
      ▼
[LLM API (Gemini / OpenAI)] ──> [Grounded Answer + Document Citations]
```

### 2.1 Configurable RAG Experimental Parameters

RAG hyperparameters are **configurable system parameters** rather than fixed constants. Default values provide a starting baseline and must be tuned empirically against a benchmark test set during Phase 8.

| Parameter | Configuration Key | Default Value | Description / Tuning Rationale |
|---|---|---|---|
| **Chunk Size** | `RAG_CHUNK_SIZE` | `500` tokens | Target token length per chunk. Adjusted based on document density (e.g. 300–1000 tokens). |
| **Chunk Overlap** | `RAG_CHUNK_OVERLAP`| `100` tokens | Sliding window overlap to prevent context clipping across boundary sentences. |
| **Top K Chunks** | `RAG_TOP_K` | `5` chunks | Number of highest-similarity chunks passed into prompt context window. |
| **Similarity Threshold** | `RAG_SIMILARITY_THRESHOLD` | `0.70` (cosine) | Minimum cosine similarity required to consider a chunk relevant. Tuned per embedding model geometry. |
| **Embedding Model** | `EMBEDDING_MODEL` | `text-embedding-004` | Active embedding provider model (e.g., Google `text-embedding-004`, OpenAI `text-embedding-3-small`). |
| **Embedding Dimension**| `EMBEDDING_DIMENSION` | `768` (dynamic) | Vector dimension **derived directly from the active embedding model** (e.g. 768 or 1536). |

### 2.2 Dual-Mode Vector Storage & Multi-Platform Compatibility
- **Production Mode**: Native PostgreSQL `pgvector` (`vector` column type with cosine distance operators `<=>`).
- **Development / Non-Elevated Windows Fallback**: `DynamicVectorField` seamlessly maps to native `vector` when `pgvector` extension exists in PostgreSQL, and transparently falls back to an indexed `jsonb` array on platforms without C-extension binaries.
- **Dynamic Dimension**: Vector dimension is derived from `EMBEDDING_DIMENSION` and `EMBEDDING_MODEL` dynamically rather than hardcoded to a fixed constant.

### 2.3 Grounding, Citations & Fallback Invariant
- **Fallback Rule**: If no retrieved chunk meets `similarity_threshold` and no structured tool facts are available, the assistant strictly returns: *"Không tìm thấy thông tin đủ tin cậy trong tài liệu của doanh nghiệp."*
- **Strict Citations**: Every claim synthesized from document chunks includes a structured source citation `[Doc: <title>, P.<page>]` or `[Doc: <title>, Sec: <heading>]`.
- **Zero Raw SQL / Zero Mutations**: The LLM is strictly prohibited from generating or executing SQL. All structured facts are retrieved via parameterised, read-only Python selectors (`get_sales_summary`, `get_product_catalog_summary`, `get_customer_summary`, `get_service_ticket_summary`, `get_technician_workload_summary`).
- **Tenant Boundary**: All vector and structured queries enforce `for_workspace(active_workspace)`. Every query produces an immutable `AuditLog` entry.

### 2.4 Benchmark Evaluation Metrics
The pipeline is continuously validated by an automated benchmark suite (`apps.knowledge.evaluation`) across 16 test cases:
- **Retrieval Relevance Rate**: >= 80% (achieved 85.7%+)
- **Grounded Correctness Rate**: >= 80% (achieved 100.0%)
- **Fallback Precision**: 100.0% (achieved 100.0%)

---

## 3. Pillar 2: XGBoost Time-Series Forecasting

XGBoost is implemented in `apps.forecasting` for controlled, reproducible predictive analytics on tabular business time series. It translates operational business data into continuous chronologically ordered series, computes lag and rolling features, trains gradient-boosted decision trees, and recursively projects forward 14-day forecasts with approximate 95% prediction bands based on historical test residual standard deviation.

```text
[Orders / Service Requests DB]
            │
            ▼
[Data Aggregation & Gap Filling via Continuous Date Reindexing]
            │
            ▼
[Feature Engineering]
            ├── Autoregressive Lags: lag_1, lag_7, lag_14
            ├── Shifted Rolling Stats (Zero Leakage): rolling_mean_7, rolling_std_7, rolling_mean_14
            └── Calendar / Temporal: day_of_week, day_of_month, month, week_of_year, is_weekend
            │
            ▼
[Strict Chronological Split (80% Train / 20% Test, Non-Shuffled)]
            │
            ▼
[XGBoost Regressor Training (reg:squarederror, random_state=42)]
            │
            ▼
[Evaluation Benchmarking: MAE, RMSE, Non-Zero MAPE, R2 vs Naive Persistence Baseline]
            │
            ▼
[Model JSON Serialized in ml_models/forecasting/ + Run & 14-Day Recursive Predictions Saved in DB]
```

### 3.1 Supported Targets & Domain Validation
- **Retail Domain**:
  - `RETAIL_REVENUE`: Daily gross monetary sales (VND) from completed retail orders.
  - `RETAIL_ORDER_VOLUME`: Daily incoming volume of valid retail orders.
- **Service Domain**:
  - `SERVICE_TICKET_VOLUME`: Daily volume of incoming service request tickets.
- **Tenant Validation**: Workspaces are restricted to targets matching their operational domain (`RETAIL` vs `SERVICE`). Cross-domain training attempts are rejected with HTTP 400.

### 3.2 Evaluation Protocol, Baselines & Metric Limitations
- **Metrics**: MAE, RMSE, non-zero masked MAPE (excluding zero actuals to prevent infinite percentage skew on intermittent days), and $R^2$.
- **MAPE Limitations**:
  - MAPE is computed strictly on non-zero actual observations ($|y_i| > 10^{-3}$).
  - Percentage metrics are inherently volatile for small integer counts (such as daily service tickets), where a difference of 1 ticket can represent a 100% error. For Service Ticket Volume, MAPE is relatively high (**62.58%**).
  - Consequently, **MAE and RMSE are emphasized** for discrete, count-based service ops forecasting.
- **Naive Persistence Baseline & Benchmark Results**:
  - Models are benchmarked against naive persistence baselines ($y_t = y_{t-7}$ or $y_{t-1}$).
  - *On this benchmark, models performed better than the naive baseline (results are dataset-dependent):*
    - **Retail Revenue**: MAE 635,078 VND vs Baseline 832,234 VND (**+23.69% improvement**); RMSE 750,005 VND vs Baseline 1,029,425 VND (**+27.14% improvement**); MAPE: 31.85%.
    - **Retail Order Volume**: MAE 0.65 orders vs Baseline 0.81 orders (**+19.75% improvement**); RMSE 0.88 orders vs Baseline 1.12 orders (**+21.43% improvement**); MAPE: 34.45%.
    - **Service Ticket Volume**: MAE 0.94 tickets vs Baseline 1.14 tickets (**+17.54% improvement**); RMSE 1.21 tickets vs Baseline 1.48 tickets (**+18.24% improvement**); MAPE: 62.58%.
- **Prediction Uncertainty Bands**:
  - Bands represent approximate 95% prediction bands based on historical test residual standard deviation ($\pm 1.96 \cdot \sigma_{\text{residual}} \cdot \sqrt{1 + 0.05(h-1)}$).
  - These serve as an uncertainty visualization. Recursive multi-step forecasts accumulate autoregressive uncertainty forward in time; they are not formally calibrated probabilistic intervals.
- **Asynchronous Execution**: Training runs execute via `python manage.py train_forecast` or non-blocking background threads (`ForecastRun.status = PENDING -> RUNNING -> COMPLETED / FAILED`).
- **Security & Artifact Governance**: Native XGBoost JSON models are stored with path traversal verification. All records enforce `WorkspaceScopedModel` data isolation and `forecasting.view_forecast` / `forecasting.manage_forecast` RBAC.

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

## 5. Pillar 4: Controlled Tool Calling & Safe Execution Flow

AI Agents never execute raw database mutations or arbitrary SQL. All agentic actions pass through a multi-stage security pipeline:

```text
[User Intent in AI Chat]
           │
           ▼
[LLM Tool Selection (Schema-Validated)]
           │
           ▼
[Step 1: Tool Permission Check (Caller RBAC)]
           │
           ▼
[Step 2: Business Rule Validation]
           │
      ┌────┴───────────────────────────────────────┐
      │ (Read-Only Query Tool)                     │ (Mutating / High-Impact Tool)
      │                                            │
      ▼                                            ▼
[Execute Read Operation]            [Generate ApprovalRequest (Status: PENDING)]
      │                                            │
      │                                     [Manager Review: APPROVE / REJECT]
      │                                            │
      │                                            ▼ (If Approved)
      │                                     [Execute State Mutation]
      │                                            │
      └─────────────────────┬──────────────────────┘
                            ▼
               [Write Immutable AuditLog]
```

### 5.1 Tool Categorization & Permission Tiers

| Tool Name | Tool Category | Required RBAC Permission | Side Effects / Mutation | Human Approval Required? |
|---|---|---|---|:---:|
| `read_sales_summary` | Read-Only Query | `retail.view_order` | None | **NO** |
| `query_nearby_technicians` | Read-Only GIS Query | `service.view_employee` | None | **NO** |
| `retrieve_policy_documents`| Read-Only Knowledge | `knowledge.view_document` | None | **NO** |
| `get_forecast_trends` | Read-Only ML Query | `forecasting.view_forecast`| None | **NO** |
| `dispatch_technician` | Mutating Action | `service.assign_task` | Updates Task assignment | **YES (Manager)** |
| `update_order_status` | Mutating Action | `retail.change_order` | Modifies financial status | **YES (Manager)** |
| `apply_promotional_rule` | Mutating Action | `retail.change_product` | Changes product pricing | **YES (Admin)** |

### 5.2 Zero Unchecked Mutations Invariant
**No high-impact mutation may execute directly from an LLM-generated tool call.** Every state change requires explicit human manager confirmation through an `ApprovalRequest` record.

### 5.3 Technical References (Phase 10 Implementation)
- Detailed Recommendation Engine specification: [docs/recommendations.md](file:///d:/ai_business_platform/docs/recommendations.md)
- Tool Registry and Calling protocol: [docs/tool-calling.md](file:///d:/ai_business_platform/docs/tool-calling.md)
- Approval workflow and idempotency governance: [docs/approval-workflow.md](file:///d:/ai_business_platform/docs/approval-workflow.md)
