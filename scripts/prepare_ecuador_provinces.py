"""Download and simplify the Ecuador provincial boundary source for the app.

The source service attributes the polygons to INEC's División Político
Administrativa and identifies the geometry year in ``DPA_ANIO``.  We retain
that provenance in the resulting GeoJSON and deliberately exclude the
``ZONA NO DELIMITADA`` feature: it is not a province a person can select.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen


SOURCE_URL = (
    'https://services7.arcgis.com/iFGeGXTAJXnjq0YN/arcgis/rest/services/'
    'Provincias_del_Ecuador/FeatureServer/0/query?where=1%3D1&'
    'outFields=OBJECTID%2CDPA_PROVIN%2CDPA_DESPRO%2CDPA_ANIO%2CAREA_KM2&'
    'returnGeometry=true&outSR=4326&f=geojson'
)
SOURCE_TITLE = 'Provincias del Ecuador - capa basada en información oficial del INEC'
PROVINCE_NAMES = {
    '01': 'Azuay', '02': 'Bolívar', '03': 'Cañar', '04': 'Carchi', '05': 'Cotopaxi',
    '06': 'Chimborazo', '07': 'El Oro', '08': 'Esmeraldas', '09': 'Guayas', '10': 'Imbabura',
    '11': 'Loja', '12': 'Los Ríos', '13': 'Manabí', '14': 'Morona Santiago', '15': 'Napo',
    '16': 'Pastaza', '17': 'Pichincha', '18': 'Tungurahua', '19': 'Zamora Chinchipe',
    '20': 'Galápagos', '21': 'Sucumbíos', '22': 'Orellana', '23': 'Santo Domingo de los Tsáchilas',
    '24': 'Santa Elena',
}


def _distance(point: list[float], first: list[float], last: list[float]) -> float:
    """Perpendicular distance in degrees; suitable for visual simplification."""
    x, y = point
    x1, y1 = first
    x2, y2 = last
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(x - x1, y - y1)
    ratio = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
    projection = [x1 + ratio * dx, y1 + ratio * dy]
    return math.hypot(x - projection[0], y - projection[1])


def _rdp(points: list[list[float]], tolerance: float) -> list[list[float]]:
    if len(points) < 3:
        return points
    largest_distance, index = 0.0, 0
    for current in range(1, len(points) - 1):
        distance = _distance(points[current], points[0], points[-1])
        if distance > largest_distance:
            largest_distance, index = distance, current
    if largest_distance <= tolerance:
        return [points[0], points[-1]]
    return _rdp(points[: index + 1], tolerance)[:-1] + _rdp(points[index:], tolerance)


def _simplify_ring(ring: list[list[float]], tolerance: float) -> list[list[float]]:
    if len(ring) < 5:
        return ring
    closed = ring[0] == ring[-1]
    raw = ring[:-1] if closed else ring
    # Split the closed ring in two sections to prevent an artificial diagonal
    # between its first and final point during RDP simplification.
    midpoint = max(1, len(raw) // 2)
    reduced = _rdp(raw[: midpoint + 1], tolerance)[:-1] + _rdp(raw[midpoint:] + [raw[0]], tolerance)
    if len(reduced) < 3:
        reduced = raw
    return reduced + [reduced[0]]


def _simplify_geometry(geometry: dict, tolerance: float) -> dict:
    if geometry['type'] == 'Polygon':
        return {**geometry, 'coordinates': [_simplify_ring(ring, tolerance) for ring in geometry['coordinates']]}
    if geometry['type'] == 'MultiPolygon':
        return {
            **geometry,
            'coordinates': [
                [_simplify_ring(ring, tolerance) for ring in polygon]
                for polygon in geometry['coordinates']
            ],
        }
    raise ValueError(f"Geometría no esperada: {geometry['type']}")


def download_source() -> dict:
    request = Request(SOURCE_URL, headers={'User-Agent': 'AndesSAR-local-boundary-import/1.0'})
    with urlopen(request, timeout=90) as response:  # noqa: S310 - fixed public source URL
        return json.load(response)


def build_collection(source: dict, tolerance: float) -> dict:
    features = []
    for feature in source.get('features', []):
        properties = feature.get('properties') or {}
        code = str(properties.get('DPA_PROVIN') or '').zfill(2)
        name = PROVINCE_NAMES.get(code, str(properties.get('DPA_DESPRO') or '').strip())
        if not name or name.upper() == 'ZONA NO DELIMITADA':
            continue
        features.append({
            'type': 'Feature',
            'id': code or str(feature.get('id')),
            'properties': {
                'area_id': code or str(feature.get('id')),
                'name_es': name,
                'name_en': name,
                'level': 'province',
                'source_year': str(properties.get('DPA_ANIO') or 'no declarado'),
                'source_area_km2': properties.get('AREA_KM2'),
            },
            'geometry': _simplify_geometry(feature['geometry'], tolerance),
        })
    features.sort(key=lambda item: item['properties']['name_es'])
    if len(features) != 24:
        raise ValueError(f'Se esperaban 24 provincias y se recibieron {len(features)}.')
    return {
        'type': 'FeatureCollection',
        'metadata': {
            'title': 'Provincias del Ecuador',
            'source_title': SOURCE_TITLE,
            'source_url': SOURCE_URL,
            'retrieved_on': date.today().isoformat(),
            'crs': 'EPSG:4326',
            'simplification_tolerance_degrees': tolerance,
            'note_es': 'Geometrías administrativas para selección zonal; no sustituyen la delimitación legal.',
        },
        'features': features,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('backend/geospatial/data/ecuador_provinces.geojson'))
    parser.add_argument('--tolerance', type=float, default=0.0015)
    args = parser.parse_args()
    collection = build_collection(download_source(), args.tolerance)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(collection, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'features={len(collection["features"])}')
    print(f'output={args.output}')


if __name__ == '__main__':
    main()
