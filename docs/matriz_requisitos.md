# Matriz de requisitos del MVP

| Requisito | Implementación actual | Estado |
| --- | --- | --- |
| Elegir Ecuador, EE. UU. o Canadá y una localidad | Catálogos explícitos y selectores de país/región | MVP |
| Consultar temperatura real de NASA | `NasaPowerProvider` consulta NASA POWER desde FastAPI | MVP |
| Precipitación sin confundir unidades | `PRECTOTCORR` e `IMERG_PRECTOT` conservan `mm/día`; el total anual multiplica por días del mes | MVP |
| Validar IMERG por coordenada y período | Fill values `-999` pasan a faltantes y se informan, sin sustitución | MVP |
| Serie temporal y tendencia | `/api/trends`: serie mensual, agregación anual, OLS, p e IC 95 % | MVP |
| Anomalías | `/api/anomalies` respecto de climatología mensual explícita | MVP |
| Comparar dos años | `/api/compare`, marcado como diferencia y no como tendencia | MVP |
| Descargas | JSON y CSV efímeros desde `/api/exports/{id}` | MVP |
| Punto, rectángulo y polígono en el mapa | La UI conserva selección; NASA POWER se etiqueta siempre como serie puntual | MVP visual |
| Capas de tendencia espacial | No se inventan: requiere datos en cuadrícula y procesamiento por celda | Pendiente |
| Clasificación de cobertura | Arquitectura/fase futura; no se generan clases ni porcentajes | Pendiente |
| AppEEARS y NOAA CDO | Adaptadores catalogados como futuros, sin simular conexión | Pendiente |
| Persistir AOI entre módulos | Estado de selección compartido en la interfaz | MVP |
| PDF de requisitos original | No se recibió en el repositorio | Bloqueado por insumo |
