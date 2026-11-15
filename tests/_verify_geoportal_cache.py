from fastapi.testclient import TestClient

from backend.main import app


asset_id = '2536924a-b18b-40b1-b5a2-e6b04b1df2c3'
client = TestClient(app)
status = client.get('/api/geospatial/status')
assert status.status_code == 200 and status.json()['ready'] is True, status.text
rgb = client.post(f'/api/geospatial/assets/{asset_id}/renders/rgb', json={'red_band': 2, 'green_band': 6, 'blue_band': 5})
assert rgb.status_code == 200 and rgb.json()['cached'] is True, rgb.text
index = client.post(f'/api/geospatial/assets/{asset_id}/analyses/normalized-difference', json={
    'numerator_band': 2, 'denominator_band': 3, 'manual_semantics_confirmed': True,
})
assert index.status_code == 200 and index.json()['cached'] is True, index.text
print({'asset_count': status.json()['asset_count'], 'rgb_cached': rgb.json()['cached'], 'index_cached': index.json()['cached']})
