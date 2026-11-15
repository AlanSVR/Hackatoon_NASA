# AndesSAR Earth Trends — MVP local para Windows

Aplicación local para explorar tendencias ambientales puntuales con datos reales de NASA POWER. Está orientada al reto **“Be An Earth System Trend Detective!”** de NASA Space Apps Challenge 2026.


## Qué funciona

- Selector de Ecuador, Estados Unidos y Canadá; con Riobamba/Quito, Denver/Phoenix y Calgary/Vancouver.
- Serie mensual de punto mediante NASA POWER, consultada desde FastAPI, con caché temporal local, timeout y mensajes de error claros.
- Temperatura media a 2 m (`T2M`) y precipitación corregida (`PRECTOTCORR`). `IMERG_PRECTOT` se consulta solo bajo disponibilidad real: los valores faltantes del proveedor se muestran como faltantes, sin sustitución.
- Tendencia OLS sobre agregados anuales, pendiente, valor p, intervalo de confianza 95 %, anomalías mensuales y comparador anual.
- Exportación JSON/CSV de resultados calculados, metadatos de fuente, unidades, calidad y limitaciones.
- Leaflet con mapas base, punto, rectángulo y polígono. NASA POWER permanece identificado como análisis de punto; no se dibuja una superficie de tendencia ficticia ni se usa el centroide de un polígono como si fuese su promedio.
- Comparador SAR local existente en `/api/analyze`, limitado a la demo de Riobamba.

## Inicio rápido en Windows

Requisitos: Python 3.12 y Node.js reciente (Vite 7 requiere Node 20.19+ o 22.12+).
