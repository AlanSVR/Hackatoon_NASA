# AndesSAR Earth Trends — MVP local para Windows

Aplicación local para explorar tendencias ambientales puntuales con datos reales de NASA POWER. Está orientada al reto **“Be An Earth System Trend Detective!”** de NASA Space Apps Challenge 2026, sin afirmar afiliación ni aval de NASA.

El módulo **SAR experimental** original se conserva en una pestaña independiente. Sus tres GeoTIFF incluidos son sintéticos; no son observaciones NISAR ni clasifican cobertura.

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

1. Ejecuta `instalar_windows.bat` una sola vez.
2. En una ventana, ejecuta `iniciar_backend.bat`.
3. En otra, ejecuta `iniciar_frontend.bat`.
4. Abre [http://127.0.0.1:5173](http://127.0.0.1:5173).

El backend queda en [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs). Vite reenvía `/api` a ese puerto.

### Alternativa por consola

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
cd frontend
npm install
```

En la raíz:

```bat
.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8080
```

En `frontend`:

```bat
npm run dev
```

## Pruebas

```bat
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run build
```

## Rutas principales

- `GET /api/health`, `GET /api/countries`, `GET /api/regions`, `GET /api/variables`, `GET /api/providers`, `GET /api/data-availability`
- `POST /api/timeseries`, `POST /api/trends`, `POST /api/anomalies`, `POST /api/compare`
- `GET /api/exports/{id}?format=json|csv`
- `GET /api/scenes`, `POST /api/analyze` (SAR experimental heredado)

## Integridad científica y límites

- NASA POWER mensual entrega una serie puntual; no equivale a un promedio de país, ciudad, rectángulo o polígono.
- Para `T2M`, se ajusta OLS sobre medias anuales con al menos nueve meses válidos. Para precipitación mensual expresada en `mm/día`, cada valor se convierte usando los días reales del mes y se suman solamente años completos.
- El valor p e IC 95 % dependen de supuestos OLS. La agregación anual reduce, pero no elimina, estacionalidad y autocorrelación. Una diferencia interanual no es una tendencia significativa y una tendencia no prueba causalidad.
- La disponibilidad efectiva de variables, períodos y coordenadas se toma de la respuesta real del proveedor; no se inventan fechas ni mediciones.
- La limpieza de `PROJ_DATA`/`PROJ_LIB` se hace solo dentro del proceso FastAPI antes de importar Rasterio. No se modifica Windows ni PostgreSQL/PostGIS.

## Documentación de proyecto

- [Diagnóstico](docs/diagnostico.md)
- [Matriz de requisitos](docs/matriz_requisitos.md)
- [Arquitectura](docs/arquitectura.md)
- [Plan de implementación](docs/plan_implementacion.md)
- [Especificación](docs/especificacion.md)

`docs/Requsitos.pdf` no estaba incluido en este paquete. La especificación lo documenta como insumo pendiente y debe actualizarse cuando se agregue.
