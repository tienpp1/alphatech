# Spatial GIS Architecture & Operational Analytics Design

## 1. GIS Vision & Scope in V1

In this platform, **GIS is an active business operations engine**, not decorative background map art. Spatial calculations directly drive territory revenue comparisons, technician proximity dispatching, and customer density insights.

### V1 Boundaries (Strictly Enforced)
- **Geometry Type**: 2D Point Geometries (`PointField(srid=4326, spatial_index=True)` representing `(longitude, latitude)` in WGS84 coordinates).
- **Coordinate Convention**:
  - *PostGIS / GeoDjango*: `Point(longitude, latitude, srid=4326)` (where `x = longitude`, `y = latitude`).
  - *GeoJSON (RFC 7946)*: `coordinates: [longitude, latitude]`.
  - *Leaflet.js*: `[latitude, longitude]`.
- **Spatial Backend**: PostGIS 3.6 with GiST (Generalized Search Tree) spatial indexing.
- **Frontend Mapping**: Leaflet.js with OpenStreetMap tiles and lightweight GeoJSON layers.
- **Explicit Exclusions**: No raster analysis, remote sensing satellite imagery processing, or custom multi-modal road routing graphs in V1. Geodesic distance (spheroidal great-circle) via PostGIS is standard.
- **AI Scope Gate**: Automated AI recommendation scoring and autonomous dispatching belong to Phase 10. Phase 5 calculates and displays deterministic spatial proximity.

---

## 2. Spatial Entities Matrix

| Module | Entity | Spatial Field | SRID & Index | Business Purpose |
|---|---|---|---|---|
| **Retail** | `Branch` | `location` (Point) | 4326 (GiST) | Physical retail store coordinates for catchment analysis and regional revenue rollups. |
| **Retail** | `Customer` | `location` (Point) | 4326 (GiST) | Customer delivery address / primary location for density clustering. |
| **Service** | `ServiceRequest` | `location` (Point) | 4326 (GiST) | Exact incident site or asset breakdown location for dispatching. |
| **Service** | `Employee` | `current_location` (Point) | 4326 (GiST) | Real-time / last-known field technician coordinates for proximity dispatching. |

---

## 3. Core Spatial Queries & PostGIS Capabilities

### 3.1 Proximity & Radius Search
Finds all entities located within a specified radius (in kilometers/meters) from an origin point using spheroidal geodesic calculation on SRID 4326 geometries.
- **Use Case**: Find all available technicians within 5 km of a critical IT incident request.
- **GeoDjango Query Pattern** (`apps.gis.services.find_objects_within_radius`):
  ```python
  from django.contrib.gis.measure import D
  from django.contrib.gis.db.models.functions import Distance
  from apps.service_ops.models import Employee

  nearby_technicians = Employee.objects.filter(
      workspace=active_workspace,
      is_available=True,
  ).annotate(
      _spatial_dist=Distance("current_location", service_request.location)
  ).filter(_spatial_dist__lte=D(km=radius_km))
  ```

### 3.2 Geodesic Distance Matrix & Ordering ($ST\_Distance$)
Computes the true spheroidal distance (in meters or kilometers) between origin and candidate points, ordering results from closest to furthest.
- **Use Case**: Rank candidate technicians by proximity to incident site.
- **GeoDjango Query Pattern** (`apps.gis.services.calculate_distances`):
  ```python
  from django.contrib.gis.db.models.functions import Distance

  ranked_employees = Employee.objects.filter(
      workspace=active_workspace,
      is_available=True,
  ).annotate(
      distance=Distance("current_location", service_request.location)
  ).order_by("distance")
  ```

### 3.3 Bounding Box & Viewport Filtering ($ST\_Within$)
Filters points that fall inside the current viewport bounding box of the user's interactive Leaflet map.
- **GeoDjango Query Pattern** (`apps.gis.services.filter_by_bounding_box`):
  ```python
  from django.contrib.gis.geos import Polygon

  bbox = Polygon.from_bbox((min_lon, min_lat, max_lon, max_lat))
  bbox.srid = 4326
  visible_customers = Customer.objects.filter(
      workspace=active_workspace,
      location__within=bbox,
  )
  ```

### 3.4 Spatial Revenue Analytics
Aggregates sales revenue and order counts grouped by physical store branches and regions.
- **Retail Use Case**: Sum total revenue for all orders and compute branch market share percentages with spatial coordinates.

