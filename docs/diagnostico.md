# Diagnóstico inicial — AndesSAR Local

Fecha de revisión: 14 de noviembre de 2026.

## Estado encontrado

El repositorio es un *starter* local ejecutable, no un producto científico terminado. Tiene:

- FastAPI en `backend/main.py`, con `GET /api/health`, `GET /api/scenes` y `POST /api/analyze`.
- React 19, Vite y React-Leaflet en `frontend/`.
- Rasterio, NumPy y Pillow para comparar dos GeoTIFF de potencia lineal.
- Tres GeoTIFF sintéticos catalogados en `data/manifest.json` para Riobamba.
- Pruebas de salud, análisis SAR dinámico y rechazo de la misma escena.

El análisis SAR existente es real respecto de esos archivos: reproyecta ambas escenas a UTM 17S, calcula diferencia de retrodispersión y genera una capa PNG. Sin embargo, las escenas son explícitamente sintéticas; no se deben tratar como NISAR ni como clasificación de cobertura.

## Riesgos y decisiones

| Hallazgo | Decisión tomada |
| --- | --- |
| El módulo SAR solo cubre una zona de Riobamba y usa UTM 17S. | Se conserva aislado como experimental en `/api/analyze`; no se reutiliza para otros países. |
| Rasterio puede heredar rutas PROJ incompatibles de PostgreSQL/PostGIS en Windows. | La API elimina `PROJ_DATA` y `PROJ_LIB` solo en su proceso, antes de importar Rasterio. No modifica Windows ni PostgreSQL. |
| No había un cliente científico remoto ni estadística de tendencia. | Se añadió el adaptador NASA POWER y un módulo estadístico separado. |
| No estaba instalado SciPy. | Se declara como dependencia científica para regresión, valor p e intervalo de confianza. |
| El PDF de requisitos se entregó fuera del repositorio el 14 de noviembre de 2026. | Se revisó y se incorporó en `docs/especificacion.md`; clasificación espacial y animación continúan pendientes de datos reales. |

## Compatibilidad comprobada

La instalación inspeccionada usa Python 3.12.10, FastAPI 0.162.6, Rasterio 1.5.2, NumPy 2.5.4, Node 24.11.1 y npm 11.6.2. El frontend tiene sus dependencias instaladas; el entorno Python requiere instalar la nueva dependencia declarada antes de ejecutar la API actualizada.
