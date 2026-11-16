# Despliegue en Supabase y Render

La aplicación se publica como **un único servicio Docker de Render**: FastAPI
entrega la API y la interfaz React compilada. La base se mantiene en
PostgreSQL/PostGIS de Supabase; los GeoTIFF originales no se guardan dentro de
la base.

## Contenido que se publica

- Código, Dockerfile, `render.yaml` y migraciones SQL.
- `data/seed/geoportal/`: cinco capas IGBP de Ecuador 2021–2025 (31 MiB). El
  backend las restaura de forma privada al iniciar, por lo que Geoportal y
  Comparar funcionan incluso después de que el disco efímero de Render se
  reinicie.
- Nunca se publica `.env`, `runtime/`, videos de trabajo ni los dos TIFF
  locales grandes: `02_2021.0.tif` (493 MiB) y `Zona Norte 2021.tiff` (246
  MiB).

Los cinco archivos semilla son suficientes para las métricas zonales,
selección de provincias, previsualizaciones y comparación 2021–2025 que se
muestran en la aplicación. La base conserva además el catálogo local completo
(7 activos, bandas, 24 provincias, caché y trabajos); los dos activos grandes
quedarán sin bytes en el entorno gratuito hasta moverlos a almacenamiento de
objetos.

## Migrar la base local a Supabase

En el SQL Editor del proyecto Supabase, con el rol administrador del proyecto:

1. Ejecutar [`db/010_supabase_geoportal_schema.sql`](../db/010_supabase_geoportal_schema.sql).
   Crea únicamente el esquema `geoportal` y PostGIS en `extensions`.
2. Ejecutar [`db/011_supabase_geoportal_data.sql`](../db/011_supabase_geoportal_data.sql).
   Importa los datos reales del catálogo local exportados el 15 de noviembre
   de 2026: 24 provincias, 7 activos, 17 bandas, 64 entradas de caché, 62
   trabajos y 8 sesiones de carga. No contiene contraseñas ni bytes ráster.
3. La última consulta del archivo 010 muestra la versión de PostGIS. Tras el
   archivo 011, comprueba en el editor:

   ```sql
   SELECT
     (SELECT count(*) FROM geoportal.raster_assets) AS assets,
     (SELECT count(*) FROM geoportal.administrative_areas) AS provinces;
   ```

El archivo 011 está diseñado para una base `geoportal` nueva. No se debe
ejecutar por segunda vez sobre tablas con datos, porque preserva las claves y
no sobrescribe registros existentes.

## Configuración de Render

1. Crea un **Web Service** desde este repositorio. Render detecta
   [`render.yaml`](../render.yaml) y construye [`Dockerfile`](../Dockerfile).
2. En *Environment*, crea el secreto `GEOPORTAL_DATABASE_URL` con la cadena
   URI de conexión de Supabase. Debe usar TLS, por ejemplo el formato de
   [`.env.example`](../.env.example), sustituyendo el marcador por la
   contraseña real y el `PROJECT_REF`. No se pega esa cadena en Git ni en
   archivos versionados.
3. Conserva los valores definidos en `render.yaml`:
   `GEOPORTAL_STORAGE_DIR=/tmp/geoportal` y
   `GEOPORTAL_ALLOW_LOCAL_UPLOADS=false`.
4. Despliega y visita `https://TU-SERVICIO.onrender.com/api/health`. La página
   principal se abre en la misma URL, sin configurar una URL de API separada.

`/tmp/geoportal` es deliberadamente efímero: al arrancar se restauran los
cinco rásteres publicados y el resto de los resultados se vuelve a calcular o
se recupera del catálogo. Las cargas nuevas están desactivadas en ese perfil
para evitar aceptar archivos que desaparecerían después de un reinicio.

## Rásteres grandes y futuras cargas

El plan gratuito de Supabase Storage admite 1 GB total pero limita cada subida
a 50 MB. Por ello no sirve para los TIFF locales de 246/493 MiB. Para publicar
también esos originales o admitir cargas permanentes se necesita almacenamiento
de objetos con archivos grandes, por ejemplo Cloudflare R2 o un plan de pago
de Supabase/Render. En ese momento hay que configurar sus credenciales como
secretos de Render y cambiar el adaptador de almacenamiento; no se deben copiar
los originales grandes a GitHub.

## Control de secretos

- `.env` está ignorado por Git y no se ha añadido al índice.
- El proyecto incluye solamente `.env.example`, que contiene marcadores sin
  credenciales.
- `GEOPORTAL_DATABASE_URL` se define manualmente como secreto de Render. La
  configuración local actual apunta a PostgreSQL local; no incluye una cadena
  de conexión de Supabase utilizable.
