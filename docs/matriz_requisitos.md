# Matriz de requisitos del MVP

| Requisito | Implementación actual | Estado |
| --- | --- | --- |
| Elegir Ecuador, EE. UU. o Canadá y una localidad | Catálogos explícitos y selectores de país/región | MVP |
| Delimitar una zona con el ratón | Punto, rectángulo y polígono; se conservan en la interfaz y se pueden borrar | MVP visual |
| Consultar temperatura real de NASA | `NasaPowerProvider` consulta NASA POWER desde FastAPI | MVP |
| Precipitación sin confundir unidades | `PRECTOTCORR` e `IMERG_PRECTOT` conservan `mm/día`; el total anual multiplica por días del mes | MVP |
| Validar IMERG por coordenada y período | Fill values `-999` pasan a faltantes y se informan, sin sustitución | MVP |
| Serie temporal y tendencia | `/api/trends`: serie mensual, agregación anual, OLS, p e IC 95 % | MVP |
| Anomalías | `/api/anomalies` respecto de climatología mensual explícita | MVP |
| Comparar dos años | `/api/compare`, marcado como diferencia y no como tendencia | MVP |
| Descargas | JSON y CSV efímeros desde `/api/exports/{id}` | MVP |
| Mapas oscuro, claro, satélite, topográfico y OSM | Fuentes de teselas configuradas sin API key | MVP |
| CRS visible y verificable | Mapa `EPSG:3857`; coordenadas de consulta `EPSG:4326`; CRS de cálculo SAR visible tras el análisis | MVP |
| Inicio de mapa predecible | Centrado estático en la localidad seleccionada; sin pedir ubicación física | MVP |
| Capas de tendencia espacial | No se inventan: requiere datos en cuadrícula y procesamiento por celda | Pendiente |
| Clasificación supervisada, porcentajes y leyenda temática | Requiere insumos, entrenamiento, validación y matriz de confusión | Pendiente |
| Antes/después espacial y animación por año | Requiere catálogo real de GeoTIFF/COG y fechas válidas | Pendiente |
| AppEEARS y NOAA CDO | Adaptadores catalogados como futuros, sin simular conexión | Pendiente |
| Requisitos PDF originales | Revisados e incorporados en `docs/especificacion.md` | Incorporado |
