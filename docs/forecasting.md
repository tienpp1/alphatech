# Predictive Analytics & XGBoost Forecasting

## 1. Overview & Business Problem

Modern multi-tenant business platforms require forward-looking visibility to assist staffing, inventory prep, cash-flow projections, and operational readiness. 

The **Predictive Analytics & Forecasting Module** (`apps.forecasting`) provides controlled, reproducible machine learning forecasting powered by **XGBoost**. It translates historical operational transactions into chronological time-series, extracts autoregressive and calendar features, trains gradient-boosted tree regressors, benchmarks performance against naive persistence baselines, and generates recursive multi-step forecasts with approximate 95% prediction bands based on historical test residual standard deviation.

These forecasts serve as analytical assets that feed directly into downstream recommendation and decision-support systems (Phase 10).

---

## 2. Supported Forecasting Targets

Target metrics are strictly categorized by domain and enforced per workspace:

| Target Identifier | Domain | Description | Source Transaction & Aggregation |
| :--- | :--- | :--- | :--- |
| `RETAIL_REVENUE` | **Retail** | Daily or weekly gross monetary sales (VND) | Completed retail orders (`OrderStatus.COMPLETED`), grouped by `order_date`, summing `total_amount`. |
| `RETAIL_ORDER_VOLUME` | **Retail** | Daily or weekly incoming order count | Non-cancelled retail orders (`status != CANCELLED`), grouped by `order_date`, counting orders. |
| `SERVICE_TICKET_VOLUME` | **Service Ops** | Daily or weekly service incident/ticket count | Service requests (`apps.service_ops.ServiceRequest`), grouped by creation date (`created_at__date`), counting tickets. |

### Domain Validation Rule
- Workspaces with `workspace_type = RETAIL` can only configure, train, or query `RETAIL_REVENUE` and `RETAIL_ORDER_VOLUME`.
- Workspaces with `workspace_type = SERVICE` can only configure, train, or query `SERVICE_TICKET_VOLUME`.
- Any attempt to cross-train or request invalid targets raises an explicit HTTP 400 Validation Error.

---

## 3. Time-Series Dataset Construction & Anti-Leakage Invariants

### 3.1 Gap-Filling via Continuous Date Reindexing
Real-world operational transactional data contains gaps (days with zero sales or zero service tickets). Naive querying produces discontinuous dates that ruin lag calculations.
1. The historical time series is fetched from the database, grouped by date.
2. The minimum and maximum transaction dates are determined.
3. A continuous calendar date index is generated using `pandas.date_range(start, end, freq="D")`.
4. The series is reindexed over this range, filling missing days with `0.0` (zero revenue, zero orders, or zero tickets).

### 3.2 Feature Engineering Pipeline
Features are derived deterministically in `apps.forecasting.features.build_feature_dataframe`:

| Feature Name | Description | Formula / Logic |
| :--- | :--- | :--- |
| `lag_1` | Previous day's actual value | $y_{t-1}$ |
| `lag_7` | Value from 7 days prior (seasonal weekly cycle) | $y_{t-7}$ |
| `lag_14` | Value from 14 days prior | $y_{t-14}$ |
| `rolling_mean_7` | 7-day rolling average | $\frac{1}{7} \sum_{i=1}^7 y_{t-i}$ |
| `rolling_std_7` | 7-day rolling volatility / standard deviation | $\sqrt{\frac{1}{7} \sum_{i=1}^7 (y_{t-i} - \bar{y})^2}$ |
| `rolling_mean_14` | 14-day rolling average | $\frac{1}{14} \sum_{i=1}^{14} y_{t-i}$ |
| `day_of_week` | Day of week integer | $0 = \text{Monday}, \dots, 6 = \text{Sunday}$ |
| `day_of_month` | Calendar day of month | $1 \dots 31$ |
| `month` | Calendar month | $1 \dots 12$ |
| `week_of_year` | ISO calendar week number | $1 \dots 53$ |
| `is_weekend` | Weekend binary indicator | $1$ if Saturday/Sunday, else $0$ |

### 3.3 Leakage Prevention Invariant
**Strict Invariant**: A forecast made at timestamp $t$ must never use actual transaction values from timestamp $t$ or later.
All rolling features are computed using `series.shift(1).rolling(window)` so that the calculation window only covers observations up to $t-1$. Initial rows containing NaN from lag lookbacks are trimmed (`dropna()`).

---

## 4. Chronological Splitting & Training Workflow

### 4.1 Chronological Split
Time-series data is never randomly partitioned or shuffled. The dataset is divided strictly chronologically:
- **Train Set**: First $80\%$ of dates ($\text{date} < t_{\text{split}}$).
- **Test Set**: Final $20\%$ of dates ($\text{date} \ge t_{\text{split}}$).

