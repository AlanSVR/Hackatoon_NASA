# Acceso remoto privado en VS Code

El modo normal sigue siendo local. Para una revisión temporal, reenvía sólo el
puerto de la interfaz o de la API mediante **Ports** de VS Code y marca la
visibilidad como privada. No publiques el puerto `5432`, pgAdmin ni
`runtime/geoportal`.

Antes de abrir un túnel, define `GEOPORTAL_UPLOAD_TOKEN` en el entorno local
del proceso y conserva `GEOPORTAL_ALLOW_LOCAL_UPLOADS` desactivado. El token se
envía únicamente en la cabecera `X-Geoportal-Token`; no pertenece al frontend,
al repositorio ni a los registros.

Los GeoTIFF originales y los resultados de caché permanecen en el
almacenamiento local privado. Cerrar el túnel no los elimina. Para una futura
migración, configure `GEOPORTAL_STORAGE_DIR` con un volumen externo y
`GEOPORTAL_DATABASE_URL` con una instancia Postgres/PostGIS gestionada; la API
no depende de Vercel ni Supabase.
