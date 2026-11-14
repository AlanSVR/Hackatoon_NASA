"""Aislamiento del runtime geoespacial local.

Rasterio/GDAL puede tomar un PROJ_DATA o PROJ_LIB global de PostgreSQL/PostGIS
en Windows. Se eliminan solo del proceso actual, antes de importar Rasterio;
nunca se modifica el entorno global del sistema.
"""
from __future__ import annotations

import os


def sanitize_proj_environment() -> tuple[str, ...]:
    cleared: list[str] = []
    for key in ('PROJ_DATA', 'PROJ_LIB'):
        if os.environ.get(key):
            os.environ.pop(key, None)
            cleared.append(key)
    return tuple(cleared)
