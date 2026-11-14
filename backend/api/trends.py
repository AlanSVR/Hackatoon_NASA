from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from backend.core.catalog import COUNTRIES, PROVIDERS, VARIABLES, public_regions
from backend.models.schemas import AnomalyRequest, CompareRequest, TimeSeriesRequest
from backend.providers.nasa_power import ProviderConnectionError
from backend.services.exports import ExportStore
from backend.services.timeseries import CatalogError, load_series
from backend.statistics.trends import calculate_anomalies, calculate_trend, compare_years

router = APIRouter(prefix='/api', tags=['Earth Trends'])
exports = ExportStore()


def _load_or_422(request):
    try:
        return load_series(request)
    except CatalogError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ProviderConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get('/countries')
def countries():
    return sorted((dict(item) for item in COUNTRIES.values()), key=lambda item: item['name'])


@router.get('/regions')
def regions(country_id: str | None = Query(default=None, max_length=64)):
    if country_id and country_id not in COUNTRIES:
        raise HTTPException(status_code=404, detail='País no configurado.')
    return public_regions(country_id)


@router.get('/variables')
def variables():
    return [dict(value) for value in VARIABLES.values()]


@router.get('/providers')
def providers():
    return [dict(value) for value in PROVIDERS.values()]


@router.get('/data-availability')
def data_availability(variable_id: str | None = None):
    catalog = [VARIABLES[variable_id]] if variable_id in VARIABLES else list(VARIABLES.values())
    if variable_id and variable_id not in VARIABLES:
        raise HTTPException(status_code=404, detail='Variable no configurada.')
    return {
        'provider_id': 'nasa_power',
        'query_kind': 'monthly_point',
        'availability_is_verified_per_request': True,
        'note': 'La cobertura efectiva se valida con la respuesta real de NASA POWER; los fill values se reportan como faltantes.',
        'variables': [dict(item) for item in catalog],
    }


@router.post('/timeseries')
def timeseries(request: TimeSeriesRequest):
    return _load_or_422(request)


@router.post('/trends')
def trends(request: TimeSeriesRequest):
    series = _load_or_422(request)
    trend = calculate_trend(series['observations'], series['variable'])
    report = {'series': series, 'trend': trend}
    report['export_id'] = exports.put(report)
    return report


@router.post('/anomalies')
def anomalies(request: AnomalyRequest):
    series = _load_or_422(request)
    anomaly = calculate_anomalies(
        series['observations'], request.baseline_start_year, request.baseline_end_year,
    )
    return {'series': series, 'anomalies': anomaly}


@router.post('/compare')
def compare(request: CompareRequest):
    series = _load_or_422(request)
    comparison = compare_years(series['observations'], series['variable'], request.year_a, request.year_b)
    return {'series': series, 'comparison': comparison}


@router.get('/exports/{export_id}')
def get_export(export_id: str, format: str = Query(default='json', pattern='^(json|csv)$')):
    item = exports.get(export_id)
    if not item:
        raise HTTPException(status_code=404, detail='La exportación ya no está disponible en esta sesión local.')
    report = item['report']
    if format == 'csv':
        return PlainTextResponse(
            exports.as_csv(report), media_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename="andes-sar-earth-trends-{export_id}.csv"'},
        )
    return JSONResponse(
        report,
        headers={'Content-Disposition': f'attachment; filename="andes-sar-earth-trends-{export_id}.json"'},
    )
