# REST API Conventions & Standards

## 1. Core Principles & Base URL

All programmatic API endpoints follow RESTful design principles and are served under a standardized versioned prefix:

$$\mathbf{Base\ URL}: \texttt{/api/v1/}$$

### Global Headers
- `Content-Type: application/json`
- `Accept: application/json`
- `Authorization: Token <token_key>` (for DRF Token Auth) OR standard Session Cookie (for Web UI / AJAX calls)
- `X-Workspace-ID: <workspace_uuid>` (Mandatory header to explicitly scope tenancy)

---

## 2. Resource Naming & HTTP Methods

### URI Guidelines
- Use **plural lowercase nouns** separated by hyphens (kebab-case) for resources:
  - `/api/v1/products/`
  - `/api/v1/service-requests/`
  - `/api/v1/forecast-models/`
  - `/api/v1/approval-requests/`

### HTTP Method Semantics
| Method | Intent | Expected Status Code |
|---|---|---|
| `GET` | Retrieve single resource or paginated collection | `200 OK` |
| `POST` | Create a new entity or trigger a dedicated operation | `201 Created` / `200 OK` |
| `PUT` | Complete replacement of a resource | `200 OK` |
| `PATCH` | Partial update of resource fields | `200 OK` |
| `DELETE` | Delete or archive a resource | `204 No Content` |

---

## 3. Standardized Response Envelopes

### 3.1 Paginated Collection Response (`200 OK`)
```json
{
  "count": 142,
  "next": "http://127.0.0.1:8000/api/v1/orders/?page=2",
  "previous": null,
  "page_size": 20,
  "results": [
    {
      "id": 1,
      "order_number": "ORD-20260825-001",
      "customer_code": "CUST_01",
      "order_date": "2026-08-25",
      "total_amount": "1500000.00",
      "status": "COMPLETED"
    }
  ]
}
```

### 3.2 Single Entity / Mutation Response (`201 Created` / `200 OK`)
```json
{
  "success": true,
  "message": "Resource created successfully.",
  "data": {
    "id": 104,
    "request_number": "SR-2026-089",
    "title": "Air conditioning unit cooling failure",
    "priority": "HIGH",
    "status": "NEW"
  }
}
```

### 3.3 AI Tool Mutation & Approval Request Response (`202 Accepted` / `200 OK`)
When an AI assistant or user action initiates a mutating operation that requires human review:
```json
{
  "success": true,
  "requires_approval": true,
  "message": "Action proposed by AI requires human manager approval.",
  "data": {
    "approval_request_id": "c7a81234-5678-4321-abcd-ef0123456789",
    "action_type": "DISPATCH_TECHNICIAN",
    "status": "PENDING",
    "payload": {
      "service_request_id": 104,
      "employee_id": 12,
      "technician_name": "Nguyen Van Nam",
      "distance_km": 3.2
    }
  }
}
```

