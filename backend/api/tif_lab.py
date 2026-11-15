"""Laboratorio local y explícito para inspeccionar los GeoTIFF MCD12Q1.

No expone rutas arbitrarias ni interpreta los códigos como clases con nombre. Sirve
solamente los archivos concretos entregados en las dos carpetas del proyecto y
permite comparar códigos de un mismo producto y grilla.
"""
from __future__ import annotations

import hashlib
import io
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
import rasterio
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from PIL import Image
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
TIF_DIRECTORIES = ('Ecu Cp', 'Ecu Cp 2021_2023', 'Ecu Cp 2023_2026', '02_2021')
FILENAME_PATTERN = re.compile(
    r'^MCD12Q1\.061_(?P<layer>.+?)_doy(?P<year>\d{4})001\d+_aid\d+(?: \(\d+\))?\.tif$',
    re.IGNORECASE,
)
PREPARED_FILENAME_PATTERN = re.compile(r'^Ecu Cp (?P<year>\d{4})\.tif$', re.IGNORECASE)
MAX_PREVIEW_EDGE = 1200

router = APIRouter(prefix='/api/tif-lab', tags=['Laboratorio GeoTIFF local'])


class TifLabCompareRequest(BaseModel):
    before_id: str = Field(min_length=8, max_length=64)
    after_id: str = Field(min_length=8, max_length=64)


def _asset_id(relative_path: str) -> str:
    return hashlib.sha256(relative_path.encode('utf-8')).hexdigest()[:16]


def _number(value):
    return value.item() if isinstance(value, np.generic) else value


def _parse_filename(path: Path) -> tuple[str, int, str] | None:
    match = FILENAME_PATTERN.match(path.name)
    if match:
        layer = match.group('layer')
        return layer, int(match.group('year')), 'quality_flag' if layer.upper() == 'QC' else 'categorical_codes'
    prepared_match = PREPARED_FILENAME_PATTERN.match(path.name)
    if prepared_match and path.parent.name == 'Ecu Cp':
        return 'Ecu Cp preparado', int(prepared_match.group('year')), 'prepared_categorical_codes'
    if path.parent.name == '02_2021' and path.suffix.lower() in {'.tif', '.tiff'}:
        # El nombre no prueba producto, sensor, máscara ni orden espectral.
        return path.stem, 2021, 'unverified_raster'
    return None


@lru_cache(maxsize=1)
def _records() -> list[dict]:
    records: list[dict] = []
    for directory_name in TIF_DIRECTORIES:
        directory = ROOT / directory_name
        if not directory.is_dir():
            continue
        paths = sorted([*directory.glob('*.tif'), *directory.glob('*.tiff')])
        for path in paths:
            parsed = _parse_filename(path)
            if not parsed:
                continue
            layer, year, kind = parsed
            relative_path = path.relative_to(ROOT).as_posix()
            with rasterio.open(path) as dataset:
                west, south, east, north = dataset.bounds
                crs = dataset.crs.to_string() if dataset.crs else None
                record = {
                    'id': _asset_id(relative_path),
                    'file_name': path.name,
                    'collection': directory_name,
                    'relative_path': relative_path,
                    'layer': layer,
                    'year': year,
                    'kind': kind,
                    'shape': [dataset.height, dataset.width],
                    'band_count': dataset.count,
                    'dtype': dataset.dtypes[0] if dataset.dtypes else None,
                    'crs': crs,
                    'epsg': dataset.crs.to_epsg() if dataset.crs else None,
                    'bounds': [west, south, east, north],
                    'resolution_degrees': [abs(dataset.transform.a), abs(dataset.transform.e)],
                    'nodata': dataset.nodata,
                    'units': dataset.tags().get('units', 'no declarado'),
                    'size_bytes': path.stat().st_size,
                    'band_descriptions': list(dataset.descriptions),
                    'band_scales': [float(value) if value is not None else None for value in dataset.scales],
                    'band_offsets': [float(value) if value is not None else None for value in dataset.offsets],
                }
            record['preview_url'] = f"/api/tif-lab/preview/{record['id']}"
            records.append(record)
    return sorted(records, key=lambda item: (item['layer'], item['year'], item['collection'], item['file_name']))


def _resolve(asset_id: str) -> tuple[dict, Path]:
    for record in _records():
        if record['id'] == asset_id:
            path = ROOT / Path(record['relative_path'])
            if path.is_file():
                return record, path
    raise HTTPException(404, 'Archivo GeoTIFF no encontrado en el catálogo local.')


def _valid_mask(data: np.ndarray, nodata) -> np.ndarray:
    valid = np.isfinite(data)
    if nodata is not None:
        valid &= data != nodata
    return valid


