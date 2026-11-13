# Map assets and tile usage

- Leaflet1.9.4, ©Vladimir Agafonkin/CloudMade/contributors, BSD2-Clause; full license LEAFLET-LICENSE.txt. JS/CSS vendored from https://unpkg.com/leaflet@1.9.4/ (no runtime CDN dependency).
- Online raster tiles: https://tile.openstreetmap.org/{z}/{x}/{y}.png ; ©OpenStreetMap contributors, https://www.openstreetmap.org/copyright . Tile policy https://operations.osmfoundation.org/policies/tiles/ reviewed2026-11-12. Standard interactive browser requests/caching only; no bulk/offline download, prefetch or server tile harvesting. Attribution remains visible. Availability is not guaranteed; no paid key.
- land.json reuses the project's already-audited simplified Natural Earth public-domain country geometry (127 features); offline fallback has coastlines/borders/continent labels and explicitly lacks street detail. It is rendered by Leaflet, with real zoom/pan, not a static image. Natural Earth: https://www.naturalearthdata.com/about/terms-of-use/ .
- Markers are exactly Registry latitude/longitude, with no visual position offsets. Registry precision/scope limitations remain; these are not verified terminal navigation coordinates.
