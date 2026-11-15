from __future__ import annotations

from calendar import monthrange

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.timeseries import series_cache
from backend.statistics.trends import annual_aggregate

client = TestClient(app)


def fake_power_series(*, parameter, latitude, longitude, start_year, end_year):
    observations = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            # Tendencia anual conocida más una componente estacional, que la
            # agregación anual no debe confundir con la pendiente de largo plazo.
            observations.append({
                'date': f'{year}-{month:02d}-01',
                'value': round(12 + (year - start_year) * .35 + month * .04, 4),
            })
    return {
        'observations': observations,
        'metadata': {
            'request_url': 'https://power.larc.nasa.gov/example',
            'provider_header': {'sources': ['MERRA2']},
            'parameter_info': {'units': 'C'}, 'fill_value': -999,
            'time_standard': 'LST', 'messages': [],
        },
    }


def test_catalog_endpoints_are_explicit():
    countries = client.get('/api/countries')
    assert countries.status_code == 200
    assert {item['id'] for item in countries.json()} == {'ecuador'}
    regions = client.get('/api/regions?country_id=ecuador')
    assert regions.status_code == 200
    assert regions.json() == []
    variables = client.get('/api/variables')
    assert any(item['parameter'] == 'T2M' for item in variables.json())


def test_trend_anomaly_comparison_and_exports(monkeypatch):
    monkeypatch.setattr('backend.services.timeseries.provider.fetch_monthly', fake_power_series)
    series_cache._items.clear()
    request = {
        'country_id': 'ecuador', 'latitude': -1.8312, 'longitude': -78.1834,
        'variable_id': 't2m', 'start_year': 2021, 'end_year': 2026,
    }
    trend = client.post('/api/trends', json=request)
    assert trend.status_code == 200, trend.text
    payload = trend.json()
    assert payload['series']['quality']['valid_observations'] == 72
    assert payload['trend']['n_annual_observations'] == 6
    # The configured 2021–2026 window contains six annual aggregates; the
    # analysis correctly withholds a significance claim for that short series.
    assert payload['trend']['is_significant'] is None
    assert payload['trend']['slope_per_year'] > 0
    assert payload['trend']['confidence_interval_95'] is None

    anomalies = client.post('/api/anomalies', json={
        **request, 'baseline_start_year': 2021, 'baseline_end_year': 2026,
    })
    assert anomalies.status_code == 200, anomalies.text
    assert len(anomalies.json()['anomalies']['observations']) == 72

    comparison = client.post('/api/compare', json={**request, 'year_a': 2021, 'year_b': 2026})
    assert comparison.status_code == 200, comparison.text
    assert comparison.json()['comparison']['difference'] > 0
    export_id = payload['export_id']
    assert client.get(f'/api/exports/{export_id}?format=json').status_code == 200
    csv = client.get(f'/api/exports/{export_id}?format=csv')
    assert csv.status_code == 200
    assert csv.text.startswith('date,value')


def test_precipitation_rate_is_converted_to_actual_days_before_annual_sum():
    observations = [
        {'date': f'2020-{month:02d}-01', 'value': 1.0}
        for month in range(1, 13)
    ] + [
        {'date': f'2021-{month:02d}-01', 'value': 1.0}
        for month in range(1, 13)
    ]
    annual, unit, _ = annual_aggregate(observations, {'annual_aggregation': 'precip_rate_to_annual_total', 'unit': 'mm/día'})
    assert unit == 'mm/año'
    assert annual[0]['value'] == sum(monthrange(2020, month)[1] for month in range(1, 13))
    assert annual[1]['value'] == 365


def test_local_tif_lab_inspects_and_compares_only_compatible_grids():
    catalog = client.get('/api/tif-lab/catalog')
    assert catalog.status_code == 200
    items = catalog.json()['items']
    assert len(items) >= 32
    before = next(item for item in items if item['layer'] == 'LC_Type5' and item['year'] == 2021)
    after = next(item for item in items if item['layer'] == 'LC_Type5' and item['year'] == 2025)

    inspection = client.get(f"/api/tif-lab/inspect/{before['id']}")
    assert inspection.status_code == 200
    assert inspection.json()['epsg'] == 4326
    assert inspection.json()['valid_pixels'] > 0
    preview = client.get(f"/api/tif-lab/preview/{before['id']}")
    assert preview.status_code == 200
    assert preview.headers['content-type'].startswith('image/png')

    comparison = client.post('/api/tif-lab/compare', json={
        'before_id': before['id'], 'after_id': after['id'],
    })
    assert comparison.status_code == 200, comparison.text
    payload = comparison.json()
    assert payload['statistics']['valid_pixels'] > 0
    assert payload['method']['resampling'] == 'ninguno; comparación directa de la grilla original'
    assert client.get(payload['comparison_preview_url']).headers['content-type'].startswith('image/png')


def test_local_tif_lab_includes_the_prepared_ecu_cp_series():
    items = client.get('/api/tif-lab/catalog').json()['items']
    prepared = [item for item in items if item['collection'] == 'Ecu Cp']
    assert [item['year'] for item in prepared] == [2021, 2022, 2023, 2024, 2025]
    assert {item['layer'] for item in prepared} == {'Ecu Cp preparado'}
    response = client.post('/api/tif-lab/compare', json={
        'before_id': prepared[0]['id'], 'after_id': prepared[-1]['id'],
    })
    assert response.status_code == 200, response.text
    assert response.json()['statistics']['valid_pixels'] == 1_205_368


def test_local_tif_lab_lists_unverified_02_2021_without_inventing_band_semantics():
    items = client.get('/api/tif-lab/catalog').json()['items']
    asset = next(item for item in items if item['collection'] == '02_2021' and item['file_name'] == 'Zona Norte 2021.tiff')
    assert asset['kind'] == 'unverified_raster'
    inspection = client.get(f"/api/tif-lab/inspect/{asset['id']}")
    assert inspection.status_code == 200
    assert inspection.json()['band_count'] == 6
    assert inspection.json()['histogram'] == []
    assert inspection.json()['interpretation'].startswith('NO VERIFICADO')


def test_geoportal_reports_configuration_without_leaking_a_connection_string():
    response = client.get('/api/geospatial/status')
    assert response.status_code == 200
    payload = response.json()
    assert {'ready', 'max_upload_bytes', 'chunk_bytes', 'upload_protection'} <= payload.keys()
    assert 'database_url' not in payload