def _inspect(record: dict, path: Path) -> dict:
    with rasterio.open(path) as dataset:
        source_pixel_count = dataset.width * dataset.height
        if record['kind'] == 'unverified_raster':
            ratio = min(1.0, MAX_PREVIEW_EDGE / max(dataset.width, dataset.height))
            data = dataset.read(1, out_shape=(max(1, round(dataset.height * ratio)), max(1, round(dataset.width * ratio))))
        else:
            data = dataset.read(1)
        valid = _valid_mask(data, dataset.nodata)
        values = data[valid]
        histogram = []
        if record['kind'] != 'unverified_raster':
            codes, counts = np.unique(values, return_counts=True) if values.size else (np.array([]), np.array([]))
            ordered = sorted(zip(codes, counts), key=lambda pair: int(pair[1]), reverse=True)
            histogram = [
                {
                    'code': _number(code),
                    'pixels': int(count),
                    'percent_valid': round(100 * int(count) / int(values.size), 4),
                }
                for code, count in ordered
            ]
        tags = dataset.tags()
    response = {
        **record,
        'valid_pixels': int(values.size),
        'nodata_pixels': int(data.size - values.size),
        'minimum_code': _number(values.min()) if values.size else None,
        'maximum_code': _number(values.max()) if values.size else None,
        'histogram': histogram,
        'metadata_tags': {key: tags[key] for key in sorted(tags)},
        'interpretation': 'Los colores del visor representan códigos almacenados. Este laboratorio no asigna nombres de coberturas ni valida una clasificación.',
    }
    if record['kind'] == 'unverified_raster':
        response['sampled_for_summary'] = data.size != source_pixel_count
        response['value_summary'] = {
            'minimum': _number(values.min()) if values.size else None,
            'maximum': _number(values.max()) if values.size else None,
            'mean': round(float(values.mean()), 8) if values.size else None,
            'standard_deviation': round(float(values.std()), 8) if values.size else None,
        }
        response['interpretation'] = (
            'NO VERIFICADO: el archivo no declara sensor, producto ni semántica de bandas. '
            'El laboratorio resume la banda 1 y no la presenta como RGB, índice o máscara válida.'
        )
    return response


def _code_palette() -> np.ndarray:
    """Paleta estable de inspección, deliberadamente sin significado temático."""
    palette = np.zeros((256, 4), dtype=np.uint8)
    palette[:, 3] = 255
    palette[0] = [79, 91, 105, 255]
    for code in range(1, 256):
        palette[code] = [
            55 + (code * 73) % 180,
            70 + (code * 131) % 155,
            65 + (code * 197) % 170,
            255,
        ]
    return palette


def _resize_preview(image: Image.Image) -> Image.Image:
    if max(image.size) <= MAX_PREVIEW_EDGE:
        return image
    ratio = MAX_PREVIEW_EDGE / max(image.size)
    target = (max(1, round(image.width * ratio)), max(1, round(image.height * ratio)))
    return image.resize(target, Image.Resampling.NEAREST)


def _png_response(rgba: np.ndarray) -> Response:
    image = _resize_preview(Image.fromarray(rgba, mode='RGBA'))
    buffer = io.BytesIO()
    image.save(buffer, format='PNG', optimize=True)
    return Response(
        buffer.getvalue(), media_type='image/png',
        headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'},
    )


def _continuous_preview(data: np.ndarray, valid: np.ndarray) -> np.ndarray:
    rgba = np.zeros((*data.shape, 4), dtype=np.uint8)
    values = np.asarray(data[valid], dtype=np.float64)
    if not values.size:
        return rgba
    low, high = np.percentile(values, [2, 98])
    if high <= low:
        high = low + 1
    normalized = np.clip((data.astype(np.float64) - low) / (high - low), 0, 1)
    shade = (normalized * 255).astype(np.uint8)
    rgba[valid] = np.column_stack((shade[valid], shade[valid], shade[valid], np.full(int(valid.sum()), 255, dtype=np.uint8)))
    return rgba


def _preview_rgba(record: dict, path: Path) -> np.ndarray:
    with rasterio.open(path) as dataset:
        if record['kind'] == 'unverified_raster':
            ratio = min(1.0, MAX_PREVIEW_EDGE / max(dataset.width, dataset.height))
            data = dataset.read(1, out_shape=(max(1, round(dataset.height * ratio)), max(1, round(dataset.width * ratio))))
        else:
            data = dataset.read(1)
        valid = _valid_mask(data, dataset.nodata)
    if record['kind'] == 'unverified_raster':
        return _continuous_preview(data, valid)
    rgba = np.zeros((*data.shape, 4), dtype=np.uint8)
    palette = _code_palette()
    index = np.mod(data.astype(np.int64), 256).astype(np.uint8)
    rgba[valid] = palette[index[valid]]
    return rgba


