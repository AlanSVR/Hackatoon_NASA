"""Configuración explícita y sin secretos del catálogo geoespacial."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote


PROJECT_ROOT = Path(__file__).resolve().parents[2]

try:
    from dotenv import load_dotenv
except ImportError:  # La API antigua debe iniciar incluso antes de reinstalar dependencias.
    load_dotenv = None


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _local_postgres_url() -> str | None:
    """Use the already configured local pgpass without copying a secret.

    The administrator login is used only to establish the local connection and
    PostgreSQL applies ``geoportal_app`` as the startup role before the API can
    execute queries.  This is a Windows-local fallback for the starter project;
    deployments should set GEOPORTAL_DATABASE_URL to their managed app account.
    """
    if os.name != 'nt' or not _bool(os.environ.get('GEOPORTAL_USE_LOCAL_PGPASS'), default=True):
        return None
    options = quote('-c role=geoportal_app', safe='')
    return f'postgresql://postgres@localhost:5432/geoportal_db?options={options}'


@dataclass(frozen=True)
class GeoportalSettings:
    """Valores de ejecución.

    DATABASE_URL y GEOPORTAL_UPLOAD_TOKEN se leen únicamente desde el entorno
    del proceso. No se guardan en el repositorio ni se devuelven por la API.
    """

    database_url: str | None
    storage_dir: Path
    max_upload_bytes: int
    chunk_bytes: int
    upload_token: str | None
    allow_local_unsafe_uploads: bool

    @classmethod
    def from_environment(cls) -> 'GeoportalSettings':
        if load_dotenv:
            load_dotenv(PROJECT_ROOT / '.env', override=False)
        storage_value = os.environ.get('GEOPORTAL_STORAGE_DIR')
        storage_dir = Path(storage_value).expanduser() if storage_value else PROJECT_ROOT / 'runtime' / 'geoportal'
        return cls(
            database_url=os.environ.get('GEOPORTAL_DATABASE_URL') or _local_postgres_url(),
            storage_dir=storage_dir.resolve(),
            max_upload_bytes=int(os.environ.get('GEOPORTAL_MAX_UPLOAD_BYTES', str(500 * 1024 * 1024))),
            chunk_bytes=int(os.environ.get('GEOPORTAL_CHUNK_BYTES', str(8 * 1024 * 1024))),
            upload_token=os.environ.get('GEOPORTAL_UPLOAD_TOKEN') or None,
            allow_local_unsafe_uploads=_bool(os.environ.get('GEOPORTAL_ALLOW_LOCAL_UPLOADS')),
        )

    @property
    def database_configured(self) -> bool:
        return bool(self.database_url)
