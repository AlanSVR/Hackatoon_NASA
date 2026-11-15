"""Explicit MCD12Q1.061 LC_Type1 (IGBP) support.

The functions in this module are deliberately enabled only when the catalog
record declares the exact analysis profile.  A number in an arbitrary TIFF is
never promoted to a land-cover class merely because it resembles this range.
"""
from __future__ import annotations

import io
import math
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from PIL import Image
from rasterio.features import bounds as geometry_bounds, geometry_mask
from rasterio.windows import Window, from_bounds
from rasterio.warp import transform, transform_bounds, transform_geom


MCD12Q1_LC_TYPE1_PROFILE = 'mcd12q1_v061_lc_type1_igbp'
MAX_EDGE = 1600

# MODIS MCD12Q1.061 Land Cover Type 1, IGBP legend.  The labels are data
# definitions from the product documentation, not an interpretation of a map.
IGBP_CLASSES: dict[int, dict[str, str]] = {
    1: {'label_es': 'Bosque perenne de coníferas', 'label_en': 'Evergreen needleleaf forest', 'color': '#05450a'},
    2: {'label_es': 'Bosque perenne de hoja ancha', 'label_en': 'Evergreen broadleaf forest', 'color': '#086a10'},
    3: {'label_es': 'Bosque caducifolio de coníferas', 'label_en': 'Deciduous needleleaf forest', 'color': '#54a708'},
    4: {'label_es': 'Bosque caducifolio de hoja ancha', 'label_en': 'Deciduous broadleaf forest', 'color': '#78d203'},
    5: {'label_es': 'Bosque mixto', 'label_en': 'Mixed forest', 'color': '#009900'},
    6: {'label_es': 'Matorral cerrado', 'label_en': 'Closed shrubland', 'color': '#c6b044'},
    7: {'label_es': 'Matorral abierto', 'label_en': 'Open shrubland', 'color': '#dcd159'},
    8: {'label_es': 'Sabana arbolada', 'label_en': 'Woody savanna', 'color': '#dade48'},
    9: {'label_es': 'Sabana', 'label_en': 'Savanna', 'color': '#fbff13'},
    10: {'label_es': 'Pastizal', 'label_en': 'Grassland', 'color': '#b6ff05'},
    11: {'label_es': 'Humedal permanente', 'label_en': 'Permanent wetland', 'color': '#27ff87'},
    12: {'label_es': 'Cultivo', 'label_en': 'Cropland', 'color': '#c24f44'},
    13: {'label_es': 'Urbano y construido', 'label_en': 'Urban and built-up', 'color': '#a5a5a5'},
    14: {'label_es': 'Mosaico cultivo / vegetación natural', 'label_en': 'Cropland / natural vegetation mosaic', 'color': '#ff6d4c'},
    15: {'label_es': 'Nieve y hielo permanentes', 'label_en': 'Permanent snow and ice', 'color': '#69fff8'},
    16: {'label_es': 'Suelo desnudo o poca vegetación', 'label_en': 'Barren or sparsely vegetated', 'color': '#f9ffa4'},
    17: {'label_es': 'Cuerpos de agua', 'label_en': 'Water bodies', 'color': '#1c0dff'},
}


def is_declared_igbp(asset: dict[str, Any]) -> bool:
    metadata = asset.get('declared_metadata') or {}
    return metadata.get('analysis_profile') == MCD12Q1_LC_TYPE1_PROFILE


def legend() -> list[dict[str, Any]]:
    return [
        {'code': code, **definition}
        for code, definition in sorted(IGBP_CLASSES.items())
    ]


def class_definition(code: int | None) -> dict[str, Any] | None:
    if code is None or code not in IGBP_CLASSES:
        return None
    return {'code': code, **IGBP_CLASSES[code]}


def _valid(data: np.ndarray, nodata: float | int | None) -> np.ndarray:
    mask = np.isfinite(data)
    if nodata is not None:
        mask &= data != nodata
    return mask


