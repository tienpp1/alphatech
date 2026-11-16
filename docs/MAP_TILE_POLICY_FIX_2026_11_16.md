# Map tile policy repair — 16 November 2026

## Symptom and cause boundary

The owner reported OSM 403 policy-block images on internal GIS pages while
branch/customer markers still rendered. All three Leaflet surfaces were checked:
retail GIS, service GIS and the public branch finder. Legacy/canonical internal
routes share the same two templates; there is no second map implementation.

The production public response has `Referrer-Policy: same-origin`. Internal
tile layers had no per-image override, suppressing cross-origin Referer, and
used the old `{s}.tile.openstreetmap.org` pattern. This violates the browser
Referer requirement of the [OSM tile policy](https://operations.osmfoundation.org/policies/tiles/)
and is a concrete code defect consistent with the reported block. Without a
successful live tile response, this is not proof of every provider-side reason
for a particular 403 or that a prior block has been lifted.

## Minimal repair and preserved boundaries

- Internal retail/service layers now use
  `https://tile.openstreetmap.org/{z}/{x}/{y}.png`.
- Leaflet 1.9.4 `referrerPolicy: 'origin'` applies only to tile images. The
  provider receives site origin, not an internal path, query or workspace ID.
  See the [Leaflet option](https://leafletjs.com/reference-1.9.4.html#tilelayer-referrerpolicy).
- Keep OSM contributors attribution and maxZoom 19. Public branch finder
  already had these settings; its existing behavior is now regression-tested.
- Global same-origin policy, CSP, workspace/RBAC, escaping, API requests,
  markers/coordinates and customer data remain unchanged. No provider switch,
  proxy, identity spoofing, cache bypass, scraping or prefetch was introduced.
- No schema, migration, business-data change, paid resource or97-ledger change.

## Verification so far

Evidence directory: `output/map_tile_fix_20261116/` on the operator workstation.

- RED: 27 focused JavaScript tests, two expected failures at the internal tile
  boundary before the fix; existing assertions were retained (`red.log`).
- GREEN: same command, 27/27 passed, no skips, 664.6535 ms (`green_js.log`).
- Aggregate JavaScript: 76/76 passed, no skips, 3285.5167 ms (`all_js.log`).
- Independent read-only reviewer found no critical/important regressions and
  reran the two changed test files: 15/15 passed. This is not an additional
  full-suite run or live map proof.
- Primary dirty workspace received only the two tile blocks and existing public
  regression file patch; its branch-finder checks passed 16/16. No broad merge
  or replacement of other agents' work was performed.
- Full Django verification: 1614/1614 tests OK, no skips, 746.843 seconds;
  isolated local PostGIS TEST database destroyed successfully, process exit 0
  (`full.log`). Fast hasher and legacy fixture compatibility were test-process
  settings only; no production configuration change.
- Five standalone collaboration transport groups also passed. Known-pattern
  secret scan checked 889 source files, zero findings (`secret-scan.json`),
  not an exhaustive guarantee of secret absence.

## Browser and network limitation

Native browser/desktop tools failed during kernel-asset initialization. A
separate installed Chrome headless process rendered the actual two templates
with synthetic empty GeoJSON, not an authenticated production user session.
Real Leaflet emitted tile requests with the configured origin-only Referer,
no explicit cache bypass and no page JavaScript errors. These requests did
not load image bytes: local default DNS returned NXDOMAIN for the OSM host.
Public DNS diagnostics resolved that host successfully. No OS DNS, VPN, browser
privacy setting or TLS verification was changed.

`after-browser.json` and the blank-map screenshots establish request policy,
not successful basemap rendering. The owner agreed to test `/chi-nhanh/` using
phone 4G/5G after deployment. Actual visual UAT and release/CI receipts remain
separate gates; do not label them passed before observing their outcomes.
