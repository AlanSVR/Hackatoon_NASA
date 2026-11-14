"""Catálogo explícito del MVP; no se deduce cobertura global ni productos."""
from __future__ import annotations

from datetime import date

LATEST_POWER_YEAR = date.today().year - 1

COUNTRIES = {
    'ecuador': {
        'id': 'ecuador', 'name': 'Ecuador',
        'center': [-1.8312, -78.1834], 'zoom': 6,
        'bounds': [[-5.05, -81.1], [1.5, -75.15]],
    },
    'united_states': {
        'id': 'united_states', 'name': 'Estados Unidos',
        'center': [39.8283, -98.5795], 'zoom': 4,
        'bounds': [[24.3, -125.1], [49.6, -66.8]],
    },
    'canada': {
        'id': 'canada', 'name': 'Canadá',
        'center': [56.1304, -106.3468], 'zoom': 3,
        'bounds': [[41.65, -141.1], [83.2, -52.5]],
    },
}

# Coordenadas de navegación comprobables y explícitas. Representan el punto
# de consulta NASA POWER, nunca un promedio de toda la localidad o provincia.
REGIONS = {
    'riobamba_chimborazo': {
        'id': 'riobamba_chimborazo', 'country_id': 'ecuador',
        'name': 'Riobamba, Chimborazo', 'latitude': -1.8312, 'longitude': -78.1834,
        'zoom': 10,
    },
    'quito_pichincha': {
        'id': 'quito_pichincha', 'country_id': 'ecuador',
        'name': 'Quito, Pichincha', 'latitude': -0.1807, 'longitude': -78.4678,
        'zoom': 10,
    },
    'denver_colorado': {
        'id': 'denver_colorado', 'country_id': 'united_states',
        'name': 'Denver, Colorado', 'latitude': 39.7392, 'longitude': -104.9903,
        'zoom': 10,
    },
    'phoenix_arizona': {
        'id': 'phoenix_arizona', 'country_id': 'united_states',
        'name': 'Phoenix, Arizona', 'latitude': 33.4484, 'longitude': -112.0740,
        'zoom': 10,
    },
    'calgary_alberta': {
        'id': 'calgary_alberta', 'country_id': 'canada',
        'name': 'Calgary, Alberta', 'latitude': 51.0447, 'longitude': -114.0719,
        'zoom': 10,
    },
    'vancouver_british_columbia': {
        'id': 'vancouver_british_columbia', 'country_id': 'canada',
        'name': 'Vancouver, Columbia Británica', 'latitude': 49.2827, 'longitude': -123.1207,
        'zoom': 10,
    },
}

# Los parámetros y unidades se conservan tal como los declara la respuesta de
# NASA POWER. IMERG_PRECTOT aparece en la API, pero puede devolver fill values
# para combinaciones de punto/período; nunca se sustituye por datos ficticios.
VARIABLES = {
    't2m': {
        'id': 't2m', 'parameter': 'T2M', 'name': 'Temperatura media a 2 m',
        'short_name': 'Temperatura media', 'unit': '°C',
        'definition': 'Temperatura del aire a 2 metros.',
        'provider': 'nasa_power', 'product': 'NASA POWER / MERRA-2',
        'temporal_resolution': 'Mensual', 'spatial_resolution': 'Resolución nativa de la fuente',
        'coverage': f'1981–{LATEST_POWER_YEAR} (verificar en la respuesta del servicio)',
        'missing_value': '-999 (NASA POWER)',
        'limitations': 'Serie puntual de una celda/fuente; no representa por sí sola el promedio de un polígono.',
        'annual_aggregation': 'mean',
    },
    'prectotcorr': {
        'id': 'prectotcorr', 'parameter': 'PRECTOTCORR', 'name': 'Precipitación corregida',
        'short_name': 'Precipitación', 'unit': 'mm/día',
        'definition': 'Precipitación media diaria del mes, corregida por NASA POWER.',
        'provider': 'nasa_power', 'product': 'NASA POWER / MERRA-2',
        'temporal_resolution': 'Mensual', 'spatial_resolution': 'Resolución nativa de la fuente',
        'coverage': f'1981–{LATEST_POWER_YEAR} (verificar en la respuesta del servicio)',
        'missing_value': '-999 (NASA POWER)',
        'limitations': 'El valor mensual es una tasa media diaria. Para el total anual, el motor multiplica cada mes por sus días antes de sumar.',
        'annual_aggregation': 'precip_rate_to_annual_total',
    },
    'imerg_prectot': {
        'id': 'imerg_prectot', 'parameter': 'IMERG_PRECTOT', 'name': 'Precipitación total (IMERG, si disponible)',
        'short_name': 'Precipitación IMERG', 'unit': 'mm/día',
        'definition': 'Parámetro IMERG_PRECTOT expuesto por NASA POWER; la disponibilidad se valida para cada punto y período.',
        'provider': 'nasa_power', 'product': 'NASA POWER / IMERG_PRECTOT',
        'temporal_resolution': 'Mensual', 'spatial_resolution': 'Resolución nativa de la fuente',
        'coverage': 'Depende de la respuesta de NASA POWER para el punto y período solicitados.',
        'missing_value': '-999 (NASA POWER)',
        'limitations': 'Puede no estar disponible para una combinación de coordenadas y fechas. No se reemplaza automáticamente por otro producto.',
        'annual_aggregation': 'precip_rate_to_annual_total',
    },
}

PROVIDERS = {
    'nasa_power': {
        'id': 'nasa_power', 'name': 'NASA POWER', 'status': 'functional',
        'description': 'Consulta temporal mensual de punto mediante HTTP desde FastAPI.',
        'documentation_url': 'https://power.larc.nasa.gov/docs/services/api/temporal/',
        'spatial_support': 'Punto. Las selecciones de área se conservan visualmente, pero no se convierten en un promedio espacial.',
    },
    'appeears': {
        'id': 'appeears', 'name': 'NASA AppEEARS', 'status': 'planned',
        'description': 'Interfaz prevista para trabajos asíncronos y productos espaciales; no conectada en este MVP.',
        'spatial_support': 'Pendiente de integración.',
    },
    'noaa_cdo': {
        'id': 'noaa_cdo', 'name': 'NOAA CDO', 'status': 'planned',
        'description': 'Adaptador futuro; no se simula una conexión.',
        'spatial_support': 'Pendiente de integración.',
    },
    'local_raster': {
        'id': 'local_raster', 'name': 'Raster local / SAR', 'status': 'experimental',
        'description': 'Conserva el comparador SAR exploratorio existente en /api/analyze.',
        'spatial_support': 'Rectángulo dentro de la zona de demostración de Riobamba.',
    },
}


def public_regions(country_id: str | None = None) -> list[dict]:
    values = [dict(item) for item in REGIONS.values()
              if country_id is None or item['country_id'] == country_id]
    return sorted(values, key=lambda item: item['name'])
