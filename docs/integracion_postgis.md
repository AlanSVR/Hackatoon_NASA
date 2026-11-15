# Integración geoespacial persistente

## Estado local verificado

`geoportal_db` es una base nueva y separada. PostGIS 3.6.2 está habilitado y
las tablas del esquema `geoportal` ya existen. No se modificaron las bases
preexistentes. El rol efectivo de la aplicación es `geoportal_app`, con inicio
de sesión directo y sin superusuario, creación de bases ni creación de roles.

El archivo local `.env` usa una URL sin contraseña; la credencial del rol queda
únicamente en el almacén local de credenciales de PostgreSQL (`pgpass.conf`) y
nunca en el proyecto ni en el frontend. Para un despliegue se debe proporcionar
`GEOPORTAL_DATABASE_URL` con una cuenta de aplicación dedicada mediante el
gestor secreto de ese entorno.

`postgis_raster` está disponible pero no se instaló: los GeoTIFF originales se
mantienen como archivos privados y Rasterio realiza la lectura por bloques. El
catálogo usa PostGIS para extensión, CRS, índice espacial, relaciones, caché y
estado de trabajos, no para duplicar archivos ráster grandes.

## Persistencia implementada

- `raster_assets`, `raster_bands`, `asset_relations`: catálogo, bandas,
  relaciones y extensión espacial EPSG:4326 con índice GiST.
- `upload_sessions`: cargas reanudables en bloques de 8 MiB, validación de
  tamaño y SHA-256, deduplicación y almacenamiento privado por hash.
- `persistent_cache` y `processing_jobs`: resultados técnicos cacheados y
  recuperables después de reiniciar el backend.
- Previsualización de banda, composición RGB técnica y diferencia normalizada
  calculada sólo con bandas que el operador selecciona explícitamente.

La combinación 2‑6‑5 se puede renderizar como composición técnica, pero el
sistema no la presenta como falso color científico cuando faltan metadatos de
sensor o bandas. De la misma forma, `F mask` conserva su archivo y metadatos,
pero sus clases no se aplican hasta disponer de su especificación verificable.

## Seguridad de carga y acceso remoto

La carga web requiere `GEOPORTAL_UPLOAD_TOKEN`; para pruebas locales se puede
habilitar explícitamente `GEOPORTAL_ALLOW_LOCAL_UPLOADS=true`. No habilites ese
modo al usar un túnel. Consulta [acceso remoto privado](acceso_remoto_privado.md)
para el reenvío de puertos en VS Code.
