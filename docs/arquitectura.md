# Arquitectura propuesta

```text
React + Vite + Leaflet
        │ /api (proxy local)
        ▼
FastAPI (127.0.0.1)
 ├─ API Earth Trends ── servicios ── DataProvider ── NASA POWER HTTPS
 │                         │
 │                         ├─ caché TTL en memoria
 │                         ├─ estadísticas (anomalías, anualización, OLS)
 │                         └─ exportaciones efímeras JSON/CSV
 └─ API SAR experimental ── Rasterio ── GeoTIFF locales sintéticos/reales
```

## Límites científicos del diseño

NASA POWER mensual se consulta como punto. Una geometría dibujada sirve para conservar la intención geográfica y ubicar un punto de consulta; no produce un promedio de polígono. Las capas espaciales y clasificación permanecen fuera del flujo hasta contar con una fuente raster/retícula apta.

Para temperatura, el análisis ajusta una regresión OLS sobre medias anuales con al menos nueve meses válidos. Para las variables de precipitación en `mm/día`, convierte cada valor a acumulado mensual con los días reales y solo acepta años completos para la suma anual. El p e IC 95 % se presentan junto con límites de estacionalidad/autocorrelación y sin inferencia causal.

## Contrato de proveedores

`DataProvider.fetch_monthly(parameter, latitude, longitude, start_year, end_year)` entrega observaciones ordenadas, metadatos originales y faltantes explícitos. `NasaPowerProvider` es la única implementación funcional. AppEEARS, NOAA CDO y raster local están identificados para evitar dependencias ficticias.
