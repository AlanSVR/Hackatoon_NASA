from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_health():
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['ok']


def test_public_catalog_is_ecuador_only_and_has_no_fake_localities():
    countries = client.get('/api/countries')
    regions = client.get('/api/regions?country_id=ecuador')
    assert countries.status_code == 200
    assert countries.json() == [
        {
            'id': 'ecuador', 'name': 'Ecuador', 'center': [-1.8312, -78.1834],
            'zoom': 6, 'bounds': [[-5.05, -81.1], [1.5, -75.15]],
        }
    ]
    assert regions.status_code == 200
    assert regions.json() == []


def test_trends_requires_a_user_selected_point_and_valid_year_window():
    no_point = client.post('/api/trends', json={'start_year': 2021, 'end_year': 2026})
    outside_window = client.post('/api/trends', json={
        'latitude': -1.8, 'longitude': -78.2, 'start_year': 2020, 'end_year': 2026,
    })
    assert no_point.status_code == 422
    assert outside_window.status_code == 422
