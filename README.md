# AndesSAR — Geoportal local para Ecuador

Aplicación local para explorar mapas de cobertura terrestre de Ecuador,
catalogados en PostgreSQL/PostGIS. La interfaz abre directamente el Geoportal;
la navegación incluye **Geoportal** y **Comparar**.

## Funciones disponibles

- Catálogo persistente de GeoTIFF con archivos originales privados.
- Visualización de clasificaciones IGBP, metadatos y sistema de referencia de
  coordenadas (SRC/CRS).
- Selección de una provincia o de varias provincias mediante los límites
  administrativos persistidos de Ecuador.
- Métricas zonales de píxeles válidos, área estimada, agua clasificada y
  distribución de clases.
- Mapa base OpenStreetMap predeterminado, con alternativas satélite,
  topográfica, clara y oscura.
- Comparación de dos mapas, transición reproducible y resumen de cambios.
- Concordancia de los dos mapas mediante acuerdo observado, Kappa y margen de
  acuerdo; se calcula para cada comparación válida.
- Español/Inglés con preferencia guardada; inglés es el idioma inicial en una
  instalación nueva.

## Inicio local en Windows

Requisitos: Python 3.12, PostgreSQL con PostGIS y Node.js reciente (Vite 7
requiere Node 20.19+ o 22.12+).

1. Configura las credenciales locales solamente en `.env`.
2. Ejecuta `iniciar_backend.bat`.
3. Ejecuta `iniciar_frontend.bat`.
4. Abre `http://127.0.0.1:5173/`.

Los GeoTIFF locales y las credenciales no deben añadirse al repositorio. La
preparación para Render y Supabase está en
[`docs/despliegue_render_supabase.md`](docs/despliegue_render_supabase.md).
