"""Load the reviewed provincial GeoJSON into PostGIS without touching rasters."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.geospatial.catalog import PostgresCatalog
from backend.geospatial.settings import GeoportalSettings


SOURCE = PROJECT_ROOT / 'backend' / 'geospatial' / 'data' / 'ecuador_provinces.geojson'


def main() -> None:
    collection = json.loads(SOURCE.read_text(encoding='utf-8'))
    catalog = PostgresCatalog(GeoportalSettings.from_environment())
    catalog.upsert_administrative_areas(collection)
    print(f"provinces={len(collection['features'])}")


if __name__ == '__main__':
    main()
