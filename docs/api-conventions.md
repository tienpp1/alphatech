# REST API Conventions & Standards

## 1. Core Principles & Base URL

All programmatic API endpoints follow RESTful design principles and are served under a standardized versioned prefix:

$$\mathbf{Base\ URL}: \texttt{/api/v1/}$$

### Global Headers
- `Content-Type: application/json`
- `Accept: application/json`
- `Authorization: Bearer <jwt_or_token>` (or Django Session Cookie)
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

### 3.3 Standardized Error Response (`400 Bad Request` / `422 Unprocessable`)
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
- `GET  /api/v1/workspaces/` (List accessible workspaces)
- `POST /api/v1/workspaces/switch/` (Switch active tenant context)

### Retail Operations
- `GET, POST    /api/v1/retail/products/`
- `GET, POST    /api/v1/retail/orders/`
- `GET          /api/v1/retail/analytics/revenue-timeseries/`
- `GET          /api/v1/retail/branches/`

### Service Operations
- `GET, POST    /api/v1/service-ops/requests/`
- `GET, PATCH   /api/v1/service-ops/tasks/`
- `GET          /api/v1/service-ops/employees/`
- `GET          /api/v1/service-ops/schedules/`

### GIS Spatial Layers
- `GET /api/v1/gis/layers/branches/` (GeoJSON FeatureCollection)
- `GET /api/v1/gis/layers/service-requests/` (GeoJSON FeatureCollection)
- `GET /api/v1/gis/layers/technicians/nearby/` (Proximity search GeoJSON)

### AI, Forecast & Decisions
- `POST /api/v1/ai/chat/` (RAG Q&A + Controlled Tool Invocations)
- `GET  /api/v1/forecasting/predictions/` (XGBoost forecasted trends)
- `GET  /api/v1/recommendations/` (Actionable decision recommendations)
- `POST /api/v1/approvals/{id}/decide/` (Manager APPROVE/REJECT action)

### System & Audit
- `GET /api/v1/notifications/`
- `GET /api/v1/audit/logs/`