---

## 4. REST API Endpoint Specifications

All endpoints enforce Session/Token Authentication and strict workspace tenancy isolation (`X-Workspace-ID` header validation).

| Method | Endpoint | Description | Query Parameters | Response Format |
|---|---|---|---|---|
| `GET` | `/api/v1/gis/retail/branches/` | Retail store network with revenue & order KPIs | `start_date`, `end_date` | RFC 7946 GeoJSON FeatureCollection |
| `GET` | `/api/v1/gis/retail/customers/` | Customer geographic distribution (PII-protected) | `segment`, `bbox` | RFC 7946 GeoJSON FeatureCollection |
| `GET` | `/api/v1/gis/retail/revenue/` | Branch spatial revenue rankings & market share | `start_date`, `end_date` | JSON Analytical Breakdown |
| `GET` | `/api/v1/gis/service/tickets/` | Incident ticket locations with category & SLA status | `status`, `priority`, `category`, `bbox` | RFC 7946 GeoJSON FeatureCollection |
| `GET` | `/api/v1/gis/service/technicians/` | Field technician locations, workload & skills | `available_only`, `skill`, `bbox` | RFC 7946 GeoJSON FeatureCollection |
| `GET` | `/api/v1/gis/service/nearby-technicians/` | Proximity search for ticket candidate technicians | `request_id` (req), `radius_km`, `available_only`, `required_skill` | Ranked JSON Candidates with geodesic $km$ |
| `GET` | `/api/v1/gis/service/coverage/` | Technician service coverage radius envelopes | `radius_km` | RFC 7946 GeoJSON FeatureCollection |

---

## 5. Customer Data Privacy & Spatial PII Protection

Customer geographic coordinates and contact details are sensitive data. The GIS module implements field-level data masking:
- **Unprivileged Viewers (`gis.view_spatial_layers` only)**:
  - Customer name masked as `Customer <CODE>` (e.g. `Customer CUST-0001`).
  - Physical address masked as `Restricted (Address Protected)`.
  - Phone and Email fields omitted completely from GeoJSON properties.
- **Privileged Users (`gis.view_customer_locations` / `retail.manage_customer` / Admin)**:
  - Full customer name, phone number, email, and address are visible for authorized operations.

---

## 6. Frontend Leaflet GIS Dashboards

### 6.1 Retail GIS Dashboard (`/retail/gis/`)
- **Interactive Map**: Centered on Ho Chi Minh City with OpenStreetMap tiles.
- **Branch Markers**: Blue store pins with custom popups displaying realized revenue, order volume, average order value, and address.
- **Customer Layer**: Density dots color-coded by segment (Gold = VIP, Purple = Enterprise, Green = Standard).
- **Revenue Time Filter**: Dynamic date range buttons (`All time`, `Past 90 days`, `Past 30 days`, `Past 7 days`) recalculating branch revenue in real time.
- **Spatial Ranking Sidebar**: Real-time leaderboard ranking branches by spatial revenue and percentage share of total business.

### 6.2 Service Operations GIS Map (`/services/gis/`)
- **Incident Ticket Markers**: Pins color-coded by SLA priority (`Critical` = Red, `High` = Orange, `Medium` = Yellow, `Low` = Green) with SLA countdown, category badge, and client address.
- **Technician Markers**: Blue engineer pins displaying skills, workload score, hourly labor rate, and current status.
- **Service Coverage Envelopes**: Toggleable 5.0 km radius circles around active technicians.
- **Proximity Dispatch Inspector**: Clicking **"Find Nearby Technicians"** on any ticket executes a PostGIS proximity query, renders a radius envelope and geodesic connection lines on the map, and lists candidate technicians sorted by distance in the inspector drawer.

---

## 7. Realistic Seed Datasets (Ho Chi Minh City)

All demo entities use realistic WGS84 coordinates across Ho Chi Minh City districts:
- **Retail Branches**: District 1 (Nguyen Hue), District 7 (Phu My Hung), Binh Thanh (Pearl Plaza).
- **Retail Customers**: 60 distributed customer locations across D1, D3, D4, D7, Binh Thanh, Phu Nhuan.
- **Service Corporate Clients**: 25 enterprise clients (Landmark 81, Bitexco, Saigon Centre, Sunwah, Crescent Mall, FPT Hi-Tech Park, etc.).
- **Technicians**: 10 qualified IT engineers positioned across operational hubs.
