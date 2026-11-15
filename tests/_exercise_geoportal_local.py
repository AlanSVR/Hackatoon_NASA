"""Manual integration exercise; created only for the local verification run."""
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)
source = Path('02_2021') / '02_2021.0.tif'
size = source.stat().st_size
created = client.post('/api/geospatial/uploads/sessions', json={
    'file_name': '02_2021.0.tif', 'total_bytes': size, 'asset_kind': 'raster',
    'captured_at': '2021-01-01', 'declared_metadata': {'source_test': '02_2021'},
})
assert created.status_code == 201, created.text
session = created.json()
with source.open('rb') as stream:
    for index in range(session['expected_chunks']):
        response = client.put(
            session['put_chunk_url_template'].replace('{chunk_index}', str(index)),
            content=stream.read(session['chunk_bytes']),
            headers={'Content-Type': 'application/octet-stream'},
        )
        assert response.status_code == 200, response.text
completed = client.post(session['complete_url'])
assert completed.status_code == 200, completed.text
asset_id = completed.json()['asset_id']
detail = client.get(f'/api/geospatial/assets/{asset_id}')
assert detail.status_code == 200, detail.text
assert detail.json()['band_count'] == 6
preview = client.get(f'/api/geospatial/assets/{asset_id}/preview?band=1')
assert preview.status_code == 200 and preview.headers['content-type'] == 'image/png'
capabilities = client.get(f'/api/geospatial/assets/{asset_id}/analysis-capabilities')
assert capabilities.status_code == 200 and capabilities.json()['generic_rgb'] is True
rgb = client.post(f'/api/geospatial/assets/{asset_id}/renders/rgb', json={'red_band': 2, 'green_band': 6, 'blue_band': 5})
assert rgb.status_code == 200, rgb.text
render = client.get(rgb.json()['image_url'])
assert render.status_code == 200 and render.headers['content-type'] == 'image/png'
index = client.post(f'/api/geospatial/assets/{asset_id}/analyses/normalized-difference', json={
    'numerator_band': 2, 'denominator_band': 3, 'manual_semantics_confirmed': True,
})
assert index.status_code == 200, index.text
print({
    'asset_id': asset_id, 'bytes': size, 'band_count': detail.json()['band_count'],
    'epsg': detail.json()['epsg'], 'rgb_cached': rgb.json()['cached'],
    'rgb_semantic_status': rgb.json()['semantic_status'],
    'index_valid_pixels': index.json()['summary']['valid_pixels'], 'index_cached': index.json()['cached'],
})
