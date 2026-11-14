from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health():
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['ok']

def test_dynamic_analysis():
    scenes = client.get('/api/scenes').json()
    assert len(scenes) >= 2
    response = client.post('/api/analyze', json={
        'before_id': scenes[0]['id'],
        'after_id': scenes[-1]['id'],
        'bbox': [-78.705, -1.705, -78.625, -1.625],
        'threshold_db': 3.0,
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['is_demo']
    assert body['statistics']['valid_pixels'] > 0
    assert body['statistics']['changed_pixels'] > 0
    assert body['overlay_png'].startswith('data:image/png;base64,')

def test_reject_same_scene():
    scene = client.get('/api/scenes').json()[0]
    response = client.post('/api/analyze', json={
        'before_id': scene['id'], 'after_id': scene['id'],
        'bbox': [-78.705, -1.705, -78.625, -1.625],
    })
    assert response.status_code == 422
