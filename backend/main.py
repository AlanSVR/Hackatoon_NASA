"""API de AndesSAR: comparación exploratoria de retrodispersión radar.

No clasifica cobertura terrestre ni identifica automáticamente inundaciones.
El MVP procesa escenas GeoTIFF georreferenciadas de potencia lineal positiva.
"""
from __future__ import annotations

# Debe ejecutarse antes de importar Rasterio, para aislar el proceso de
# variables PROJ globales posiblemente heredadas de PostgreSQL/PostGIS.
from backend.core.geo_runtime import sanitize_proj_environment

sanitize_proj_environment()

import base64
import io
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
from pydantic import BaseModel, Field
from rasterio.enums import Resampling
from rasterio.transform import from_bounds
from rasterio.warp import reproject, transform_bounds

from backend.api.trends import router as trends_router
from backend.api.tif_lab import router as tif_lab_router
from backend.api.geospatial import router as geospatial_router

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'data' / 'manifest.json'
SCENES_DIR = ROOT / 'data' / 'scenes'
TARGET_CRS = 'EPSG:32717'  # UTM 17S: área de estudio de Riobamba, Ecuador
CELL_SIZE_M = 30          # resolución de análisis del MVP; NO afirmar resolución NISAR
MAX_CELLS = 1_000_000    # evitar que una solicitud consuma demasiada memoria

app = FastAPI(title='AndesSAR Local API', version='0.1.0',
              description='Comparación dinámica exploratoria SAR por fechas y área.')
app.include_router(trends_router)
app.include_router(tif_lab_router)
app.include_router(geospatial_router)


class AnalysisRequest(BaseModel):
    before_id: str
    after_id: str
    bbox: tuple[float, float, float, float]  # oeste, sur, este, norte; EPSG:4326
    threshold_db: float = Field(default=3.0, ge=0.5, le=12.0)


def read_catalog() -> list[dict]:
    if not MANIFEST.exists():
        return []
    content = json.loads(MANIFEST.read_text(encoding='utf-8'))
    return [
        s for s in content.get('scenes', [])
        if (SCENES_DIR / str(s.get('file', ''))).is_file()
        and Path(str(s.get('file', ''))).name == str(s.get('file', ''))
    ]


def read_linear_power(file_path: Path, width: int, height: int, dst_transform) -> np.ndarray:
    dst = np.full((height, width), np.nan, dtype=np.float32)
    with rasterio.open(file_path) as src:
        if src.count < 1 or src.crs is None:
            raise ValueError('El GeoTIFF debe contener una banda y un CRS válido.')
        reproject(
            source=rasterio.band(src, 1), destination=dst,
            src_transform=src.transform, src_crs=src.crs, src_nodata=src.nodata,
            dst_transform=dst_transform, dst_crs=TARGET_CRS,
            dst_nodata=np.nan, init_dest_nodata=True,
            resampling=Resampling.bilinear,
        )
    return dst