def _mask_area_km2(mask: np.ndarray, transform_value, crs) -> float | None:
    """Estimate area on a geographic grid using spherical cell areas.

    The imported MCD12Q1 grids are EPSG:4326.  This avoids reporting a count
    of water pixels as if it were a physical water volume.  If a future raster
    uses another CRS, the API withholds the area KPI instead of approximating it.
    """
    if not crs or crs.to_epsg() != 4326 or transform_value.b != 0 or transform_value.d != 0:
        return None
    rows = np.arange(mask.shape[0], dtype=np.float64)
    north = transform_value.f + transform_value.e * rows
    south = transform_value.f + transform_value.e * (rows + 1)
    earth_radius_km = 6371.0088
    cell_area = (earth_radius_km ** 2) * abs(math.radians(transform_value.a)) * abs(
        np.sin(np.radians(north)) - np.sin(np.radians(south))
    )
    return float(np.dot(mask.sum(axis=1, dtype=np.float64), cell_area))


def _summarize(
    data: np.ndarray,
    nodata: float | int | None,
    included: np.ndarray | None = None,
    *,
    transform_value=None,
    crs=None,
) -> dict[str, Any]:
    selected = included if included is not None else np.ones(data.shape, dtype=bool)
    valid = _valid(data, nodata) & selected
    values = data[valid]
    total = int(values.size)
    codes, counts = np.unique(values, return_counts=True) if total else (np.array([], dtype=np.uint8), np.array([], dtype=np.int64))
    classes = []
    for raw_code, raw_count in sorted(zip(codes, counts), key=lambda item: int(item[1]), reverse=True):
        code, count = int(raw_code), int(raw_count)
        definition = class_definition(code)
        class_area = _mask_area_km2((data == code) & valid, transform_value, crs) if transform_value is not None else None
        classes.append({
            'code': code,
            'pixels': count,
            'percent_valid': round(100 * count / total, 4) if total else 0,
            'area_km2': round(class_area, 4) if class_area is not None else None,
            **(definition or {'label_es': f'Código {code}', 'label_en': f'Code {code}', 'color': '#64748b'}),
        })
    valid_area = _mask_area_km2(valid, transform_value, crs) if transform_value is not None else None
    by_code = {item['code']: item for item in classes}
    return {
        'valid_pixels': total,
        'nodata_pixels': int(selected.sum() - total),
        'selected_pixels': int(selected.sum()),
        'valid_area_km2': round(valid_area, 4) if valid_area is not None else None,
        'water_area_km2': by_code.get(17, {}).get('area_km2'),
        'urban_area_km2': by_code.get(13, {}).get('area_km2'),
        'dominant_class': classes[0] if classes else None,
        'area_method': 'spherical-geographic-cell-area' if valid_area is not None else None,
        'classes': classes,
    }


def summary(source: Path) -> dict[str, Any]:
    with rasterio.open(source) as dataset:
        data = dataset.read(1)
        result = _summarize(data, dataset.nodata, transform_value=dataset.transform, crs=dataset.crs)
        result['grid'] = {
            'width': dataset.width, 'height': dataset.height,
            'crs': dataset.crs.to_string() if dataset.crs else None,
            'resolution': [abs(float(dataset.transform.a)), abs(float(dataset.transform.e))],
        }
    return result


def _window_for_bbox(dataset: rasterio.DatasetReader, bbox: list[float]) -> Window:
    west, south, east, north = bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError('La zona debe ser una extensión válida en WGS 84.')
    if dataset.crs is None:
        raise ValueError('El ráster no declara un CRS.')
    source_bounds = transform_bounds('EPSG:4326', dataset.crs, west, south, east, north, densify_pts=21)
    proposed = from_bounds(*source_bounds, transform=dataset.transform).round_offsets().round_lengths()
    full = Window(0, 0, dataset.width, dataset.height)
    row_start = max(full.row_off, proposed.row_off)
    col_start = max(full.col_off, proposed.col_off)
    row_end = min(full.row_off + full.height, proposed.row_off + proposed.height)
    col_end = min(full.col_off + full.width, proposed.col_off + proposed.width)
    if row_end <= row_start or col_end <= col_start:
        raise ValueError('La zona no intersecta el ráster seleccionado.')
    return Window(col_start, row_start, col_end - col_start, row_end - row_start)


