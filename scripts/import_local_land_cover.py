"""Register the supplied Ecuador LC_Type1 GeoTIFFs through the normal API.

The original files in ``Ecu Cp`` are never altered.  The API copies validated
files to its private runtime store and writes only their catalog metadata to
PostGIS.  Run from the repository root with the project's virtual environment.
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = ROOT / 'Ecu Cp'
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.geospatial.landcover import MCD12Q1_LC_TYPE1_PROFILE  # noqa: E402
from backend.main import app  # noqa: E402


def upload(client: TestClient, path: Path, year: int) -> dict:
    metadata = {
        'product_name': 'MODIS MCD12Q1.061',
        'analysis_profile': MCD12Q1_LC_TYPE1_PROFILE,
        'classification_system': 'IGBP Land Cover Type 1',
        'local_collection': 'Ecu Cp',
        'map_title': f'Mapa de cobertura del suelo — Ecuador {year}',
        'source_note': 'Ráster local proporcionado en la colección Ecu Cp; clases MCD12Q1.061 LC_Type1 (IGBP).',
    }
    session = client.post('/api/geospatial/uploads/sessions', json={
        'file_name': path.name,
        'total_bytes': path.stat().st_size,
        'asset_kind': 'raster',
        'captured_at': f'{year}-01-01',
        'declared_metadata': metadata,
    })
    session.raise_for_status()
    payload = session.json()
    with path.open('rb') as source:
        for index in range(payload['expected_chunks']):
            block = source.read(payload['chunk_bytes'])
            response = client.put(
                payload['put_chunk_url_template'].replace('{chunk_index}', str(index)),
                content=block,
                headers={'Content-Type': 'application/octet-stream'},
            )
            response.raise_for_status()
    completed = client.post(payload['complete_url'])
    completed.raise_for_status()
    return completed.json()


def main() -> None:
    client = TestClient(app)
    status = client.get('/api/geospatial/status')
    status.raise_for_status()
    if not status.json().get('ready'):
        raise SystemExit('El catálogo PostGIS no está disponible.')
    results = []
    for year in range(2021, 2026):
        path = SOURCE_DIRECTORY / f'Ecu Cp {year}.tif'
        if not path.is_file():
            raise SystemExit(f'Falta el archivo local esperado: {path.name}')
        results.append({'year': year, **upload(client, path, year)})
    print({'registered': results})


if __name__ == '__main__':
    main()