def _ensure_comparable(before: dict, after: dict, before_path: Path, after_path: Path) -> None:
    if before['id'] == after['id']:
        raise HTTPException(422, 'Selecciona dos archivos diferentes.')
    if before['layer'] != after['layer']:
        raise HTTPException(422, 'Solo se pueden comparar archivos del mismo producto/capa (por ejemplo, LC_Type5 con LC_Type5).')
    with rasterio.open(before_path) as first, rasterio.open(after_path) as second:
        same_grid = (
            first.count == second.count
            and first.width == second.width
            and first.height == second.height
            and first.crs == second.crs
            and first.transform.almost_equals(second.transform)
        )
    if not same_grid:
        raise HTTPException(422, 'Los archivos no comparten grilla, CRS o transformación; no se compararon.')


def _comparison(before: dict, after: dict, before_path: Path, after_path: Path) -> dict:
    _ensure_comparable(before, after, before_path, after_path)
    with rasterio.open(before_path) as first, rasterio.open(after_path) as second:
        first_data = first.read(1)
        second_data = second.read(1)
        valid = _valid_mask(first_data, first.nodata) & _valid_mask(second_data, second.nodata)
    changed = valid & (first_data != second_data)
    valid_count = int(valid.sum())
    changed_count = int(changed.sum())
    transitions: list[dict] = []
    if changed_count:
        pairs = np.stack((first_data[changed], second_data[changed]), axis=1)
        values, counts = np.unique(pairs, axis=0, return_counts=True)
        transitions = [
            {
                'from_code': _number(pair[0]),
                'to_code': _number(pair[1]),
                'pixels': int(count),
                'percent_valid': round(100 * int(count) / valid_count, 4),
            }
            for pair, count in sorted(zip(values, counts), key=lambda item: int(item[1]), reverse=True)[:12]
        ]
    return {
        'before': {key: before[key] for key in ('id', 'file_name', 'layer', 'year', 'collection')},
        'after': {key: after[key] for key in ('id', 'file_name', 'layer', 'year', 'collection')},
        'statistics': {
            'valid_pixels': valid_count,
            'unchanged_pixels': int(valid_count - changed_count),
            'changed_code_pixels': changed_count,
            'changed_code_percent': round(100 * changed_count / valid_count, 4) if valid_count else None,
            'excluded_nodata_pixels': int(valid.size - valid_count),
        },
        'top_transitions': transitions,
        'method': {
            'quantity': 'Diferencia de código de píxel entre dos archivos compatibles',
            'resampling': 'ninguno; comparación directa de la grilla original',
            'scope': 'Un código distinto no prueba por sí mismo un cambio de cobertura real.',
            'crs': before['crs'],
        },
        'comparison_preview_url': f"/api/tif-lab/comparison-preview?before_id={before['id']}&after_id={after['id']}",
    }


@router.get('/catalog')
def catalog():
    warnings = []
    vrt_directory = ROOT / '02_2021'
    if vrt_directory.is_dir() and list(vrt_directory.glob('*.vrt')):
        warnings.append('Los VRT de 02_2021 no se abren en este laboratorio: sus dependencias deben validarse y quedar bajo rutas controladas antes de procesarlos.')
    return {
        'items': _records(),
        'note': 'Catálogo limitado a GeoTIFF locales de carpetas aprobadas. No acepta rutas ingresadas por el usuario.',
        'warnings': warnings,
    }


@router.get('/inspect/{asset_id}')
def inspect(asset_id: str):
    record, path = _resolve(asset_id)
    return _inspect(record, path)


@router.get('/preview/{asset_id}')
def preview(asset_id: str):
    record, path = _resolve(asset_id)
    return _png_response(_preview_rgba(record, path))


@router.post('/compare')
def compare(payload: TifLabCompareRequest):
    before, before_path = _resolve(payload.before_id)
    after, after_path = _resolve(payload.after_id)
    return _comparison(before, after, before_path, after_path)


@router.get('/comparison-preview')
def comparison_preview(before_id: str, after_id: str):
    before, before_path = _resolve(before_id)
    after, after_path = _resolve(after_id)
    _ensure_comparable(before, after, before_path, after_path)
    with rasterio.open(before_path) as first, rasterio.open(after_path) as second:
        first_data = first.read(1)
        second_data = second.read(1)
        valid = _valid_mask(first_data, first.nodata) & _valid_mask(second_data, second.nodata)
    changed = valid & (first_data != second_data)
    rgba = np.zeros((*first_data.shape, 4), dtype=np.uint8)
    rgba[valid & ~changed] = [120, 137, 154, 55]
    rgba[changed] = [249, 201, 120, 240]
    return _png_response(rgba)
