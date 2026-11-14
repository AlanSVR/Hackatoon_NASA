"""Genera GeoTIFF SINTÉTICOS para probar la API (NO son imágenes NISAR)."""
from pathlib import Path
import json

import numpy as np
import rasterio
from rasterio.transform import from_bounds

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'scenes'
OUT.mkdir(parents=True, exist_ok=True)

N = 512
rng = np.random.default_rng(2026)
y, x = np.mgrid[0:N, 0:N]
terrain = -12.0 + 2.5 * np.sin(x / 55) + 1.5 * np.cos(y / 70)
terrain += 1.2 * np.sin((x + y) / 19) + rng.normal(0, 0.55, size=(N, N))
rect1 = (x > 125) & (x < 275) & (y > 145) & (y < 320)
rect2 = (x > 310) & (x < 445) & (y > 200) & (y < 380)

layers = [terrain.copy(), terrain.copy(), terrain.copy()]
layers[1][rect1] -= 4.8
layers[1][rect2] += 3.5
layers[2][rect1] -= 2.3
layers[2][rect2] += 5.2
# Cambio temporal adicional simulado sobre una zona elíptica
ellipse = ((x - 320) / 72) ** 2 + ((y - 90) / 45) ** 2 < 1
layers[2][ellipse] -= 4.2

scene_info = [
    ('demo_2026_01_08', '2026-01-08'),
    ('demo_2026_03_02', '2026-03-02'),
    ('demo_2026_06_10', '2026-06-10'),
]
manifest = {'note': 'TODAS las escenas demo son SINTÉTICAS; no son productos satelitales reales.',
            'scenes': []}

for (scene_id, date), db in zip(scene_info, layers):
    # GeoTIFF en potencia lineal positiva: 10^(dB/10)
    power = np.power(10.0, db / 10.0).astype('float32')
    name = f'{scene_id}.tif'
    with rasterio.open(
        OUT / name, 'w', driver='GTiff', width=N, height=N,
        count=1, dtype='float32', crs='EPSG:4326',
        transform=from_bounds(-78.74, -1.74, -78.59, -1.59, N, N),
        compress='deflate', tiled=True,
        nodata=-9999.0,
    ) as dst:
        dst.write(power, 1)
    manifest['scenes'].append({
        'id': scene_id, 'file': name, 'date': date,
        'source': 'DEMO_SINTETICA', 'channel': 'HHHH',
        'units': 'linear_power', 'is_demo': True,
        'description': 'Datos fabricados solo para validar la aplicación. No representan NISAR.',
    })

(ROOT / 'data' / 'manifest.json').write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
print(f'Listo: {len(scene_info)} escenas de prueba en {OUT}')
