from fastapi.testclient import TestClient

from backend.geospatial.landcover import MCD12Q1_LC_TYPE1_PROFILE
from backend.main import app


client = TestClient(app)


def _landcover_assets():
    response = client.get('/api/geospatial/assets')
    assert response.status_code == 200, response.text
    return sorted(
        [item for item in response.json()['items'] if item['declared_metadata'].get('analysis_profile') == MCD12Q1_LC_TYPE1_PROFILE],
        key=lambda item: item['captured_at'],
    )


def test_declared_mcd12q1_assets_have_real_class_summary_and_preview():
    status = client.get('/api/geospatial/status')
    assert status.status_code == 200 and status.json()['ready'] is True
    asset = _landcover_assets()[0]
    summary = client.get(f"/api/geospatial/assets/{asset['asset_id']}/land-cover")
    preview = client.get(f"/api/geospatial/assets/{asset['asset_id']}/land-cover/preview")
    assert summary.status_code == 200, summary.text
    assert summary.json()['profile'] == MCD12Q1_LC_TYPE1_PROFILE
    assert summary.json()['statistics']['valid_pixels'] > 0
    assert any(item['code'] == 2 for item in summary.json()['statistics']['classes'])
    assert preview.status_code == 200 and preview.headers['content-type'] == 'image/png'


def test_landcover_comparison_uses_matching_real_grids():
    before, after = _landcover_assets()[0], _landcover_assets()[-1]
    response = client.post(
        f"/api/geospatial/assets/{before['asset_id']}/land-cover/compare",
        json={'after_asset_id': after['asset_id']},
    )
    assert response.status_code == 200, response.text
    comparison = response.json()['comparison']
    assert comparison['valid_pixels'] > 0
    assert comparison['changed_pixels'] >= 0
    assert -1 <= comparison['agreement']['kappa'] <= 1
    assert 0 <= comparison['agreement']['observed_agreement'] <= 1
    assert comparison['agreement']['agreement_margin_95'] is not None


def test_province_selection_uses_persisted_boundaries_and_zonal_statistics():
    areas = client.get('/api/geospatial/admin-areas?level=province')
    assert areas.status_code == 200, areas.text
    assert len(areas.json()['features']) == 24
    assert any(item['properties']['name_es'] == 'Orellana' for item in areas.json()['features'])

    before, after = _landcover_assets()[0], _landcover_assets()[-1]
    summary = client.post(
        f"/api/geospatial/assets/{before['asset_id']}/land-cover/area",
        json={'area_ids': ['22']},
    )
    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload['selection']['areas'][0]['name_es'] == 'Orellana'
    assert payload['statistics']['valid_area_km2'] is not None
    assert payload['statistics']['water_area_km2'] is not None

    comparison = client.post(
        f"/api/geospatial/assets/{before['asset_id']}/land-cover/compare",
        json={'after_asset_id': after['asset_id'], 'area_ids': ['22']},
    )
    assert comparison.status_code == 200, comparison.text
    assert comparison.json()['comparison']['changed_area_km2'] is not None