### 4.2 XGBoost Regressor Configuration
Model hyperparameters are persisted per workspace in `ForecastModelConfig`:
```python
model = xgb.XGBRegressor(
    n_estimators=100,
    max_depth=4,
    learning_rate=0.08,
    subsample=0.85,
    colsample_bytree=0.85,
    objective="reg:squarederror",
    random_state=42,
    n_jobs=-1,
)
```

### 4.3 Evaluation Metrics & Persistence Baseline Comparison
Every trained model is evaluated against the held-out test split:
1. **MAE (Mean Absolute Error)**: $\frac{1}{n} \sum |y_i - \hat{y}_i|$
2. **RMSE (Root Mean Squared Error)**: $\sqrt{\frac{1}{n} \sum (y_i - \hat{y}_i)^2}$
3. **Non-Zero Masked MAPE (Mean Absolute Percentage Error)**:
   $$\text{MAPE} = \frac{1}{|K|} \sum_{i \in K} \left| \frac{y_i - \hat{y}_i}{y_i} \right| \times 100\% \quad \text{where } K = \{i \mid |y_i| > 10^{-3}\}$$

#### Critical Metric Limitations (MAPE):
- **Non-Zero Masking**: Standard MAPE divides by actual value $y_i$. To prevent infinite percentage distortion on zero-demand/zero-incident days, MAPE is computed strictly over non-zero actual observations ($|y_i| > 10^{-3}$).
- **Instability on Low-Count Targets**: Percentage error metrics inherently inflate when actual values are small positive integers (e.g. 1 or 2 tickets). An absolute error of just 1 ticket ($|1 - 2| / 1$) yields a 100% error rate.
- **Service Ticket Volume MAPE**: Because daily service ticket volume in typical branch operations is small and count-based, the Service Ticket Volume MAPE is relatively high (**62.58%**).
- **Metric Guidance**: For discrete, count-based service operations, **MAE and RMSE must be emphasized** over MAPE as primary indicators of practical model fit.

4. **$R^2$ Score**: Coefficient of determination.
5. **Naive Persistence Baseline**:
   - Compares predictions against seasonal lag ($y_t = y_{t-7}$) or previous step ($y_{t-1}$).
   - Calculates percentage improvement:
     $$\text{Improvement} = \frac{\text{MAE}_{\text{naive}} - \text{MAE}_{\text{xgb}}}{\text{MAE}_{\text{naive}}} \times 100\%$$

#### Benchmark Evaluation Summary:
*Note: Results are dataset-dependent. On this seeded benchmark dataset, models performed better than the naive baseline across all three operational targets:*

| Model Target | XGBoost MAE | Naive Baseline MAE | MAE Improvement (%) | XGBoost RMSE | Naive Baseline RMSE | RMSE Improvement (%) | XGBoost MAPE |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Retail Revenue** (`abc-retail`) | **635,078 VND** | 832,234 VND | **+23.69%** | **750,005 VND** | 1,029,425 VND | **+27.14%** | **31.85%** |
| **Retail Order Volume** (`abc-retail`) | **0.65 orders** | 0.81 orders | **+19.75%** | **0.88 orders** | 1.12 orders | **+21.43%** | **34.45%** |
| **Service Ticket Volume** (`xyz-service`) | **0.94 tickets** | 1.14 tickets | **+17.54%** | **1.21 tickets** | 1.48 tickets | **+18.24%** | **62.58%** |

---

## 5. Recursive Multi-Step Horizon Forecasting

To project 14 consecutive future days:
1. The trained model is loaded from disk.
2. The initial state is seeded using the most recent historical window.
3. For each future day $t+1, t+2, \dots, t+H$:
   - Dynamic lag features are synthesized using past actuals or previous recursive predictions.
   - Calendar features (`day_of_week`, `is_weekend`, `month`, etc.) are computed for the future date.
   - The model predicts $\hat{y}_t$.
   - The prediction is clamped to non-negative values ($\hat{y}_t = \max(0, \hat{y}_t)$).
   - Approximate 95% prediction bands based on historical test residual standard deviation:
     $$\text{Lower Bound} = \max(0, \hat{y}_t - 1.96 \cdot \sigma_{\text{residual}} \cdot \sqrt{1 + 0.05(h-1)})$$
     $$\text{Upper Bound} = \hat{y}_t + 1.96 \cdot \sigma_{\text{residual}} \cdot \sqrt{1 + 0.05(h-1)}$$
     *(where $h = 1 \dots 14$ is the forecast step).*

