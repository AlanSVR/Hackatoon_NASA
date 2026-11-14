from __future__ import annotations

import json
from typing import Any

from backend.core.catalog import REGIONS, VARIABLES
from backend.providers.nasa_power import NasaPowerProvider
from backend.services.cache import TTLCache

series_cache = TTLCache(ttl_seconds=900, max_entries=64)
provider = NasaPowerProvider()


class CatalogError(ValueError):
    pass


def resolve_location(*, country_id: str, region_id: str | None, latitude: float | None, longitude: float | None) -> dict[str, Any]:
    if latitude is not None and longitude is not None:
        return {
            'name': 'Punto seleccionado en el mapa', 'country_id': country_id,
            'region_id': region_id, 'latitude': latitude, 'longitude': longitude,
            'selection_kind': 'point',
        }
    region = REGIONS.get(region_id or '')
    if not region:
        raise CatalogError('La región seleccionada no está configurada.')
    if region['country_id'] != country_id:
        raise CatalogError('La región no corresponde al país seleccionado.')
    return {
        'name': region['name'], 'country_id': country_id, 'region_id': region['id'],
        'latitude': region['latitude'], 'longitude': region['longitude'], 'selection_kind': 'configured_region_point',
    }


def get_variable(variable_id: str) -> dict[str, Any]:
    variable = VARIABLES.get(variable_id)
    if not variable:
        raise CatalogError('La variable solicitada no está disponible en este MVP.')
    return dict(variable)


def load_series(request) -> dict[str, Any]:
    variable = get_variable(request.variable_id)
    location = resolve_location(
        country_id=request.country_id, region_id=request.region_id,
        latitude=request.latitude, longitude=request.longitude,
    )
    cache_key = json.dumps({
        'provider': request.provider_id, 'parameter': variable['parameter'],
        'lat': round(location['latitude'], 5), 'lon': round(location['longitude'], 5),
        'start': request.start_year, 'end': request.end_year,
    }, sort_keys=True)
    cached = series_cache.get(cache_key)
    if cached:
        cached['cached'] = True
        return cached
    source = provider.fetch_monthly(
        parameter=variable['parameter'], latitude=location['latitude'], longitude=location['longitude'],
        start_year=request.start_year, end_year=request.end_year,
    )
    observations = source['observations']
    valid = sum(item['value'] is not None for item in observations)
    expected = (request.end_year - request.start_year + 1) * 12
    result = {
        'provider': {'id': 'nasa_power', 'name': 'NASA POWER'},
        'variable': variable,
        'location': location,
        'period': {'start_year': request.start_year, 'end_year': request.end_year, 'frequency': 'monthly'},
        'observations': observations,
        'quality': {
            'expected_observations': expected, 'valid_observations': valid,
            'missing_observations': expected - valid,
            'valid_percent': round((valid / expected) * 100, 2) if expected else 0,
            'is_point_series': True,
            'note': 'NASA POWER devuelve una serie para un punto. No se interpreta como promedio espacial de una selección de área.',
        },
        'metadata': source['metadata'],
        'cached': False,
    }
    series_cache.put(cache_key, result)
    return result
