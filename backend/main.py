"""AndesSAR Earth Trends local API.

The active application exposes point time-series and the persisted GeoTIFF
Geoportal.
"""
from __future__ import annotations

# Execute before a router imports Rasterio, isolating this process from an
# optional PostgreSQL/PostGIS PROJ installation on Windows.
from backend.core.geo_runtime import sanitize_proj_environment

sanitize_proj_environment()

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from backend.api.geospatial import router as geospatial_router
from backend.api.tif_lab import router as tif_lab_router
from backend.api.trends import router as trends_router
from backend.geospatial.seed import restore_seed_assets
from backend.geospatial.settings import GeoportalSettings


app = FastAPI(
    title='AndesSAR Earth Trends API',
    version='0.2.0',
    description='Series temporales de punto y Geoportal de cobertura terrestre persistente.',
)
app.include_router(trends_router)
app.include_router(tif_lab_router)
app.include_router(geospatial_router)


@app.on_event('startup')
def restore_deployment_seed_data() -> None:
    """Recreate the reviewed public layers after an ephemeral deploy restart."""
    restore_seed_assets(GeoportalSettings.from_environment())


@app.get('/api/health')
def health() -> dict[str, bool]:
    return {'ok': True}


_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_FRONTEND_DIST = _PROJECT_ROOT / 'frontend' / 'dist'


@app.get('/{path:path}', include_in_schema=False)
def frontend_application(path: str) -> FileResponse:
    """Serve the compiled React application in a single Render web service."""
    index = _FRONTEND_DIST / 'index.html'
    if not index.is_file():
        raise HTTPException(404, 'La interfaz web compilada no está disponible.')
    if path:
        candidate = (_FRONTEND_DIST / path).resolve()
        try:
            candidate.relative_to(_FRONTEND_DIST.resolve())
        except ValueError:
            candidate = index
        if candidate.is_file():
            return FileResponse(candidate)
    return FileResponse(index)
