from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from backend.providers.base import DataProvider

POWER_MONTHLY_POINT_URL = 'https://power.larc.nasa.gov/api/temporal/monthly/point'
POWER_TIMEOUT_SECONDS = 20
POWER_FILL_THRESHOLD = -900.0


class ProviderConnectionError(RuntimeError):
    pass


class NasaPowerProvider(DataProvider):
    provider_id = 'nasa_power'

    def fetch_monthly(
        self, *, parameter: str, latitude: float, longitude: float, start_year: int, end_year: int,
    ) -> dict[str, Any]:
        # La URL base es fija. Los únicos valores variables son coordenadas,
        # fechas y el parámetro presente en el catálogo local.
        query = urlencode({
            'parameters': parameter,
            'community': 'RE',
            'longitude': f'{longitude:.5f}',
            'latitude': f'{latitude:.5f}',
            'format': 'JSON',
            'start': start_year,
            'end': end_year,
        })
        request_url = f'{POWER_MONTHLY_POINT_URL}?{query}'
        try:
            with urlopen(request_url, timeout=POWER_TIMEOUT_SECONDS) as response:  # noqa: S310: URL constante de NASA POWER
                raw = response.read().decode('utf-8')
        except HTTPError as exc:
            detail = exc.read().decode('utf-8', errors='replace')[:400]
            raise ProviderConnectionError(f'NASA POWER respondió HTTP {exc.code}: {detail}') from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ProviderConnectionError(
                'No se pudo contactar NASA POWER. Comprueba la conexión e inténtalo de nuevo.'
            ) from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderConnectionError('NASA POWER devolvió una respuesta que no es JSON válido.') from exc
        if payload.get('messages') and not payload.get('properties', {}).get('parameter'):
            raise ProviderConnectionError(f"NASA POWER rechazó la consulta: {payload['messages']}")

        properties = payload.get('properties') or {}
        parameters = properties.get('parameter') or {}
        values = parameters.get(parameter)
        if not isinstance(values, dict):
            raise ProviderConnectionError(f'NASA POWER no devolvió el parámetro {parameter}.')
        # POWER sitúa `header` y `parameters` al nivel superior del JSON;
        # `properties` contiene la matriz temporal bajo `parameter`.
        declared = ((payload.get('parameters') or {}).get(parameter) or {})
        observations: list[dict[str, Any]] = []
        for period, raw_value in sorted(values.items()):
            # YYYYMM; YYYY13 es la agregación anual de POWER y no se mezcla con la serie mensual.
            if len(period) != 6 or not period.isdigit() or period[4:] == '13':
                continue
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                value = None
            if value is not None and value <= POWER_FILL_THRESHOLD:
                value = None
            observations.append({'date': f'{period[:4]}-{period[4:]}-01', 'value': value})

        header = payload.get('header') or {}
        return {
            'observations': observations,
            'metadata': {
                'request_url': request_url,
                'provider_header': header,
                'parameter_info': declared,
                'fill_value': header.get('fill_value', -999),
                'time_standard': header.get('time_standard'),
                'messages': payload.get('messages') or [],
            },
        }
