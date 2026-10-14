---
icon: material/globe-model
---

Enriche TenXObjects by geo-referencing [ipAddress](https://doc.log10x.com/api/js/#TenXObject+ipAddress) values via [GeoIP DB](https://doc.log10x.com/api/js/#TenXLookup.loadGeoIPDB) lookup.

Database files [reload](https://doc.log10x.com/run/reload/) on disk changes and can [sync](https://doc.log10x.com/config/github/) from GitHub. On Kubernetes, deliver them via [ConfigMap](https://doc.log10x.com/config/k8s/) (the `@kubernetes` macro writes via temp + atomic rename, which reloads; plain volume-mounted ConfigMaps do not).

Resolves IP addresses to: Continent, Country, Subdivision, City, Postal, Latitude, Longitude. 