# Matriz de requisitos vigente

| Requisito | Implementación |
| --- | --- |
| Ecuador y años 2021–2026 | Filtros validados en interfaz y API |
| Consulta de tendencia | NASA POWER por punto seleccionado |
| CRS visible | Vista `EPSG:3857`; consultas y rásteres declarados con su CRS |
| GeoTIFF persistente | Carga por bloques, SHA-256 y catálogo PostGIS |
| Cobertura del suelo | Perfil declarado MCD12Q1.061 LC_Type1 (IGBP) |
| Mapa y leyenda temática | Previsualización categórica, inspección de píxel y área rectangular |
| Comparación temporal | Sólo activos compatibles y con fechas realmente disponibles |
| ES / EN | Cambio inmediato, persistente y con formatos locales |
| Carga remota | Requiere token; la excepción sin token es exclusivamente local |

No se presentan límites provinciales, índices, máscaras ni análisis de áreas
que no tengan una fuente geoespacial validada.
