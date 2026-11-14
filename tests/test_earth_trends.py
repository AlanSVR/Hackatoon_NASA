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
    assert {item['id'] for item in countries.json()} == {'ecuador', 'united_states', 'canada'}
    regions = client.get('/api/regions?country_id=canada')
    assert regions.status_code == 200
    assert len(regions.json()) == 2
    variables = client.get('/api/variables')
    assert any(item['parameter'] == 'T2M' for item in variables.json())


def test_trend_anomaly_comparison_and_exports(monkeypatch):
    monkeypatch.setattr('backend.services.timeseries.provider.fetch_monthly', fake_power_series)
    series_cache._items.clear()
    request = {
        'country_id': 'ecuador', 'region_id': 'riobamba_chimborazo',
        'variable_id': 't2m', 'start_year': 2010, 'end_year': 2019,
    }
    trend = client.post('/api/trends', json=request)
    assert trend.status_code == 200, trend.text
    payload = trend.json()
    assert payload['series']['quality']['valid_observations'] == 120
    assert payload['trend']['n_annual_observations'] == 10
    assert payload['trend']['is_significant'] is True
    assert payload['trend']['slope_per_year'] > 0
    assert payload['trend']['confidence_interval_95'][0] > 0

    anomalies = client.post('/api/anomalies', json={
        **request, 'baseline_start_year': 2010, 'baseline_end_year': 2019,
    })
    assert anomalies.status_code == 200, anomalies.text
    assert len(anomalies.json()['anomalies']['observations']) == 120

    comparison = client.post('/api/compare', json={**request, 'year_a': 2010, 'year_b': 2019})
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
