# Diagnóstico de la integración local

La aplicación utiliza FastAPI, React/Vite, Leaflet, Rasterio y PostgreSQL con
PostGIS. `geoportal_db` es una base separada; la cuenta de aplicación tiene
privilegios mínimos y las credenciales se mantienen fuera del proyecto.

El catálogo geoespacial valida GeoTIFF, registra CRS, extensión, resolución,
nodata, bandas y hash SHA-256. Los resultados y previsualizaciones se recuperan
desde caché persistente después de reiniciar la API. La carga local sólo está
activa para `127.0.0.1`; un acceso remoto debe usar un token de carga.

Los mapas de cobertura importados de la colección local se identifican como
MCD12Q1.061 LC_Type1 (IGBP), no como una clasificación inferida por la
aplicación. No se declara una fecha local si no existe su GeoTIFF validado.
