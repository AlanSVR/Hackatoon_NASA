"""Public configuration for the Ecuador-only point-series screen.

No locality is pre-selected: the person using the application chooses a point
on the Ecuador map and the server records that exact WGS 84 coordinate.
"""
from __future__ import annotations


EARTH_TRENDS_MIN_YEAR = 2021
EARTH_TRENDS_MAX_YEAR = 2026

COUNTRIES = {
    'ecuador': {
        'id': 'ecuador', 'name': 'Ecuador',
        'center': [-1.8312, -78.1834], 'zoom': 6,
        'bounds': [[-5.05, -81.1], [1.5, -75.15]],
    },
}

# The app deliberately does not invent a locality catalogue or provincial
# boundaries. A selected map coordinate is the reproducible query location.
REGIONS: dict[str, dict] = {}

VARIABLES = {
    't2m': {
        'id': 't2m', 'parameter': 'T2M', 'name': 'Temperatura media a 2 m',
        'short_name': 'Temperatura media', 'unit': '°C',
        'definition': 'Temperatura del aire a 2 metros.',
        'provider': 'nasa_power', 'product': 'NASA POWER / MERRA-2',
        'temporal_resolution': 'Mensual', 'spatial_resolution': 'Resolución nativa de la fuente',
        'coverage': '2021–2026 solicitables; la disponibilidad se comprueba en la respuesta del servicio.',
        'missing_value': '-999 (NASA POWER)',
        'limitations': 'Serie para el punto elegido; no representa por sí sola el promedio de un polígono.',
        'annual_aggregation': 'mean',
    },
    'prectotcorr': {
        'id': 'prectotcorr', 'parameter': 'PRECTOTCORR', 'name': 'Precipitación corregida',
        'short_name': 'Precipitación', 'unit': 'mm/día',
        'definition': 'Precipitación media diaria del mes, corregida por NASA POWER.',
        'provider': 'nasa_power', 'product': 'NASA POWER / MERRA-2',
        'temporal_resolution': 'Mensual', 'spatial_resolution': 'Resolución nativa de la fuente',
        'coverage': '2021–2026 solicitables; la disponibilidad se comprueba en la respuesta del servicio.',
        'missing_value': '-999 (NASA POWER)',
        'limitations': 'El valor mensual es una tasa media diaria; el motor calcula el total anual según los días de cada mes.',
        'annual_aggregation': 'precip_rate_to_annual_total',
    },
    'imerg_prectot': {
        'id': 'imerg_prectot', 'parameter': 'IMERG_PRECTOT', 'name': 'Precipitación total (IMERG, si disponible)',
        'short_name': 'Precipitación IMERG', 'unit': 'mm/día',
        'definition': 'Parámetro IMERG_PRECTOT expuesto por NASA POWER.',
        'provider': 'nasa_power', 'product': 'NASA POWER / IMERG_PRECTOT',
        'temporal_resolution': 'Mensual', 'spatial_resolution': 'Resolución nativa de la fuente',
        'coverage': '2021–2026 solicitables; se valida por punto y período.',
        'missing_value': '-999 (NASA POWER)',
        'limitations': 'Puede no estar disponible para una coordenada o período. Nunca se sustituye por un producto distinto.',
        'annual_aggregation': 'precip_rate_to_annual_total',
    },
}

PROVIDERS = {
    'nasa_power': {
        'id': 'nasa_power', 'name': 'NASA POWER', 'status': 'functional',
        'description': 'Consulta temporal mensual de punto mediante HTTP desde FastAPI.',
        'documentation_url': 'https://power.larc.nasa.gov/docs/services/api/temporal/',
        'spatial_support': 'Punto. Las geometrías de área son sólo una referencia visual en esta pantalla.',
    },
}


def public_regions(country_id: str | None = None) -> list[dict]:
    if country_id and country_id not in COUNTRIES:
        return []
    return []