def analyze(payload: AnalysisRequest) -> dict:
    catalog = {s['id']: s for s in read_catalog()}
    a = catalog.get(payload.before_id)
    b = catalog.get(payload.after_id)
    if not a or not b:
        raise HTTPException(404, 'Escena no encontrada. Revisa el catálogo.')
    if a['id'] == b['id']:
        raise HTTPException(422, 'Selecciona dos escenas diferentes.')
    if a.get('source') != b.get('source') or a.get('channel') != b.get('channel'):
        raise HTTPException(422, 'Las escenas deben ser del mismo sensor/producto y canal.')
    if a.get('units') != 'linear_power' or b.get('units') != 'linear_power':
        raise HTTPException(422, 'Este MVP requiere GeoTIFF de potencia lineal, no dB ni RGB.')

    west, south, east, north = payload.bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise HTTPException(422, 'Las coordenadas de la zona no son válidas.')
    # No prometemos análisis global: el CRS local corresponde a Riobamba.
    if not (-79.3 < west < -78.0 and -79.3 < east < -78.0 and
            -2.3 < south < -1.1 and -2.3 < north < -1.1):
        raise HTTPException(422, 'Este prototipo usa UTM 17S y está limitado al entorno de Riobamba.')

    x0, y0, x1, y1 = transform_bounds('EPSG:4326', TARGET_CRS,
                                     west, south, east, north, densify_pts=21)
    width = max(1, math.ceil((x1 - x0) / CELL_SIZE_M))
    height = max(1, math.ceil((y1 - y0) / CELL_SIZE_M))
    if width * height > MAX_CELLS:
        raise HTTPException(422, 'Zona demasiado grande. Selecciona un área menor (máx. 1 millón de píxeles).')

    transform = from_bounds(x0, y0, x1, y1, width, height)
    try:
        before = read_linear_power(SCENES_DIR / a['file'], width, height, transform)
        after = read_linear_power(SCENES_DIR / b['file'], width, height, transform)
    except (rasterio.errors.RasterioError, ValueError) as exc:
        raise HTTPException(422, f'No se pudo leer la escena: {exc}') from exc

    valid = np.isfinite(before) & np.isfinite(after) & (before > 0) & (after > 0)
    valid_count = int(valid.sum())
    if valid_count == 0:
        raise HTTPException(422, 'Las escenas no tienen píxeles válidos coincidentes en esta zona.')

    delta_db = np.full_like(before, np.nan)
    delta_db[valid] = 10.0 * np.log10(after[valid]) - 10.0 * np.log10(before[valid])
    increased = valid & (delta_db >= payload.threshold_db)
    decreased = valid & (delta_db <= -payload.threshold_db)

    # La superficie se calcula en metros del CRS UTM 17S; aproximación por píxel.
    pixel_ha = abs(transform.a * transform.e) / 10_000
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    rgba[increased] = [67, 204, 182, 195]    # aumento: turquesa
    rgba[decreased] = [239, 116, 76, 195]    # disminución: naranja
    buf = io.BytesIO()
    Image.fromarray(rgba, mode='RGBA').save(buf, format='PNG', optimize=True)
    png_b64 = base64.b64encode(buf.getvalue()).decode('ascii')
    overlay_west, overlay_south, overlay_east, overlay_north = transform_bounds(
        TARGET_CRS, 'EPSG:4326', x0, y0, x1, y1, densify_pts=21,
    )

    return {
        'before': {k: a[k] for k in ('id', 'date', 'source', 'channel')},
        'after': {k: b[k] for k in ('id', 'date', 'source', 'channel')},
        'threshold_db': payload.threshold_db,
        'bbox': payload.bbox,
        'overlay_bounds': [overlay_west, overlay_south, overlay_east, overlay_north],
        'overlay_png': f'data:image/png;base64,{png_b64}',
        'statistics': {
            'valid_pixels': valid_count,
            'changed_pixels': int((increased | decreased).sum()),
            'increased_pixels': int(increased.sum()),
            'decreased_pixels': int(decreased.sum()),
            'valid_area_ha': round(valid_count * pixel_ha, 2),
            'changed_area_ha': round(int((increased | decreased).sum()) * pixel_ha, 2),
            'increased_area_ha': round(int(increased.sum()) * pixel_ha, 2),
            'decreased_area_ha': round(int(decreased.sum()) * pixel_ha, 2),
            'changed_percent': round(100 * int((increased | decreased).sum()) / valid_count, 2),
        },
        'method': {
            'quantity': 'Diferencia de retrodispersión en dB (fecha final menos inicial)',
            'resolution_m': CELL_SIZE_M,
            'crs_analysis': TARGET_CRS,
            'resampling': 'bilinear de potencia lineal',
            'scope': 'Exploratorio: cambio de señal radar, no cambio de cobertura confirmado',
            'quality': 'Sin máscara externa de layover/sombra ni evaluación de incertidumbre; validar antes de conclusiones',
        },
        'is_demo': bool(a.get('is_demo') or b.get('is_demo')),
    }


@app.get('/api/health')
def health():
    return {'ok': True, 'scenes': len(read_catalog())}


@app.get('/api/scenes')
def scenes():
    return sorted(read_catalog(), key=lambda s: s['date'])


@app.post('/api/analyze')
def analyze_endpoint(payload: AnalysisRequest):
    return JSONResponse(analyze(payload))
