# Importación para el SQL Editor de Supabase

El SQL Editor rechaza el archivo histórico de 1.2 MB. Ejecuta estos archivos
por separado, en este orden, en una base nueva que ya recibió
`../010_supabase_geoportal_schema.sql`:

1. `011a_administrative_areas.sql`
2. `011b_catalog_and_cache.sql`
3. `011c_job_history.sql`

Los tres son menores de 690 KB y juntos restauran los mismos datos del archivo
histórico `../011_supabase_geoportal_data.sql`. Ese archivo se conserva solo
para restauraciones por conexión directa con `psql`; no se debe pegar completo
en el SQL Editor.
