"""Block-safe visual products for catalogued GeoTIFFs.

These routines deliberately work from explicitly selected band indices.  They
do not infer satellite products or assign scientific band meanings from a file
name.  Derived PNGs are disposable render cache files; original rasters remain
private, immutable files outside PostgreSQL.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from PIL import Image


MAX_RENDER_EDGE = 1600


def _shape(dataset: rasterio.DatasetReader) -> tuple[int, int]:
    scale = min(1.0, MAX_RENDER_EDGE / max(dataset.width, dataset.height))
    return max(1, round(dataset.height * scale)), max(1, round(dataset.width * scale))


def _stretch(values: np.ma.MaskedArray) -> tuple[np.ndarray, np.ndarray]:
    valid = np.asarray(values.compressed(), dtype=np.float64)
    filled = np.asarray(values.astype(np.float64).filled(np.nan), dtype=np.float64)
    mask = ~np.ma.getmaskarray(values) & np.isfinite(filled)
    if not valid.size:
        return np.zeros(filled.shape, dtype=np.uint8), mask
    low, high = np.nanpercentile(valid, (2, 98))
    if not np.isfinite(low) or not np.isfinite(high) or high <= low:
        high = low + 1
    output = np.clip((filled - low) / (high - low), 0, 1)
    return (np.nan_to_num(output, nan=0.0) * 255).astype(np.uint8), mask


def render_rgb(source: Path, target: Path, bands: tuple[int, int, int]) -> dict[str, Any]:
    """Render a generic RGB composite using a 2–98% display stretch."""
    with rasterio.open(source) as dataset:
        if any(index < 1 or index > dataset.count for index in bands):
            raise ValueError('El índice de banda está fuera de rango.')
        height, width = _shape(dataset)
        image = np.zeros((height, width, 4), dtype=np.uint8)
        valid = np.ones((height, width), dtype=bool)
        stretch: list[dict[str, float | int]] = []
        for channel, index in enumerate(bands):
            data = dataset.read(index, out_shape=(height, width), masked=True)
            values, channel_valid = _stretch(data)
            image[..., channel] = values
            valid &= channel_valid
            compressed = np.asarray(data.compressed(), dtype=np.float64)
            low, high = (np.nanpercentile(compressed, (2, 98)) if compressed.size else (None, None))
            stretch.append({'band': index, 'low': float(low) if low is not None else None, 'high': float(high) if high is not None else None})
    image[..., 3][valid] = 255
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image, mode='RGBA').save(target, format='PNG', optimize=True)
    return {'width': width, 'height': height, 'stretch_percentiles': stretch}


def _scaled(values: np.ma.MaskedArray, scale: float | None, offset: float | None) -> np.ma.MaskedArray:
    # Rasterio reports identity scale/offset when a file does not specify them.
    return values.astype(np.float64) * (1.0 if scale is None else scale) + (0.0 if offset is None else offset)


def render_normalized_difference(source: Path, target: Path, numerator_band: int, denominator_band: int) -> dict[str, Any]:
    """Calculate an explicitly named normalized difference and summary in blocks."""
    if numerator_band == denominator_band:
        raise ValueError('Las dos bandas del índice deben ser diferentes.')
    total = 0
    sum_value = 0.0
    min_value: float | None = None
    max_value: float | None = None
    with rasterio.open(source) as dataset:
        if min(numerator_band, denominator_band) < 1 or max(numerator_band, denominator_band) > dataset.count:
            raise ValueError('El índice de banda está fuera de rango.')
        for _, window in dataset.block_windows(numerator_band):
            numerator = _scaled(dataset.read(numerator_band, window=window, masked=True), dataset.scales[numerator_band - 1], dataset.offsets[numerator_band - 1])
            denominator = _scaled(dataset.read(denominator_band, window=window, masked=True), dataset.scales[denominator_band - 1], dataset.offsets[denominator_band - 1])
            valid = ~(np.ma.getmaskarray(numerator) | np.ma.getmaskarray(denominator))
            raw_denominator = numerator + denominator
            valid &= np.isfinite(raw_denominator) & (np.abs(raw_denominator) > np.finfo(np.float64).eps)
            if not valid.any():
                continue
            index = (numerator - denominator) / raw_denominator
            current = np.asarray(index[valid], dtype=np.float64)
            total += int(current.size)
            sum_value += float(current.sum())
            current_min, current_max = float(current.min()), float(current.max())
            min_value = current_min if min_value is None else min(min_value, current_min)
            max_value = current_max if max_value is None else max(max_value, current_max)

        height, width = _shape(dataset)
        numerator = _scaled(dataset.read(numerator_band, out_shape=(height, width), masked=True), dataset.scales[numerator_band - 1], dataset.offsets[numerator_band - 1])
        denominator = _scaled(dataset.read(denominator_band, out_shape=(height, width), masked=True), dataset.scales[denominator_band - 1], dataset.offsets[denominator_band - 1])
        raw_denominator = numerator + denominator
        valid = ~(np.ma.getmaskarray(numerator) | np.ma.getmaskarray(denominator)) & np.isfinite(raw_denominator) & (np.abs(raw_denominator) > np.finfo(np.float64).eps)
        index = np.zeros((height, width), dtype=np.float64)
        index[valid] = np.asarray(((numerator - denominator) / raw_denominator)[valid])
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    # Diverging display: blue below zero, gold above zero; this is display-only.
    negative = valid & (index < 0)
    positive = valid & ~negative
    rgba[..., 0][negative] = np.clip(80 + 130 * (1 + index[negative]), 0, 255).astype(np.uint8)
    rgba[..., 1][negative] = np.clip(125 + 100 * (1 + index[negative]), 0, 255).astype(np.uint8)
    rgba[..., 2][negative] = 210
    rgba[..., 0][positive] = 230
    rgba[..., 1][positive] = np.clip(130 + 100 * (1 - index[positive]), 0, 255).astype(np.uint8)
    rgba[..., 2][positive] = 80
    rgba[..., 3][valid] = 255
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, mode='RGBA').save(target, format='PNG', optimize=True)
    return {
        'valid_pixels': total,
        'mean': round(sum_value / total, 8) if total else None,
        'minimum': min_value,
        'maximum': max_value,
        'width': width,
        'height': height,
        'scales': {'numerator': dataset.scales[numerator_band - 1], 'denominator': dataset.scales[denominator_band - 1]},
        'offsets': {'numerator': dataset.offsets[numerator_band - 1], 'denominator': dataset.offsets[denominator_band - 1]},
    }
