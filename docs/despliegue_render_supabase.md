# Despliegue gratuito en Supabase y Render

La aplicación se despliega en **un solo Web Service nativo de Python de
Render**, plan `free`. No usa Docker, imagen de contenedor ni disco de pago.
Durante la compilación, Render instala las dependencias Python, compila React y
FastAPI entrega tanto la API como la interfaz web.

## Qué se publica

- Código, `render.yaml`, migraciones SQL y las cinco capas IGBP Ecuador
  2021–2025 de `data/seed/geoportal/` (31 MiB).
- En cada inicio, esas cinco capas se copian a la zona privada efímera y hacen
  funcionales Geoportal y Comparar: provincias, métricas, previsualizaciones y
  comparación temporal.
- No se publican `.env`, `runtime/`, videos ni los originales locales grandes:
  `02_2021.0.tif` (493 MiB) y `Zona Norte 2021.tiff` (246 MiB).

## Terminar la importación en el SQL Editor de Supabase

El esquema y PostGIS ya se pueden crear con
[`db/010_supabase_geoportal_schema.sql`](../db/010_supabase_geoportal_schema.sql).
El SQL Editor no acepta el histórico completo de 1.2 MB, por lo que importa
estos tres archivos en este orden:

1. [`011a_administrative_areas.sql`](../db/supabase_sql_editor/011a_administrative_areas.sql)
2. [`011b_catalog_and_cache.sql`](../db/supabase_sql_editor/011b_catalog_and_cache.sql)
3. [`011c_job_history.sql`](../db/supabase_sql_editor/011c_job_history.sql)

Cada uno queda por debajo de 690 KB. Juntos restauran 24 provincias, 7 activos,
17 bandas, 64 entradas de caché, 62 trabajos y 8 sesiones. Comprueba después:

```sql
SELECT
  (SELECT count(*) FROM geoportal.raster_assets) AS assets,
  (SELECT count(*) FROM geoportal.administrative_areas) AS provinces,
  (SELECT count(*) FROM geoportal.raster_bands) AS bands;
```

El archivo histórico `db/011_supabase_geoportal_data.sql` se conserva solo
para restaurar mediante conexión directa con `psql`; no se pega completo en el
SQL Editor.

## Configurar Render sin Docker

1. En Render, crea un **Web Service** desde el repositorio y selecciona la
   rama `main`. Detectará [`render.yaml`](../render.yaml).
2. Verifica estos valores nativos:

   ```text
   Runtime: Python
   Plan: Free
   Build: pip install -r requirements.txt && cd frontend && npm ci && npm run build
   Start: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
   Health check: /api/health
   ```

3. En *Environment*, crea el secreto `GEOPORTAL_DATABASE_URL` usando la URI
   de conexión de Supabase con `sslmode=require`. Usa el formato de
   [`.env.example`](../.env.example), sustituyendo solo los marcadores por los
   valores reales del proyecto. No subas ni pegues la clave en Git.
4. Mantén `GEOPORTAL_STORAGE_DIR=/tmp/geoportal` y
   `GEOPORTAL_ALLOW_LOCAL_UPLOADS=false`, como ya declara `render.yaml`.
5. Despliega. La aplicación abrirá en la URL `onrender.com` del mismo servicio;
   prueba primero `/api/health` y después la página raíz.

## TIFF pesados: solución gratuita aplicada

Render Free pierde los archivos locales en reinicios, pero el proyecto repone
automáticamente las cinco capas pequeñas desde Git. Esto no genera un cargo
adicional y evita subir los originales de 246/493 MiB.

Supabase Storage gratuito permite 1 GB total, pero limita cada archivo a 50
MB; por eso no puede alojar esos dos TIFF. Mientras se use el plan gratuito,
las cargas nuevas se mantienen desactivadas en Render: no se aceptan archivos
que se perderían tras un reinicio. Para cargas permanentes o para publicar los
dos originales grandes habrá que integrar un almacenamiento de objetos con
archivos grandes; no se deben subir a GitHub.

## Credenciales

`.env` está correctamente ignorado. La configuración local actualmente apunta
a PostgreSQL en `localhost`; Render no puede usar esa dirección. La URI real de
Supabase se configura como secreto de Render, no sustituyendo ni versionando la
configuración local.
