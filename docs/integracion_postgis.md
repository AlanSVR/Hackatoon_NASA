# Integración geoespacial persistente

El geoportal añade un catálogo PostGIS separado de los experimentos y bases existentes. Conserva el laboratorio como instrumento de inspección y no afirma que las capas analizadas sean clasificaciones válidas.

## Estado verificado en esta máquina

- PostgreSQL 17 responde en `127.0.0.1:5432`.
- La conexión administrativa requiere contraseña. Por seguridad no se intentó adivinarla, buscarla ni escribirla en comandos.
- Por tanto, `geoportal_db`, el rol `geoportal_app` y PostGIS están **NO VERIFICADOS** hasta ejecutar el aprovisionamiento local con una cuenta administradora.
- La aplicación expone `GET /api/geospatial/status`. Antes de configurar la base responde explícitamente que falta `GEOPORTAL_DATABASE_URL`; no simula persistencia.

## Aprovisionamiento seguro

El script solo crea `geoportal_db` y `geoportal_app`; se detiene si ya existe alguno. No lista, altera ni elimina `bodega_db`, `postgis_35_sample` ni `postgis_36_sample2`.

1. Abre PowerShell local en la raíz del proyecto.
2. Ejecuta `& .\db\setup_geoportal.ps1`.
3. Escribe las contraseñas únicamente en los avisos seguros de PowerShell. No las pegues en la consola, la URL del navegador, Git ni el chat.
4. Copia `.env.example` a `.env` y completa la cadena de conexión en el editor local. El backend carga `.env`, pero `.gitignore` lo excluye.
5. Elige `GEOPORTAL_STORAGE_DIR` fuera de `frontend/`, `data/` público y el repositorio si se va a publicar la aplicación.
6. Reinicia el backend y ejecuta `& .\db\verify_geoportal.ps1` para comprobar la extensión y las tablas sin modificar nada.

`setup_geoportal.ps1` usa las contraseñas en memoria y las pasa a `psql` mediante entrada estándar cuando crea el rol. No las guarda en el script ni las expone en su línea de comandos.

## Qué persiste

La migración [001_geoportal_catalog.sql](../db/001_geoportal_catalog.sql) crea:

- `raster_assets`: nombre original, ruta interna, SHA-256, tamaño, CRS/EPSG, grilla, nodata, resolución, extensión en EPSG:4326 con índice GiST, metadatos declarados y técnicos.
- `raster_bands` y `asset_relations`: bandas y relaciones de origen, máscara, auxiliar, derivado o dependencia VRT.
- `upload_sessions`: carga reanudable por bloques y estado de validación.
- `processing_jobs` y `persistent_cache`: contratos persistentes para ejecuciones y cachés reproducibles. No se declaran trabajos terminados hasta que exista un procesador real.

Los píxeles originales se guardan como archivos privados direccionados por hash. PostGIS conserva catálogo, geometrías, relaciones y resultados; no se duplican rásteres grandes dentro de una columna raster. Esta separación permite validar, deduplicar y servir una vista previa cacheada sin procesar el GeoTIFF completo en cada apertura.

## Flujo de carga actual

1. El navegador crea una sesión con tamaño, nombre y metadatos declarados.
2. Sube bloques de 8 MiB (configurable) y puede repetir un bloque ya confirmado usando su SHA-256.
3. Al completar, el backend concatena los bloques sin cargar el archivo entero en memoria, calcula SHA-256, rechaza duplicados y abre el fichero con Rasterio.
4. Para GeoTIFF exige un controlador GTiff, al menos una banda y CRS; extrae extensión transformada a EPSG:4326, dimensiones, resolución, nodata, bandas, escalas, offsets y etiquetas.
5. Solo después mueve el archivo al almacén privado y registra una fila `ready` en una transacción de catálogo. Una vista de banda 1 se cachea como PNG técnico; no se publica el TIFF original.

El límite predeterminado es 500 MiB. La sesión y cada bloque validan su tamaño; los archivos incompletos no se registran como activos. La carga requiere `GEOPORTAL_UPLOAD_TOKEN`, o el modo de prueba explícito `GEOPORTAL_ALLOW_LOCAL_UPLOADS=true` desde `localhost`. Este MVP no implementa cuentas, cuotas por usuario ni autorización multiusuario: no debe exponerse a Internet hasta incorporar ese control en un proveedor de identidad o proxy de autenticación.

## VRT y auxiliares

Se admiten de forma deliberadamente restringida por API, no por la interfaz inicial:

- Un VRT solo pasa si declara un `asset_group_id` y cada fuente es un nombre simple de archivo ya catalogado dentro de ese mismo grupo. Rutas absolutas, `..`, DTD/entidades XML y dependencias externas se rechazan.
- Un `.aux.xml` debe estar bien formado, no incluir DTD/entidades y referir `source_asset_id` ya catalogado.

No se abre un VRT que apunte fuera del almacenamiento controlado. Esto evita que una carga XML solicite archivos arbitrarios del servidor.

## Hallazgo de `02_2021`

Se inspeccionaron seis TIFF: tres rásteres de seis bandas y tres archivos monobanda. Todos declaran EPSG:4326, una grilla de 3300 × 6525 y nodata `-9999` para los multibanda o `255` para los monobanda. Dos variantes enteras declaran escala `0.0001`; otras ya son `float32`.

Los archivos no incluyen descripciones de bandas ni metadatos suficientes de sensor/producto. Por eso:

- **NO VERIFICADO:** el orden de bandas, RGB, índices espectrales, unidades físicas y semántica de `F mask`.
- Los VRT de esta carpeta no se procesan en el laboratorio: contienen fuentes externas y no satisfacen la política de almacenamiento controlado.
- El laboratorio ahora lista los TIFF de `02_2021`, resume técnicamente la banda 1 y usa escala de grises. No crea una composición RGB ni llama “máscara” a una capa por su nombre.

## CRS y visualización

El catálogo guarda el CRS original y una extensión transformada a EPSG:4326. Leaflet puede mostrar mapas base en Web Mercator; eso no cambia el CRS fuente ni convierte una resolución angular en metros. Antes de combinar fechas, un trabajo futuro deberá verificar CRS, transformación de grilla, nodata y extensión; ese trabajo no está marcado como disponible en la interfaz actual.

## Túnel de desarrollo

La API permanece ligada a `127.0.0.1`. Si se usa un túnel para una demostración, publica solo el frontend o un proxy autenticado que reenvíe al backend local; nunca expongas PostgreSQL en el túnel. Define el token de carga y no habilites `GEOPORTAL_ALLOW_LOCAL_UPLOADS` en ese escenario.
