"""Repositorio PostgreSQL/PostGIS para el catálogo, sesiones y caché.

El código importa psycopg de forma diferida: la API existente continúa
arrancando si aún no se instaló la dependencia o configuró la base. Los
endpoints del geoportal entonces indican el motivo en vez de simular guardado.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator
from uuid import UUID

from backend.geospatial.settings import GeoportalSettings


class CatalogUnavailable(RuntimeError):
    """La persistencia no está lista para aceptar o consultar activos."""


class PostgresCatalog:
    def __init__(self, settings: GeoportalSettings):
        self.settings = settings

    @contextmanager
    def connection(self) -> Iterator[Any]:
        if not self.settings.database_url:
            raise CatalogUnavailable('GEOPORTAL_DATABASE_URL no está configurada.')
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise CatalogUnavailable('Falta psycopg. Instala requirements.txt antes de activar el catálogo.') from exc
        try:
            with psycopg.connect(self.settings.database_url, row_factory=dict_row, connect_timeout=5) as connection:
                # Supabase keeps PostGIS in ``extensions``.  Local PostgreSQL
                # installations commonly use ``public``; retaining both keeps
                # the same queries portable without exposing extension objects.
                connection.execute('SET search_path TO geoportal, public, extensions')
                yield connection
        except Exception as exc:  # psycopg expone varias clases de error según el servidor.
            raise CatalogUnavailable('No se pudo conectar al catálogo PostgreSQL/PostGIS.') from exc

    def status(self) -> dict[str, Any]:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT current_database() AS database_name, postgis_full_version() AS postgis_version"
            ).fetchone()
            count = connection.execute("SELECT count(*) AS value FROM geoportal.raster_assets").fetchone()
        return {
            'ready': True,
            'database_name': row['database_name'],
            'postgis_version': row['postgis_version'],
            'asset_count': int(count['value']),
        }

    def upsert_administrative_areas(self, collection: dict[str, Any]) -> None:
        """Persist reviewed administrative polygons used for zonal selection."""
        metadata = collection.get('metadata') or {}
        source_title = str(metadata.get('source_title') or 'Fuente no declarada')
        source_url = str(metadata.get('source_url') or '')
        if not source_url:
            raise ValueError('La colección de áreas no declara la fuente.')
        rows = []
        for feature in collection.get('features') or []:
            properties = feature.get('properties') or {}
            geometry = feature.get('geometry')
            if not geometry:
                continue
            rows.append({
                'area_id': str(properties['area_id']),
                'level': str(properties.get('level') or 'province'),
                'name_es': str(properties['name_es']),
                'name_en': str(properties.get('name_en') or properties['name_es']),
                'source_year': str(properties.get('source_year') or ''),
                'source_title': source_title,
                'source_url': source_url,
                'geometry': json.dumps(geometry),
            })
        if not rows:
            raise ValueError('La colección no contiene áreas importables.')
        with self.connection() as connection:
            connection.cursor().executemany(
                """
                INSERT INTO geoportal.administrative_areas
                    (area_id, level, name_es, name_en, source_year, source_title, source_url, boundary)
                VALUES
                    (%(area_id)s, %(level)s, %(name_es)s, %(name_en)s, %(source_year)s,
                     %(source_title)s, %(source_url)s,
                     ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%(geometry)s), 4326)))
                ON CONFLICT (area_id) DO UPDATE SET
                    level = EXCLUDED.level, name_es = EXCLUDED.name_es, name_en = EXCLUDED.name_en,
                    source_year = EXCLUDED.source_year, source_title = EXCLUDED.source_title,
                    source_url = EXCLUDED.source_url, boundary = EXCLUDED.boundary, updated_at = now()
                """,
                rows,
            )

    def list_administrative_areas(self, level: str = 'province') -> dict[str, Any]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT area_id, level, name_es, name_en, source_year, source_title, source_url,
                       ST_AsGeoJSON(boundary)::jsonb AS geometry
                FROM geoportal.administrative_areas
                WHERE level = %s
                ORDER BY name_es
                """,
                (level,),
            ).fetchall()
        features = [
            {
                'type': 'Feature', 'id': row['area_id'],
                'properties': {
                    'area_id': row['area_id'], 'level': row['level'],
                    'name_es': row['name_es'], 'name_en': row['name_en'],
                    'source_year': row['source_year'],
                },
                'geometry': row['geometry'],
            }
            for row in rows
        ]
        source = dict(rows[0]) if rows else {}
        return {
            'type': 'FeatureCollection', 'features': features,
            'metadata': {
                'source_title': source.get('source_title'), 'source_url': source.get('source_url'),
                'count': len(features), 'crs': 'EPSG:4326',
            },
        }

    def administrative_geometries(self, area_ids: list[str], level: str = 'province') -> list[dict[str, Any]]:
        if not area_ids:
            return []
        unique_ids = list(dict.fromkeys(area_ids))
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT area_id, name_es, name_en, ST_AsGeoJSON(boundary)::jsonb AS geometry
                FROM geoportal.administrative_areas
                WHERE level = %s AND area_id = ANY(%s)
                ORDER BY name_es
                """,
                (level, unique_ids),
            ).fetchall()
        if len(rows) != len(unique_ids):
            raise ValueError('Una o más provincias seleccionadas no existen en el catálogo.')
        return [dict(row) for row in rows]

    def list_assets(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT asset_id::text, original_name, asset_kind, sha256, byte_size, storage_key,
                       crs_text, epsg, width, height, band_count, nodata, resolution_x,
                       resolution_y, captured_at, declared_metadata, technical_metadata,
                       created_at, source_asset_id::text
                FROM geoportal.raster_assets
                WHERE ingestion_status = 'ready'
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_asset(self, asset_id: str | UUID) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT asset_id::text, original_name, asset_kind, sha256, byte_size,
                       storage_key, crs_text, epsg, width, height, band_count, nodata,
                       resolution_x, resolution_y, captured_at, declared_metadata,
                       technical_metadata, created_at, source_asset_id::text,
                       ST_AsGeoJSON(extent_4326)::jsonb AS extent
                FROM geoportal.raster_assets WHERE asset_id = %s
                """,
                (str(asset_id),),
            ).fetchone()
        return dict(row) if row else None

    def update_declared_metadata(self, asset_id: str | UUID, metadata: dict[str, Any]) -> dict[str, Any] | None:
        """Merge human-authored catalog notes without touching technical facts."""
        with self.connection() as connection:
            row = connection.execute(
                """
                UPDATE geoportal.raster_assets
                SET declared_metadata = COALESCE(declared_metadata, '{}'::jsonb) || %s::jsonb,
                    last_seen_at = now()
                WHERE asset_id = %s
                RETURNING asset_id::text, original_name, declared_metadata
                """,
                (json.dumps(metadata), str(asset_id)),
            ).fetchone()
        return dict(row) if row else None

    def list_bands(self, asset_id: str | UUID) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT band_index, dtype, scale, band_offset, description,
                       color_interpretation, semantic_role
                FROM geoportal.raster_bands WHERE asset_id = %s ORDER BY band_index
                """,
                (str(asset_id),),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_persistent_cache(self, cache_key: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                """
                SELECT cache_key, namespace, payload, expires_at, created_at, accessed_at
                FROM geoportal.persistent_cache
                WHERE cache_key = %s AND (expires_at IS NULL OR expires_at > now())
                """,
                (cache_key,),
            ).fetchone()
            if row:
                connection.execute(
                    "UPDATE geoportal.persistent_cache SET accessed_at = now() WHERE cache_key = %s",
                    (cache_key,),
                )
        return dict(row) if row else None

    def put_persistent_cache(self, cache_key: str, namespace: str, payload: dict[str, Any]) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO geoportal.persistent_cache (cache_key, namespace, payload)
                VALUES (%s, %s, %s::jsonb)
                ON CONFLICT (cache_key) DO UPDATE
                SET namespace = EXCLUDED.namespace, payload = EXCLUDED.payload, accessed_at = now()
                """,
                (cache_key, namespace, json.dumps(payload)),
            )

    def record_processing_job(self, values: dict[str, Any]) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO geoportal.processing_jobs
                    (job_id, job_type, input_fingerprint, parameters, state, progress,
                     cache_key, result_summary, completed_at)
                VALUES (%(job_id)s, %(job_type)s, %(input_fingerprint)s,
                        %(parameters)s::jsonb, 'completed', 100, %(cache_key)s,
                        %(result_summary)s::jsonb, now())
                ON CONFLICT (job_id) DO NOTHING
                """,
                {
                    **values,
                    'parameters': json.dumps(values['parameters']),
                    'result_summary': json.dumps(values['result_summary']),
                },
            )

    def find_by_hash(self, sha256: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT asset_id::text, original_name, asset_kind, storage_key FROM geoportal.raster_assets WHERE sha256 = %s",
                (sha256,),
            ).fetchone()
        return dict(row) if row else None

    def create_upload_session(self, values: dict[str, Any]) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO geoportal.upload_sessions
                    (session_id, original_name, expected_bytes, expected_chunks, chunk_bytes,
                     requested_sha256, file_kind, declared_metadata, asset_group_id, source_asset_id)
                VALUES (%(session_id)s, %(original_name)s, %(expected_bytes)s, %(expected_chunks)s,
                        %(chunk_bytes)s, %(requested_sha256)s, %(file_kind)s,
                        %(declared_metadata)s::jsonb, %(asset_group_id)s, %(source_asset_id)s)
                """,
                {**values, 'declared_metadata': json.dumps(values['declared_metadata'])},
            )

    def create_asset_group(self, group_id: str, label: str) -> None:
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO geoportal.asset_groups (asset_group_id, label) VALUES (%s, %s)",
                (group_id, label),
            )

    def get_upload_session(self, session_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM geoportal.upload_sessions WHERE session_id = %s", (session_id,)
            ).fetchone()
        return dict(row) if row else None

    def mark_chunk_received(self, session_id: str, chunk_index: int, byte_size: int, digest: str) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                UPDATE geoportal.upload_sessions
                SET received_chunks = jsonb_set(
                        COALESCE(received_chunks, '{}'::jsonb),
                        ARRAY[%s::text], jsonb_build_object('bytes', %s::bigint, 'sha256', %s::text), true
                    ),
                    received_bytes = (
                        SELECT COALESCE(sum((item.value ->> 'bytes')::bigint), 0)
                        FROM jsonb_each(
                            jsonb_set(COALESCE(received_chunks, '{}'::jsonb),
                                ARRAY[%s::text], jsonb_build_object('bytes', %s::bigint, 'sha256', %s::text), true)
                        ) AS item
                    ),
                    updated_at = now()
                WHERE session_id = %s AND state = 'active'
                """,
                (str(chunk_index), byte_size, digest, str(chunk_index), byte_size, digest, session_id),
            )

    def complete_upload_session(self, session_id: str, asset_id: str, deduplicated: bool) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                UPDATE geoportal.upload_sessions
                SET state = 'completed', asset_id = %s, deduplicated = %s, completed_at = now(), updated_at = now()
                WHERE session_id = %s
                """,
                (asset_id, deduplicated, session_id),
            )

    def fail_upload_session(self, session_id: str, error: str) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                UPDATE geoportal.upload_sessions
                SET state = 'failed', error_message = %s, updated_at = now()
                WHERE session_id = %s AND state <> 'completed'
                """,
                (error[:800], session_id),
            )

    def register_asset(self, values: dict[str, Any]) -> str:
        """Inserta un activo validado; la exclusión SHA-256 evita duplicados."""
        with self.connection() as connection:
            row = connection.execute(
                """
                INSERT INTO geoportal.raster_assets
                    (asset_id, asset_group_id, source_asset_id, original_name, storage_key,
                     sha256, byte_size, asset_kind, mime_type, crs_text, epsg, width, height,
                     band_count, nodata, resolution_x, resolution_y, captured_at,
                     declared_metadata, technical_metadata, extent_4326, ingestion_status)
                VALUES
                    (%(asset_id)s, %(asset_group_id)s, %(source_asset_id)s, %(original_name)s,
                     %(storage_key)s, %(sha256)s, %(byte_size)s, %(asset_kind)s, %(mime_type)s,
                     %(crs_text)s, %(epsg)s, %(width)s, %(height)s, %(band_count)s, %(nodata)s,
                     %(resolution_x)s, %(resolution_y)s, %(captured_at)s,
                     %(declared_metadata)s::jsonb, %(technical_metadata)s::jsonb,
                     CASE WHEN %(west)s IS NULL THEN NULL
                          ELSE ST_SetSRID(ST_MakeEnvelope(%(west)s, %(south)s, %(east)s, %(north)s), 4326)
                     END, 'ready')
                ON CONFLICT (sha256) DO UPDATE SET last_seen_at = now()
                RETURNING asset_id::text
                """,
                {
                    **values,
                    'declared_metadata': json.dumps(values['declared_metadata']),
                    'technical_metadata': json.dumps(values['technical_metadata']),
                },
            ).fetchone()
        return str(row['asset_id'])

    def insert_bands(self, asset_id: str, bands: list[dict[str, Any]]) -> None:
        if not bands:
            return
        with self.connection() as connection:
            connection.cursor().executemany(
                """
                INSERT INTO geoportal.raster_bands
                    (asset_id, band_index, dtype, scale, band_offset, description, color_interpretation)
                VALUES (%(asset_id)s, %(band_index)s, %(dtype)s, %(scale)s, %(offset)s,
                        %(description)s, %(color_interpretation)s)
                ON CONFLICT (asset_id, band_index) DO NOTHING
                """,
                [{**band, 'asset_id': asset_id} for band in bands],
            )

    def create_relation(self, parent_id: str, child_id: str, relation_type: str) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO geoportal.asset_relations (parent_asset_id, child_asset_id, relation_type)
                VALUES (%s, %s, %s) ON CONFLICT DO NOTHING
                """,
                (parent_id, child_id, relation_type),
            )

    def group_source_assets(self, group_id: str) -> dict[str, str]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT original_name, asset_id::text FROM geoportal.raster_assets WHERE asset_group_id = %s AND ingestion_status = 'ready'", (group_id,)
            ).fetchall()
        return {str(row['original_name']): str(row['asset_id']) for row in rows}