def summary_for_bbox(source: Path, bbox: list[float]) -> dict[str, Any]:
    with rasterio.open(source) as dataset:
        window = _window_for_bbox(dataset, bbox)
        result = _summarize(
            dataset.read(1, window=window), dataset.nodata,
            transform_value=dataset.window_transform(window), crs=dataset.crs,
        )
        result['bbox'] = bbox
        result['window'] = {'column': int(window.col_off), 'row': int(window.row_off), 'width': int(window.width), 'height': int(window.height)}
    return result


def _window_and_mask_for_geometries(dataset: rasterio.DatasetReader, geometries: list[dict[str, Any]]) -> tuple[Window, np.ndarray]:
    if not geometries:
        raise ValueError('Selecciona al menos una provincia.')
    raw_bounds = [geometry_bounds(geometry) for geometry in geometries]
    bbox = [
        min(item[0] for item in raw_bounds), min(item[1] for item in raw_bounds),
        max(item[2] for item in raw_bounds), max(item[3] for item in raw_bounds),
    ]
    window = _window_for_bbox(dataset, bbox)
    projected = [transform_geom('EPSG:4326', dataset.crs, geometry) for geometry in geometries]
    mask = geometry_mask(
        projected,
        out_shape=(int(window.height), int(window.width)),
        transform=dataset.window_transform(window),
        invert=True,
        all_touched=False,
    )
    if not mask.any():
        raise ValueError('La provincia seleccionada no intersecta el ráster.')
    return window, mask


def summary_for_geometries(source: Path, geometries: list[dict[str, Any]]) -> dict[str, Any]:
    with rasterio.open(source) as dataset:
        window, selection = _window_and_mask_for_geometries(dataset, geometries)
        result = _summarize(
            dataset.read(1, window=window), dataset.nodata, selection,
            transform_value=dataset.window_transform(window), crs=dataset.crs,
        )
        result['window'] = {'column': int(window.col_off), 'row': int(window.row_off), 'width': int(window.width), 'height': int(window.height)}
    return result


def class_at(source: Path, longitude: float, latitude: float) -> dict[str, Any]:
    if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
        raise ValueError('La coordenada debe estar en WGS 84.')
    with rasterio.open(source) as dataset:
        if dataset.crs is None:
            raise ValueError('El ráster no declara un CRS.')
        x, y = transform('EPSG:4326', dataset.crs, [longitude], [latitude])
        row, column = dataset.index(x[0], y[0])
        if not (0 <= row < dataset.height and 0 <= column < dataset.width):
            raise ValueError('El punto está fuera del ráster seleccionado.')
        value = dataset.read(1, window=Window(column, row, 1, 1))[0, 0]
        if dataset.nodata is not None and value == dataset.nodata:
            return {'longitude': longitude, 'latitude': latitude, 'row': row, 'column': column, 'code': None, 'class': None, 'nodata': True}
        code = int(value)
        return {'longitude': longitude, 'latitude': latitude, 'row': row, 'column': column, 'code': code, 'class': class_definition(code), 'nodata': False}


def _palette() -> np.ndarray:
    palette = np.zeros((256, 4), dtype=np.uint8)
    for code, item in IGBP_CLASSES.items():
        palette[code, :3] = tuple(int(item['color'][offset:offset + 2], 16) for offset in (1, 3, 5))
        palette[code, 3] = 235
    return palette


def categorical_png(source: Path) -> bytes:
    with rasterio.open(source) as dataset:
        ratio = min(1.0, MAX_EDGE / max(dataset.width, dataset.height))
        height, width = max(1, round(dataset.height * ratio)), max(1, round(dataset.width * ratio))
        data = dataset.read(1, out_shape=(height, width), resampling=rasterio.enums.Resampling.nearest)
        valid = _valid(data, dataset.nodata)
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    indexed = np.clip(data.astype(np.int64), 0, 255).astype(np.uint8)
    palette = _palette()
    rgba[valid] = palette[indexed[valid]]
    image = Image.fromarray(rgba, mode='RGBA')
    buffer = io.BytesIO()
    image.save(buffer, format='PNG', optimize=True)
    return buffer.getvalue()


