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

### 2.2 Grounding & Fallback Invariant
- **Fallback Rule**: If no retrieved chunk meets `similarity_threshold`, the assistant is strictly instructed to respond: *"Dữ liệu tài liệu hiện tại không đủ thông tin để trả lời chính xác câu hỏi này"* rather than hallucinating.
- **Tenant Boundary**: All vector queries join with `knowledge_base__workspace_id = active_workspace_id`.

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
- **Offline / Background Execution**: Model training is executed via Django management commands or background workers, never inside synchronous HTTP request loops.

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