#### Methodological & Uncertainty Disclaimers:
- **Uncertainty Visualization**: These bands serve as an intuitive uncertainty visualization based on historical test residuals.
- **Recursive Multi-Step Error Accumulation**: Because recursive multi-step forecasting feeds predicted values back as autoregressive inputs for subsequent steps ($t+1 \to t+2$), prediction errors may compound over the horizon.
- **Not a Formally Calibrated Interval**: This heuristic is an approximate prediction band, not a formally calibrated probabilistic prediction interval (e.g. from conformal prediction or quantile loss regression), and does not represent a guaranteed coverage probability.
   - The projected point is appended into the time series to provide autoregressive inputs for subsequent steps.

---

## 6. Model Artifact Storage & Security

- **Serialization**: Native XGBoost JSON format (`model.save_model(...)` and `model.load_model(...)`).
- **Storage Location**: `ml_models/forecasting/model_<run_id>.json`.
- **Path Traversal Prevention**: The artifact loader verifies that the resolved canonical path starts with the configured `FORECASTING_ARTIFACTS_DIR`. Attempts to access paths outside this directory raise immediate security exceptions.

---

## 7. Multi-Tenant Architecture & RBAC

- **Data Isolation**: All models (`ForecastModelConfig`, `ForecastRun`, `ForecastResult`) inherit from `WorkspaceScopedModel`. Every query filters by `workspace = current_workspace`.
- **Permissions**:
  - `forecasting.view_forecast`: View configurations, training runs, metrics, and forecast charts.
  - `forecasting.manage_forecast`: Create/edit model configurations and trigger model training runs.
- **Audit Logging**: Successful training triggers create an immutable audit record in `apps.audit.models.AuditLog` with actor ID, target type, run ID, and evaluation metrics.

---

## 8. REST API & UI Reference

### 8.1 API Endpoints (`/api/v1/forecasting/`)

| Method | Endpoint | Description | Required Permission |
| :--- | :--- | :--- | :--- |
| `GET` | `/models/` | List model configs for workspace | `forecasting.view_forecast` |
| `POST` | `/models/` | Create a custom model config | `forecasting.manage_forecast` |
| `GET` | `/models/<id>/` | Retrieve model config details | `forecasting.view_forecast` |
| `PATCH` | `/models/<id>/` | Update hyperparameters | `forecasting.manage_forecast` |
| `DELETE` | `/models/<id>/` | Delete custom model config | `forecasting.manage_forecast` |
| `GET` | `/runs/` | List historical training runs | `forecasting.view_forecast` |
| `GET` | `/runs/<id>/` | Retrieve run details & metrics | `forecasting.view_forecast` |
| `POST` | `/train/` | Trigger model training run (sync or async) | `forecasting.manage_forecast` |
| `GET` | `/results/` | Query forecast points for a run | `forecasting.view_forecast` |
| `GET` | `/chart-data/` | Unified Chart.js payload (historical, forecast, CI bands, importances) | `forecasting.view_forecast` |

### 8.2 CLI Management Command
```powershell
python manage.py train_forecast --workspace abc-retail --target RETAIL_REVENUE --horizon 14
```

### 8.3 Web UI Dashboard (`/forecasting/`)
- Accessible via the top navigation bar (`📈 Forecasting`) in Retail and Service workspaces.
- **KPI Summary Cards**: Latest training run status, MAE, RMSE, MAPE, and baseline relative improvement.
- **Interactive Chart.js Visualization**: Combined historical actuals, 14-day future forecast, and shaded approximate 95% prediction bands based on historical test residual standard deviation.
- **Feature Importance Chart**: Top contributing features with explainability disclaimer.
- **Training History**: Status badge, parameters, metrics, duration, and user trigger metadata.
- **Training Modal**: Synchronous or non-blocking async training trigger directly from the browser.

---

## 9. Phase Scope Boundaries & Next Steps

### Strictly Out of Scope for Phase 9:
- Recommendation Engine (Reorder suggestions, staffing reallocation).
- Autonomous AI Agent / Tool Calling.
- Hungarian Algorithm (Bipartite matching).
- Isolation Forest (Anomaly detection).
- Multi-Agent Orchestration.
- RAG Vector Search modifications.
- Warehouse / inventory replenishment optimization.

### Next Phase: Phase 10 (Decision Support & Recommendation Engine)
In Phase 10, the predictions generated by Phase 9 (`ForecastResult`) will be consumed by deterministic rule-based algorithms and optimization heuristics (such as Hungarian bipartite matching and safety stock policies) to generate proactive business recommendations.