def compare(
    source_before: Path,
    source_after: Path,
    bbox: list[float] | None = None,
    geometries: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    with rasterio.open(source_before) as before, rasterio.open(source_after) as after:
        compatible = before.count == after.count and before.width == after.width and before.height == after.height and before.crs == after.crs and before.transform.almost_equals(after.transform)
        if not compatible:
            raise ValueError('Los archivos no comparten grilla, CRS y transformación; no se compararon.')
        if bbox and geometries:
            raise ValueError('Selecciona una extensión manual o provincias, no ambas a la vez.')
        if geometries:
            window, selection = _window_and_mask_for_geometries(before, geometries)
        else:
            window = _window_for_bbox(before, bbox) if bbox else None
            shape = (int(window.height), int(window.width)) if window else (before.height, before.width)
            selection = np.ones(shape, dtype=bool)
        first, second = before.read(1, window=window), after.read(1, window=window)
        analysis_transform = before.window_transform(window) if window else before.transform
        analysis_crs = before.crs
        valid = _valid(first, before.nodata) & _valid(second, after.nodata) & selection
    changed = valid & (first != second)
    valid_pixels = int(valid.sum())
    # Cohen's Kappa follows the same marginal-frequency formula as the supplied
    # report, but here it measures *agreement between two compatible maps*.
    # It is intentionally not labelled as classifier accuracy: no ground-truth
    # samples are available in these rasters.
    if valid_pixels:
        before_codes, before_counts = np.unique(first[valid], return_counts=True)
        after_codes, after_counts = np.unique(second[valid], return_counts=True)
        before_marginal = {int(code): int(count) for code, count in zip(before_codes, before_counts)}
        after_marginal = {int(code): int(count) for code, count in zip(after_codes, after_counts)}
        expected_pixels = sum(before_marginal.get(code, 0) * after_marginal.get(code, 0) for code in set(before_marginal) | set(after_marginal))
        observed_agreement = int((first[valid] == second[valid]).sum()) / valid_pixels
        expected_agreement = expected_pixels / (valid_pixels * valid_pixels)
        kappa = (observed_agreement - expected_agreement) / (1 - expected_agreement) if expected_agreement < 1 else (1.0 if observed_agreement == 1 else None)
        agreement_margin_95 = 1.96 * math.sqrt(observed_agreement * (1 - observed_agreement) / valid_pixels)
    else:
        observed_agreement = expected_agreement = kappa = agreement_margin_95 = None
    transitions: list[dict[str, Any]] = []
    if changed.any():
        pairs, counts = np.unique(np.stack((first[changed], second[changed]), axis=1), axis=0, return_counts=True)
        for pair, count in sorted(zip(pairs, counts), key=lambda item: int(item[1]), reverse=True)[:15]:
            from_code, to_code, pixels = int(pair[0]), int(pair[1]), int(count)
            transitions.append({
                'from': class_definition(from_code), 'to': class_definition(to_code), 'pixels': pixels,
                'percent_valid': round(100 * pixels / valid_pixels, 4) if valid_pixels else 0,
            })
    valid_area = _mask_area_km2(valid, analysis_transform, analysis_crs)
    changed_area = _mask_area_km2(changed, analysis_transform, analysis_crs)
    return {
        'bbox': bbox,
        'valid_pixels': valid_pixels,
        'changed_pixels': int(changed.sum()),
        'changed_percent': round(100 * int(changed.sum()) / valid_pixels, 4) if valid_pixels else 0,
        'nodata_pixels': int(selection.sum() - valid_pixels),
        'valid_area_km2': round(valid_area, 4) if valid_area is not None else None,
        'changed_area_km2': round(changed_area, 4) if changed_area is not None else None,
        'agreement': {
            'sample_pixels': valid_pixels,
            'observed_agreement': round(observed_agreement, 8) if observed_agreement is not None else None,
            'expected_agreement': round(expected_agreement, 8) if expected_agreement is not None else None,
            'kappa': round(kappa, 8) if kappa is not None else None,
            'agreement_margin_95': round(agreement_margin_95, 8) if agreement_margin_95 is not None else None,
            'method': 'cohen-kappa-map-agreement',
        },
        'transitions': transitions,
    }
