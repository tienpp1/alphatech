# Đợt 11 — GIS public map evidence

Ngày: 15/09/2026. PostgreSQL/PostGIS local test database; provider requests are mocked or rejected intentionally.

## Items closed

| 52 | `test_radius_includes_point_at_measured_boundary` measures the PostGIS geodesic distance to a real branch and reuses that exact value as the radius; the branch is included. Interior/exterior radii and cross-workspace cases are also covered by the spatial/security suite. |

| Mục | Bằng chứng |
|---|---|
| 53 | Public branch serialization keeps missing/invalid coordinates as null, uses a valid GIS Point fallback, and excludes non-public fields. GIS security tests reject a member's cross-workspace request and protect customer location/PII by role. |
| 54 | Branch UI states radius as straight-line distance and route as driving distance; OSRM is used for route/table requests. Test asserts both labels and source text. |
| 55 | UI states “Không bảo đảm ngắn nhất tuyệt đối” and “không có dữ liệu kẹt xe trực tiếp”; JS labels results as provider-supplied and warns when not all branches have routes. No absolute shortest/traffic guarantee is made. |
| 58 | Nominatim public-provider attribution/limits and possible interruption are shown; mocked busy/failure tests return 429/503, `Retry-After`, truthful Vietnamese status, and the server rate gate/cache/cooldown are tested. |

## Validation

- `python manage.py test tests.test_public_geocoding tests.test_public_branch_finder tests.test_gis_spatial tests.test_gis_security tests.test_gis_service --settings=config.settings_evidence_test --keepdb --noinput`: **27 passed, 27.257s** after correcting one test assertion.
- `python manage.py test tests.test_public_branch_finder --settings=config.settings_evidence_test --keepdb --noinput`: **4 passed, 0.249s** after the final copy assertions.
- `python manage.py test tests.test_gis_spatial.PostGISSpatialServicesTests.test_radius_includes_point_at_measured_boundary --settings=config.settings_evidence_test --keepdb --noinput`: **1 passed, 0.221s**.
- Django check was clean during the same local verification; no migration was added.

## Not closed

- Item 56 (live Nominatim success) and 57 (device GPS denial/accuracy) require external provider/device evidence.
- Browser helper failed before opening a target (`failed to write kernel assets`, Windows error 3), so this batch contains no production UI claim.
