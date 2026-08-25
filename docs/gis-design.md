# Spatial GIS Architecture & Operational Analytics Design

## 1. GIS Vision & Scope in V1

In this platform, **GIS is an active business operations engine**, not decorative background map art. Spatial calculations directly drive territory revenue comparisons, technician dispatch decisions, and customer density insights.

### V1 Boundaries (Strictly Enforced)
- **Geometry Type**: 2D Point Geometries (`PointField(srid=4326, spatial_index=True)` representing `(longitude, latitude)` in WGS84).
- **Spatial Backend**: PostGIS 3.6 with GiST (Generalized Search Tree) spatial indexing.
- **Frontend Mapping**: Leaflet.js with OpenStreetMap tiles and lightweight GeoJSON layers.
- **Explicit Exclusions**: No raster analysis, remote sensing satellite imagery processing, or custom multi-modal road routing graphs in V1. Geodesic distance (great-circle) via PostGIS is standard.

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

### 3.1 Proximity & Radius Search ($ST\_DWithin$)
Finds all entities located within a specified radius (in meters) from an origin point.
- **Use Case**: Find all available technicians within 10 km of a critical service request.
- **GeoDjango Query Pattern**:
  ```python
  from django.contrib.gis.measure import D
  from apps.service_ops.models import Employee

  nearby_technicians = Employee.objects.filter(
      workspace=active_workspace,
      is_available=True,
      current_location__dwithin=(service_request.location, D(km=10))
  )
  ```

### 3.2 Geodesic Distance Matrix ($ST\_Distance$)
Computes the true spheroidal distance (in meters or kilometers) between origin and candidate points, ordering results from closest to furthest.
- **Use Case**: Rank candidate technicians by proximity to incident site.
- **GeoDjango Query Pattern**:
  ```python
  from django.contrib.gis.db.models.functions import Distance

  ranked_employees = Employee.objects.filter(
      workspace=active_workspace,
      is_available=True
  ).annotate(
      distance_to_site=Distance("current_location", service_request.location)
  ).order_by("distance_to_site")
  ```

### 3.3 Bounding Box & Regional Filtering ($ST\_MakeEnvelope$ / BBox)
Filters points that fall inside the current viewport bounding box of the user's interactive Leaflet map.
- **GeoDjango Query Pattern**:
  ```python
  from django.contrib.gis.geos import Polygon

  bbox = Polygon.from_bbox((min_lon, min_lat, max_lon, max_lat))
  visible_customers = Customer.objects.filter(
      workspace=active_workspace,
      location__within=bbox
  )
  ```

### 3.4 Regional Aggregation & Business Heatmaps
Aggregates sales revenue and order counts grouped by administrative regions or spatial grids.
- **Retail Use Case**: Sum total revenue for all orders where customer location falls within District 1 vs District 7.
- **Service Use Case**: Identify service request hotspots to recommend strategic technician placement.

---

## 4. Frontend GIS Presentation (Leaflet.js)

### 4.1 Map Architecture
- **Base Tile Provider**: OpenStreetMap (`https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`).
- **Data Exchange**: High-performance GeoJSON endpoints (`/api/v1/gis/layers/...`) returning FeatureCollections with embedded properties (revenue, status, priority, technician workload).
- **Layer Controls**:
  1. *Retail Workspace*: Branch Markers (with revenue popup) + Customer Distribution Dots + Regional Outlines.
  2. *Service Workspace*: Incident Markers (color-coded by priority/SLA) + Technician Markers (pulsing status) + Dynamic Proximity Circles (5km, 10km radii).

```text
[Leaflet Map Container]
   ├── Base Tile Layer (OSM)
   ├── LayerGroup: Branch Points (Custom Icons + Revenue Badges)
   ├── LayerGroup: Service Request Markers (Red = Critical, Orange = High)
   ├── LayerGroup: Active Technicians (Blue Marker + Proximity Radius Circle)
   └── Interactive Popup: [Trigger AI Recommendation / Dispatch]
```
