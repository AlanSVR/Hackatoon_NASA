# Arquitectura actual

```text
React + Vite + Leaflet
        │ /api (proxy local)
        ▼
FastAPI (127.0.0.1)
 ├─ Earth Trends ── NASA POWER HTTPS ── caché local
 └─ Geoportal ── PostGIS (catálogo y caché) ── almacenamiento privado GeoTIFF
```

Los GeoTIFF originales no se cargan dentro de PostgreSQL. Rasterio los valida y
lee por bloques desde almacenamiento privado; PostGIS conserva su extensión,
CRS, bandas, relaciones, metadatos editables y resultados cacheados. El perfil
MCD12Q1.061 LC_Type1 se habilita solamente cuando se declara explícitamente.

NASA POWER entrega series puntuales mensuales. Las geometrías de Earth Trends
ubican la consulta, pero no se presentan como promedios zonales inexistentes.
Para tendencias cortas, la aplicación muestra una pendiente descriptiva y no
atribuye significancia estadística.
