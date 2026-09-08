# Recommendation Engine & Operational Decision Support Specification

## 1. Architectural Mission
The Recommendation Engine provides explainable, deterministic operational guidance by combining:
1. **Current business data**: Retail orders, branch performance, service tickets, technician workloads.
2. **Spatial GIS analytics**: Geodesic distances, active technician assignments, radius queries.
3. **XGBoost forecasts**: Recursive 14-day predictions with uncertainty bands.
4. **Deterministic rule evaluation**: Hardcoded business logic thresholds without black-box inference.

The system adheres strictly to:
$$\text{DATA} \longrightarrow \text{ANALYSIS} \longrightarrow \text{RECOMMENDATION} \longrightarrow \text{HUMAN DECISION} \longrightarrow \text{CONTROLLED ACTION} \longrightarrow \text{AUDIT}$$

---

## 2. Recommendation Structure & Explainability Contract
Every recommendation record (`Recommendation`) inherits `WorkspaceScopedModel` and contains a mandatory structured explanation schema:

```json
{
  "what": "Clear description of the recommended operational action",
  "why": "Business reason and threshold trigger that caused this recommendation",
  "evidence": {
    "metrics": {},
    "forecast_values": {},
    "gis_candidates": {}
  },
  "expected_effect": "Operational objective and impact expected upon execution"
}
```

### Recommendation Status Lifecycle
- `PENDING`: Initial state upon deterministic rule generation. Awaiting manager review.
- `ACCEPTED`: Manager approved the recommendation. May proceed to controlled action execution.
- `REJECTED`: Manager dismissed the recommendation with documented reason.
- `EXPIRED`: System or rule invalidated the recommendation due to time lapse.

---

## 3. Deterministic Rules Catalogue

### Retail Rules (`evaluate_retail_recommendations`)
1. **Declining Branch Revenue**:
   - *Trigger*: Recent 7-day revenue $< 100,000,000$ VND or forecast MAE improvement $> 10\%$.
   - *Action*: Propose targeted promotional campaign or sales channel review.
2. **Low Order Volume Alert**:
   - *Trigger*: Order count over 7 days $< 10$ orders.
   - *Action*: Flag for customer engagement and marketing outreach.
3. **High Performing Branch Practice Sharing**:
   - *Trigger*: 7-day branch revenue $\ge 150,000,000$ VND.
   - *Action*: Standardize operating procedures to replicate success across network.

### Service Rules (`evaluate_service_recommendations`)
1. **SLA At-Risk Ticket Alert**:
   - *Trigger*: Tickets in `OPEN` / `ASSIGNED` / `IN_PROGRESS` with age $> 12$ hours or priority `HIGH` / `CRITICAL`.
   - *Action*: Prioritize urgent dispatch to avoid contractual breach.
2. **Nearby Technician Candidate Dispatch**:
   - *Trigger*: Unassigned or at-risk ticket requiring field service dispatch.
   - *Action*: Query GIS proximity within 25km radius and compute transparent candidate score.
3. **Technician Workload Imbalance**:
   - *Trigger*: Technician assigned to $\ge 3$ active tasks simultaneously.
   - *Action*: Recommend workload rebalancing to avoid fatigue and missed SLAs.

---

## 4. Transparent Technician Candidate Scoring Formula
The ranking of technician dispatch candidates strictly avoids black-box ML and uses an explainable weighted multi-criteria formula:

$$\text{Score} = w_{\text{dist}} \times S_{\text{dist}} + w_{\text{workload}} \times S_{\text{workload}} + w_{\text{skill}} \times S_{\text{skill}}$$

Where:
- $w_{\text{dist}} = 0.40$
- $w_{\text{workload}} = 0.40$
- $w_{\text{skill}} = 0.20$
- $S_{\text{dist}} = \max(0, 100 - \text{distance\_km} \times 10)$
- $S_{\text{workload}} = \max(0, 100 - \text{active\_tasks} \times 20)$
- $S_{\text{skill}} = 100.0$ if skills match required service category, else $50.0$.

### Multi-Criteria Enhancements & Hard Gating:
1. **Hard Availability Gate**:
   If a technician is inactive or currently flagged unavailable (`is_available=False`), their total score is gated to `0.0` with `availability_score: 0.0`.
2. **Cost Efficiency & Labor Rate**:
   Technicians record their standard hourly rate (`hourly_labor_rate`). The subscore $S_{\text{rate}} = \max(0, 100 - \frac{\text{rate}}{5,000})$ is computed for transparent cost analysis.
3. **SLA Urgency Factor**:
   When a service request is near SLA breach or marked `CRITICAL` / `HIGH`, `sla_urgency_factor > 1.0` prioritizes candidates with highest skill and nearest proximity to prevent contractual penalty.

All weights remain strictly deterministic, linear, and completely explainable in the recommendation `EVIDENCE` JSON payload.

---

## 5. Security & Multi-Tenancy
- **Strict Tenancy Isolation**: All recommendation queries filter by `Recommendation.objects.for_workspace(workspace)`.
- **RBAC**: Requires `recommendations.view_recommendation` to inspect and `recommendations.manage_recommendation` to accept/reject or trigger rule evaluation.
- **Audit Logging**: Every evaluation run and acceptance/rejection writes an immutable entry to `AuditLog`.
