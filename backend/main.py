"""AndesSAR Earth Trends local API.

The active application exposes point time-series and the persisted GeoTIFF
Geoportal.
"""
from __future__ import annotations

# Execute before a router imports Rasterio, isolating this process from an
# optional PostgreSQL/PostGIS PROJ installation on Windows.
from backend.core.geo_runtime import sanitize_proj_environment

sanitize_proj_environment()

from fastapi import FastAPI

from backend.api.geospatial import router as geospatial_router
from backend.api.tif_lab import router as tif_lab_router
from backend.api.trends import router as trends_router


app = FastAPI(
    title='AndesSAR Earth Trends API',
    version='0.2.0',
    description='Series temporales de punto y Geoportal de cobertura terrestre persistente.',
)
app.include_router(trends_router)
app.include_router(tif_lab_router)
app.include_router(geospatial_router)


@app.get('/api/health')
def health() -> dict[str, bool]:
    return {'ok': True}