### 3.4 Standardized Error Response (`400 Bad Request` / `422 Unprocessable`)
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Invalid input payload.",
    "details": [
      {
        "field": "unit_price",
        "message": "Unit price must be a positive decimal greater than 0.00."
      }
    ]
  }
}
```

---

## 4. Query Parameter Conventions

### 4.1 Filtering & Search
- Text Search: `?search=hvac` (performs full-text / trigram match across relevant fields).
- Exact Match: `?status=COMPLETED&branch=2`
- Date Ranges: `?date_from=2026-08-01&date_to=2026-08-25`

### 4.2 Spatial Proximity Queries (GIS)
- Radius Search: `?lat=10.7769&lon=106.7009&radius_km=5.0`
- Bounding Box: `?bbox=106.65,10.75,106.75,10.82` (minLon, minLat, maxLon, maxLat)

### 4.3 Sorting & Ordering
- Ascending: `?ordering=order_date`
- Descending: `?ordering=-total_amount`

---

## 5. Primary API Endpoint Directory (V1 Roadmap)

### Authentication & Workspace
- `POST /api/v1/auth/login/` (Session / Token exchange)
- `POST /api/v1/auth/logout/` (Flush session and revoke DRF token)
- `GET  /api/v1/auth/me/` (Retrieve caller identity, active workspace & permissions)
- `GET  /api/v1/workspaces/` (List accessible workspaces and assigned roles)
- `POST /api/v1/workspaces/switch/` (Switch active tenant context in session)
- `GET  /api/v1/workspaces/current/` (Retrieve currently active workspace context)

### Retail Operations
- `GET, POST    /api/v1/retail/products/`
- `GET, POST    /api/v1/retail/orders/`
- `GET          /api/v1/retail/analytics/revenue-timeseries/`
- `GET          /api/v1/retail/branches/`

### Service Operations
- `GET, POST    /api/v1/service-ops/services/` (Service catalog listing & creation with categories)
- `GET, PATCH   /api/v1/service-ops/services/{id}/`
- `GET, POST    /api/v1/service-ops/employees/` (Technicians directory with hourly rates & skills)
- `GET, POST    /api/v1/service-ops/slas/` (Deterministic SLA policies per priority tier)
- `GET, POST    /api/v1/service-ops/requests/` (Incident tickets)
- `GET          /api/v1/service-ops/requests/{id}/`
- `GET          /api/v1/service-ops/requests/{id}/cost/` (Aggregated labor cost & ticket cost breakdown)
- `POST         /api/v1/service-ops/requests/{id}/assign/`
- `POST         /api/v1/service-ops/requests/{id}/start|resolve|close|cancel/`
- `GET, POST    /api/v1/service-ops/tasks/`
- `POST         /api/v1/service-ops/tasks/{id}/start|complete|cancel/`
- `GET, POST    /api/v1/service-ops/tasks/{id}/labor/` (Labor tracking logs)
- `GET, POST    /api/v1/service-ops/labor-entries/` (Server-calculated labor cost records)
- `GET, POST    /api/v1/service-ops/schedules/` (Technician dispatch slots with overlap checks)
- `GET          /api/v1/service-ops/analytics/overview/` (KPI summary: tickets, labor cost, SLA, categories)
- `GET          /api/v1/service-ops/analytics/workload/` (Deterministic technician workload rankings)
- `GET          /api/v1/service-ops/analytics/sla/` (SLA compliance metrics)

### GIS Spatial & Proximity Analytics (Phase 5)
- `GET /api/v1/gis/retail/branches/` (Store network GeoJSON with sales & order KPIs)
- `GET /api/v1/gis/retail/customers/` (Customer density GeoJSON with PII protection)
- `GET /api/v1/gis/retail/revenue/` (Branch spatial revenue rankings and percentage share)
- `GET /api/v1/gis/service/tickets/` (Incident ticket GeoJSON with priority, category & SLA countdown)
- `GET /api/v1/gis/service/technicians/` (Field technician GeoJSON with skills & hourly rates)
- `GET /api/v1/gis/service/nearby-technicians/` (Proximity candidate search: `?request_id=<id>&radius_km=5`)
- `GET /api/v1/gis/service/coverage/` (Technician service coverage radius envelopes GeoJSON)

### Data Integration & Ingestion (Phase 6)
- `GET, POST    /api/v1/integration/data-sources/` (List / Register external data sources)
- `GET, PATCH, DELETE /api/v1/integration/data-sources/{id}/`
- `POST         /api/v1/integration/imports/preview/` (Pre-import schema preview & type inference)
- `GET, POST    /api/v1/integration/import-jobs/` (List / Trigger batch ingestion job)
- `GET          /api/v1/integration/import-jobs/{id}/` (Job execution progress & counters)
- `GET          /api/v1/integration/import-jobs/{id}/raw-records/` (Paginated staged RawImportRecords)
- `GET          /api/v1/integration/import-jobs/{id}/errors/` (Validation error breakdown)

### Mock External Partner Feeds (Phase 6)
- `GET /api/v1/mock-external/retail/orders/` (Vietnamese schema partner orders feed)
- `GET /api/v1/mock-external/retail/customers/` (External customer CRM records)
- `GET /api/v1/mock-external/retail/products/` (External ERP catalog records)
- `GET /api/v1/mock-external/service/tickets/` (External helpdesk ticket feed)
- `GET /api/v1/mock-external/service/technicians/` (External subcontractor directory)

### Data Mapping Engine & Standard Data Model (Phase 7)
- `GET, POST    /api/v1/mapping/profiles/` (List / Create mapping profile)
- `GET, PATCH, DELETE /api/v1/mapping/profiles/{id}/` (Retrieve / Update / Delete profile)
- `GET          /api/v1/mapping/profiles/{id}/fields/` (Discover source columns and canonical target fields)
- `POST         /api/v1/mapping/profiles/{id}/rules/` (Add mapping rule to profile)
- `PATCH, DELETE /api/v1/mapping/profiles/{id}/rules/{rule_id}/` (Update / Delete rule or trigger `ACCEPT_AI` / `REJECT_AI`)
- `POST         /api/v1/mapping/preview/` (Read-only simulation preview on staged rows)
- `POST         /api/v1/mapping/apply/` (Atomic transactional commit to canonical domain tables)
- `POST         /api/v1/mapping/ai-suggest/` (AI-assisted schema recommendation with confidence scores)

### AI Knowledge Assistant & Grounded RAG (Phase 8)
- `POST   /api/v1/ai/chat/` (Grounded Q&A: Ingested documents + Controlled read-only telemetry tools + Citations)
- `GET    /api/v1/ai/sessions/` (List conversation sessions for authenticated user)
- `POST   /api/v1/ai/sessions/` (Create new conversation session)
- `GET    /api/v1/ai/sessions/{id}/` (Retrieve conversation messages and citations)
- `GET, POST /api/v1/knowledge/bases/` (List / Create workspace knowledge bases)
- `GET, DELETE /api/v1/knowledge/bases/{id}/` (Retrieve / Delete knowledge base)
- `GET, POST /api/v1/knowledge/documents/` (List documents / Upload & ingest PDF, DOCX, TXT, MD)
- `GET, DELETE /api/v1/knowledge/documents/{id}/` (Retrieve document metadata / Delete document and chunks)
- `POST   /api/v1/knowledge/documents/{id}/reindex/` (Re-parse, re-chunk and re-embed document)
- `GET    /api/v1/knowledge/documents/{id}/chunks/` (Inspect chunk splits, vectors and metadata)

### Forecast & Decisions (Phases 9 & 10)
- `GET  /api/v1/forecasting/predictions/` (XGBoost forecasted trends)
- `GET  /api/v1/recommendations/` (Actionable decision recommendations)
- `POST /api/v1/approvals/{id}/decide/` (Manager APPROVE/REJECT action)

### System & Audit
- `GET /api/v1/notifications/`
- `GET /api/v1/audit/logs/`
