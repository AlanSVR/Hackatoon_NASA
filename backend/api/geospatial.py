"""API local para cargar y catalogar rásteres validados de forma persistente.

No acepta rutas del equipo cliente ni publica los archivos originales. El
contenido ingresa por sesiones de bloques, se valida con Rasterio y queda en un
almacenamiento privado cuyos metadatos se persisten en PostGIS.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import shutil
import uuid
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Any, Literal

import numpy as np
import rasterio
from fastapi import APIRouter, HTTPException, Request, Response
from PIL import Image
from pydantic import BaseModel, Field, field_validator
from rasterio.warp import transform_bounds

from backend.geospatial.catalog import CatalogUnavailable, PostgresCatalog
from backend.geospatial.processing import render_normalized_difference, render_rgb
from backend.geospatial.settings import GeoportalSettings


router = APIRouter(prefix='/api/geospatial', tags=['Geoportal PostGIS'])
settings = GeoportalSettings.from_environment()
catalog = PostgresCatalog(settings)
ALLOWED_EXTENSIONS = {
    'raster': {'.tif', '.tiff'},
    'virtual': {'.vrt'},
    'auxiliary': {'.aux.xml'},
}
MAX_PREVIEW_EDGE = 1400


class UploadSessionRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=220)
    total_bytes: int = Field(gt=0)
    sha256: str | None = Field(default=None, max_length=64)
    asset_kind: Literal['raster', 'virtual', 'auxiliary']
    declared_metadata: dict[str, Any] = Field(default_factory=dict)
    captured_at: date | None = None
    asset_group_id: uuid.UUID | None = None
    source_asset_id: uuid.UUID | None = None

    @field_validator('file_name')
    @classmethod
    def safe_file_name(cls, value: str) -> str:
        candidate = Path(value)
        if candidate.name != value or value in {'.', '..'}:
            raise ValueError('El nombre debe ser un archivo simple, sin ruta.')
        return value

    @field_validator('sha256')
    @classmethod
    def valid_optional_hash(cls, value: str | None) -> str | None:
        if value is not None and (len(value) != 64 or any(char not in '0123456789abcdefABCDEF' for char in value)):
            raise ValueError('El SHA-256 debe tener 64 caracteres hexadecimales.')
        return value.lower() if value else None


class AssetGroupRequest(BaseModel):
    label: str = Field(min_length=1, max_length=160)


class RgbRenderRequest(BaseModel):
    red_band: int = Field(ge=1)
    green_band: int = Field(ge=1)
    blue_band: int = Field(ge=1)


class NormalizedDifferenceRequest(BaseModel):
    numerator_band: int = Field(ge=1)
    denominator_band: int = Field(ge=1)
    manual_semantics_confirmed: bool = False


def _extension(file_name: str) -> str:
    lowered = file_name.lower()
    return '.aux.xml' if lowered.endswith('.aux.xml') else Path(lowered).suffix


def _assert_allowed_name(file_name: str, asset_kind: str) -> None:
    if _extension(file_name) not in ALLOWED_EXTENSIONS[asset_kind]:
        allowed = ', '.join(sorted(ALLOWED_EXTENSIONS[asset_kind]))
        raise HTTPException(422, f'Formato no permitido para {asset_kind}. Se esperaba: {allowed}.')


def _catalog_or_error() -> PostgresCatalog:
    if not settings.database_configured:
        raise HTTPException(503, 'Catálogo no configurado: falta GEOPORTAL_DATABASE_URL.')
    return catalog


def _ensure_upload_authorized(request: Request) -> None:
    """No hay identidad de usuario todavía: se exige token o modo local explícito."""
    if settings.upload_token:
        supplied = request.headers.get('X-Geoportal-Token', '')
        if not hmac.compare_digest(supplied, settings.upload_token):
            raise HTTPException(401, 'Token de carga inválido o ausente.')
        return
    client_host = request.client.host if request.client else ''
    if settings.allow_local_unsafe_uploads and client_host in {'127.0.0.1', '::1', 'testclient'}:
        return
    raise HTTPException(
        503,
        'La carga está desactivada. Configura GEOPORTAL_UPLOAD_TOKEN o habilita explícitamente GEOPORTAL_ALLOW_LOCAL_UPLOADS solo para localhost.',
    )


def _session_directory(session_id: str) -> Path:
    directory = settings.storage_dir / 'incoming' / session_id
    resolved_root = settings.storage_dir.resolve()
    resolved = directory.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise HTTPException(400, 'Identificador de sesión inválido.') from exc
    return resolved


def _storage_path(storage_key: str) -> Path:
    root = settings.storage_dir.resolve()
    candidate = (root / storage_key).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(500, 'La ruta interna del activo no es segura.') from exc
    return candidate


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _hash_and_join(session: dict[str, Any], destination: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    session_dir = _session_directory(str(session['session_id']))
    with destination.open('xb') as output:
        for index in range(int(session['expected_chunks'])):
            part = session_dir / f'{index:08d}.part'
            if not part.is_file():
                raise HTTPException(422, f'Falta el bloque {index + 1} de la carga.')
            with part.open('rb') as source:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    total += len(block)
                    digest.update(block)
                    output.write(block)
    if total != int(session['expected_bytes']):
        raise HTTPException(422, 'El tamaño final no coincide con el tamaño declarado.')
    return digest.hexdigest(), total


def _json_safe_tags(tags: dict[str, str]) -> dict[str, str]:
    # Evita arrastrar metadatos excesivos o binarios al catálogo.
    return {str(key): str(value)[:2000] for key, value in tags.items() if len(str(key)) <= 120}


def _inspect_raster(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], tuple[float, float, float, float]]:
    try:
        with rasterio.open(path) as dataset:
            if dataset.driver != 'GTiff':
                raise ValueError(f'El controlador declarado es {dataset.driver}, no GeoTIFF.')
            if dataset.crs is None:
                raise ValueError('El GeoTIFF no declara CRS.')
            if dataset.count < 1:
                raise ValueError('El GeoTIFF no contiene bandas.')
            try:
                west, south, east, north = transform_bounds(dataset.crs, 'EPSG:4326', *dataset.bounds, densify_pts=21)
            except Exception as exc:
                raise ValueError('No se pudo transformar la extensión a EPSG:4326.') from exc
            if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= 90 and -90 <= north <= 90):
                raise ValueError('La extensión transformada está fuera de EPSG:4326.')
            color_interpretations: list[str | None]
            try:
                color_interpretations = [item.name for item in dataset.colorinterp]
            except Exception:
                color_interpretations = [None] * dataset.count
            bands = [
                {
                    'band_index': index + 1,
                    'dtype': dataset.dtypes[index],
                    'scale': float(dataset.scales[index]) if dataset.scales[index] is not None else None,
                    'offset': float(dataset.offsets[index]) if dataset.offsets[index] is not None else None,
                    'description': dataset.descriptions[index],
                    'color_interpretation': color_interpretations[index],
                }
                for index in range(dataset.count)
            ]
            technical = {
                'driver': dataset.driver,
                'source_bounds': [dataset.bounds.left, dataset.bounds.bottom, dataset.bounds.right, dataset.bounds.top],
                'source_transform': list(dataset.transform)[:6],
                'source_resolution': [abs(dataset.transform.a), abs(dataset.transform.e)],
                'source_crs': dataset.crs.to_string(),
                'metadata_tags': _json_safe_tags(dataset.tags()),
                'band_semantics': 'NO VERIFICADO: se conservan descripciones y colorinterp del archivo; no se infiere sensor ni bandas espectrales.',
            }
            values = {
                'crs_text': dataset.crs.to_string(),
                'epsg': dataset.crs.to_epsg(),
                'width': dataset.width,
                'height': dataset.height,
                'band_count': dataset.count,
                'nodata': float(dataset.nodata) if dataset.nodata is not None else None,
                'resolution_x': abs(float(dataset.transform.a)),
                'resolution_y': abs(float(dataset.transform.e)),
                'technical_metadata': technical,
            }
    except (rasterio.errors.RasterioError, ValueError) as exc:
        raise HTTPException(422, f'El archivo no es un GeoTIFF georreferenciado válido: {exc}') from exc
    return values, bands, (west, south, east, north)


def _assert_safe_xml(path: Path) -> ET.Element:
    raw = path.read_bytes()
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise HTTPException(422, 'XML con DTD o entidades no está permitido.')
    try:
        return ET.fromstring(raw)
    except ET.ParseError as exc:
        raise HTTPException(422, 'El XML no es válido.') from exc


def _validate_virtual_file(path: Path, session: dict[str, Any], repository: PostgresCatalog) -> dict[str, str]:
    root = _assert_safe_xml(path)
    if root.tag.split('}')[-1] != 'VRTDataset':
        raise HTTPException(422, 'El XML no describe un VRTDataset.')
    sources = [node.text.strip() for node in root.iter() if node.tag.split('}')[-1] == 'SourceFilename' and node.text]
    if not sources:
        raise HTTPException(422, 'El VRT no declara fuentes controladas.')
    group_id = session.get('asset_group_id')
    if not group_id:
        raise HTTPException(422, 'Un VRT requiere asset_group_id y dependencias ya cargadas en ese grupo.')
    allowed = repository.group_source_assets(str(group_id))
    for source in sources:
        candidate = Path(source)
        if candidate.is_absolute() or candidate.name != source or source not in allowed:
            raise HTTPException(422, 'El VRT referencia una dependencia externa o no registrada en su grupo.')
    return {source: allowed[source] for source in sources}


def _validate_auxiliary_file(path: Path, session: dict[str, Any], repository: PostgresCatalog) -> None:
    _assert_safe_xml(path)
    source_asset_id = session.get('source_asset_id')
    if not source_asset_id or not repository.get_asset(str(source_asset_id)):
        raise HTTPException(422, 'Un .aux.xml requiere source_asset_id de un ráster ya catalogado.')


def _make_preview(source: Path, target: Path, band_index: int) -> None:
    with rasterio.open(source) as dataset:
        if band_index < 1 or band_index > dataset.count:
            raise HTTPException(422, 'Índice de banda fuera de rango.')
        scale = min(1.0, MAX_PREVIEW_EDGE / max(dataset.width, dataset.height))
        width = max(1, round(dataset.width * scale))
        height = max(1, round(dataset.height * scale))
        data = dataset.read(band_index, out_shape=(height, width), masked=True)
    valid = np.asarray(data.compressed(), dtype=np.float64)
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    if valid.size:
        low, high = np.nanpercentile(valid, [2, 98])
        if not np.isfinite(low) or not np.isfinite(high) or high <= low:
            high = low + 1
        filled = np.asarray(data.astype(np.float64).filled(np.nan), dtype=np.float64)
        normalized = np.clip((filled - low) / (high - low), 0, 1)
        values = (np.nan_to_num(normalized, nan=0.0) * 255).astype(np.uint8)
        mask = ~np.ma.getmaskarray(data) & np.isfinite(filled)
        rgba[..., 0][mask] = values[mask]
        rgba[..., 1][mask] = values[mask]
        rgba[..., 2][mask] = values[mask]
        rgba[mask, 3] = 255
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, mode='RGBA').save(target, format='PNG', optimize=True)


def _analysis_cache_key(asset_hashes: list[str], operation: str, parameters: dict[str, Any]) -> str:
    payload = json.dumps({'version': 'geoportal-analysis-v1', 'assets': asset_hashes, 'operation': operation, 'parameters': parameters}, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def _cached_render(asset: dict[str, Any], operation: str, parameters: dict[str, Any], render) -> dict[str, Any]:
    """Persist a rendered result on disk plus a PostGIS cache record."""
    repository = _catalog_or_error()
    cache_key = _analysis_cache_key([str(asset['sha256'])], operation, parameters)
    cached = repository.get_persistent_cache(cache_key)
    storage_key = str(Path('derived-cache') / cache_key[:2] / f'{cache_key}.png')
    target = _storage_path(storage_key)
    if cached and target.is_file():
        return {**dict(cached['payload']), 'cache_key': cache_key, 'cached': True}
    try:
        summary = render(target)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    payload = {
        'asset_id': str(asset['asset_id']), 'operation': operation, 'parameters': parameters,
        'summary': summary, 'image_url': f'/api/geospatial/assets/{asset["asset_id"]}/derived/{cache_key}',
    }
    repository.put_persistent_cache(cache_key, f'geospatial:{operation}', payload)
    repository.record_processing_job({
        'job_id': str(uuid.uuid4()), 'job_type': operation, 'input_fingerprint': str(asset['sha256']),
        'parameters': parameters, 'cache_key': cache_key, 'result_summary': summary,
    })
    return {**payload, 'cache_key': cache_key, 'cached': False}


def _asset_or_error(asset_id: uuid.UUID) -> dict[str, Any]:
    try:
        asset = _catalog_or_error().get_asset(asset_id)
    except CatalogUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    if not asset:
        raise HTTPException(404, 'Activo no encontrado.')
    if asset['asset_kind'] not in {'raster', 'derived', 'mask'}:
        raise HTTPException(422, 'El activo no es un GeoTIFF procesable.')
    if not _storage_path(asset['storage_key']).is_file():
        raise HTTPException(410, 'El archivo privado ya no está disponible.')
    return asset


@router.get('/status')
def geospatial_status() -> dict[str, Any]:
    response: dict[str, Any] = {
        'database_configured': settings.database_configured,
        'storage_path_configured': bool(settings.storage_dir),
        'max_upload_bytes': settings.max_upload_bytes,
        'chunk_bytes': settings.chunk_bytes,
        'upload_protection': 'token' if settings.upload_token else ('explicit-local-only' if settings.allow_local_unsafe_uploads else 'disabled'),
    }
    if not settings.database_configured:
        response.update({'ready': False, 'reason': 'Falta GEOPORTAL_DATABASE_URL.'})
        return response
    try:
        response.update(catalog.status())
    except CatalogUnavailable:
        response.update({'ready': False, 'reason': 'PostgreSQL/PostGIS no verificable con la configuración actual.'})
    return response


@router.get('/assets')
def list_assets(limit: int = 100) -> dict[str, Any]:
    if not 1 <= limit <= 250:
        raise HTTPException(422, 'limit debe estar entre 1 y 250.')
    try:
        return {'items': _catalog_or_error().list_assets(limit)}
    except CatalogUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get('/assets/{asset_id}')
def asset_detail(asset_id: uuid.UUID) -> dict[str, Any]:
    try:
        asset = _catalog_or_error().get_asset(asset_id)
    except CatalogUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    if not asset:
        raise HTTPException(404, 'Activo no encontrado.')
    return asset


@router.get('/assets/{asset_id}/analysis-capabilities')
def analysis_capabilities(asset_id: uuid.UUID) -> dict[str, Any]:
    asset = _asset_or_error(asset_id)
    bands = _catalog_or_error().list_bands(asset_id)
    descriptions = [str(item.get('description') or '').strip() for item in bands]
    # Only tags inside the raster are reported.  An empty or vague description is
    # never converted to a fictional sensor, RGB mapping, index, or Fmask class.
    has_declared_roles = any(value.lower() in {'red', 'green', 'blue', 'nir', 'swir'} for value in descriptions)
    return {
        'asset_id': str(asset_id), 'bands': bands,
        'generic_rgb': asset['band_count'] >= 3,
        'requested_265_requires_sensor_evidence': True,
        'normalized_difference_requires_manual_confirmation': not has_declared_roles,
        'band_semantics': 'verified-from-raster-tags' if has_declared_roles else 'unverified',
        'mask_classes': 'unverified',
        'note': 'Las bandas pueden seleccionarse para una visualización técnica. Los índices científicos requieren roles de banda verificados o confirmación manual explícita.',
    }


@router.post('/assets/{asset_id}/renders/rgb')
def create_rgb_render(asset_id: uuid.UUID, payload: RgbRenderRequest) -> dict[str, Any]:
    asset = _asset_or_error(asset_id)
    parameters = {'red_band': payload.red_band, 'green_band': payload.green_band, 'blue_band': payload.blue_band}
    result = _cached_render(
        asset, 'rgb-render', parameters,
        lambda target: render_rgb(_storage_path(asset['storage_key']), target, (payload.red_band, payload.green_band, payload.blue_band)),
    )
    result['semantic_status'] = 'unverified' if (payload.red_band, payload.green_band, payload.blue_band) == (2, 6, 5) else 'technical-display'
    result['note'] = 'La composición muestra las bandas seleccionadas con estiramiento visual. La combinación 2-6-5 no se etiqueta como falso color científico sin evidencia de sensor y bandas.' if result['semantic_status'] == 'unverified' else 'Visualización técnica de las bandas seleccionadas; no asigna significados espectrales no verificados.'
    return result


@router.post('/assets/{asset_id}/analyses/normalized-difference')
def create_normalized_difference(asset_id: uuid.UUID, payload: NormalizedDifferenceRequest) -> dict[str, Any]:
    asset = _asset_or_error(asset_id)
    if not payload.manual_semantics_confirmed:
        raise HTTPException(422, 'Confirma manualmente los roles de las bandas antes de calcular un índice; el archivo no declara semántica verificable.')
    parameters = {'numerator_band': payload.numerator_band, 'denominator_band': payload.denominator_band, 'manual_semantics_confirmed': True}
    result = _cached_render(
        asset, 'normalized-difference', parameters,
        lambda target: render_normalized_difference(_storage_path(asset['storage_key']), target, payload.numerator_band, payload.denominator_band),
    )
    result['semantic_status'] = 'manual-unverified'
    result['note'] = 'Resultado de diferencia normalizada calculado con bandas confirmadas manualmente; no se etiqueta automáticamente como NDVI, NDMI o NDWI.'
    return result


@router.get('/assets/{asset_id}/derived/{cache_key}')
def derived_render(asset_id: uuid.UUID, cache_key: str) -> Response:
    if len(cache_key) != 64 or any(char not in '0123456789abcdef' for char in cache_key):
        raise HTTPException(404, 'Resultado derivado no encontrado.')
    repository = _catalog_or_error()
    cached = repository.get_persistent_cache(cache_key)
    if not cached or str(cached['payload'].get('asset_id')) != str(asset_id):
        raise HTTPException(404, 'Resultado derivado no encontrado.')
    target = _storage_path(str(Path('derived-cache') / cache_key[:2] / f'{cache_key}.png'))
    if not target.is_file():
        raise HTTPException(410, 'El archivo de resultado ya no está disponible.')
    return Response(target.read_bytes(), media_type='image/png', headers={
        'Cache-Control': 'private, max-age=86400', 'X-Content-Type-Options': 'nosniff',
    })


@router.get('/assets/{asset_id}/preview')
def asset_preview(asset_id: uuid.UUID, band: int = 1) -> Response:
    try:
        asset = _catalog_or_error().get_asset(asset_id)
    except CatalogUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    if not asset or asset['asset_kind'] not in {'raster', 'derived', 'mask'}:
        raise HTTPException(404, 'Vista previa no disponible para este activo.')
    source = _storage_path(asset['storage_key'])
    if not source.is_file():
        raise HTTPException(410, 'El archivo privado ya no está disponible.')
    cache_key = f"{asset['sha256']}-b{band}.png"
    target = _storage_path(str(Path('preview-cache') / cache_key))
    if not target.is_file():
        _make_preview(source, target, band)
    return Response(target.read_bytes(), media_type='image/png', headers={
        'Cache-Control': 'private, max-age=86400', 'X-Content-Type-Options': 'nosniff',
    })


@router.post('/asset-groups', status_code=201)
def create_asset_group(payload: AssetGroupRequest, request: Request) -> dict[str, Any]:
    _ensure_upload_authorized(request)
    group_id = str(uuid.uuid4())
    try:
        _catalog_or_error().create_asset_group(group_id, payload.label.strip())
    except CatalogUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    return {'asset_group_id': group_id, 'label': payload.label.strip()}


@router.post('/uploads/sessions', status_code=201)
def create_upload_session(payload: UploadSessionRequest, request: Request) -> dict[str, Any]:
    _ensure_upload_authorized(request)
    _assert_allowed_name(payload.file_name, payload.asset_kind)
    if payload.total_bytes > settings.max_upload_bytes:
        raise HTTPException(413, f'El archivo supera el máximo configurado de {settings.max_upload_bytes} bytes.')
    if payload.asset_kind == 'auxiliary' and not payload.source_asset_id:
        raise HTTPException(422, '.aux.xml requiere source_asset_id.')
    repository = _catalog_or_error()
    session_id = uuid.uuid4()
    expected_chunks = math.ceil(payload.total_bytes / settings.chunk_bytes)
    metadata = {**payload.declared_metadata}
    if payload.captured_at:
        metadata['captured_at'] = payload.captured_at.isoformat()
    values = {
        'session_id': str(session_id),
        'original_name': payload.file_name,
        'expected_bytes': payload.total_bytes,
        'expected_chunks': expected_chunks,
        'chunk_bytes': settings.chunk_bytes,
        'requested_sha256': payload.sha256,
        'file_kind': payload.asset_kind,
        'declared_metadata': metadata,
        'asset_group_id': str(payload.asset_group_id) if payload.asset_group_id else None,
        'source_asset_id': str(payload.source_asset_id) if payload.source_asset_id else None,
    }
    try:
        repository.create_upload_session(values)
    except CatalogUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    _session_directory(str(session_id)).mkdir(parents=True, exist_ok=False)
    return {
        'session_id': str(session_id), 'chunk_bytes': settings.chunk_bytes,
        'expected_chunks': expected_chunks,
        'put_chunk_url_template': f'/api/geospatial/uploads/sessions/{session_id}/chunks/{{chunk_index}}',
        'complete_url': f'/api/geospatial/uploads/sessions/{session_id}/complete',
    }


@router.put('/uploads/sessions/{session_id}/chunks/{chunk_index}')
async def upload_chunk(session_id: uuid.UUID, chunk_index: int, request: Request) -> dict[str, Any]:
    _ensure_upload_authorized(request)
    if chunk_index < 0:
        raise HTTPException(422, 'Índice de bloque inválido.')
    repository = _catalog_or_error()
    try:
        session = repository.get_upload_session(str(session_id))
    except CatalogUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    if not session or session['state'] != 'active':
        raise HTTPException(404, 'Sesión de carga activa no encontrada.')
    expected_chunks = int(session['expected_chunks'])
    if chunk_index >= expected_chunks:
        raise HTTPException(422, 'Índice de bloque fuera de rango.')
    expected_size = min(int(session['chunk_bytes']), int(session['expected_bytes']) - chunk_index * int(session['chunk_bytes']))
    session_dir = _session_directory(str(session_id))
    final_path = session_dir / f'{chunk_index:08d}.part'
    declared_digest = request.headers.get('X-Chunk-SHA256')
    if final_path.is_file():
        existing_digest = _hash_file(final_path)
        if declared_digest and hmac.compare_digest(existing_digest, declared_digest.lower()):
            return {'chunk_index': chunk_index, 'bytes': final_path.stat().st_size, 'already_received': True}
        raise HTTPException(409, 'El bloque ya existe con contenido diferente.')
    temporary = session_dir / f'{chunk_index:08d}.partial'
    digest = hashlib.sha256()
    written = 0
    try:
        with temporary.open('xb') as output:
            async for block in request.stream():
                written += len(block)
                if written > expected_size:
                    raise HTTPException(413, 'El bloque excede el tamaño esperado.')
                digest.update(block)
                output.write(block)
        if written != expected_size:
            raise HTTPException(422, f'El bloque debe contener exactamente {expected_size} bytes.')
        actual_digest = digest.hexdigest()
        if declared_digest and not hmac.compare_digest(actual_digest, declared_digest.lower()):
            raise HTTPException(422, 'El SHA-256 del bloque no coincide.')
        os.replace(temporary, final_path)
        repository.mark_chunk_received(str(session_id), chunk_index, written, actual_digest)
    except HTTPException:
        temporary.unlink(missing_ok=True)
        raise
    except (OSError, CatalogUnavailable) as exc:
        temporary.unlink(missing_ok=True)
        raise HTTPException(503, 'No se pudo conservar el bloque de carga.') from exc
    return {'chunk_index': chunk_index, 'bytes': written, 'sha256': actual_digest, 'already_received': False}


@router.post('/uploads/sessions/{session_id}/complete')
def complete_upload(session_id: uuid.UUID, request: Request) -> dict[str, Any]:
    _ensure_upload_authorized(request)
    repository = _catalog_or_error()
    try:
        session = repository.get_upload_session(str(session_id))
    except CatalogUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    if not session:
        raise HTTPException(404, 'Sesión de carga no encontrada.')
    if session['state'] == 'completed':
        return {'asset_id': str(session['asset_id']), 'deduplicated': bool(session['deduplicated']), 'state': 'completed'}
    if session['state'] != 'active':
        raise HTTPException(409, 'La sesión no se puede completar en su estado actual.')
    session_dir = _session_directory(str(session_id))
    assembled = session_dir / 'assembled.pending'
    missing_chunks = [index for index in range(int(session['expected_chunks'])) if not (session_dir / f'{index:08d}.part').is_file()]
    if missing_chunks:
        raise HTTPException(422, f'Faltan {len(missing_chunks)} bloques; la sesión sigue activa y puede reanudarse.')
    destination: Path | None = None
    moved_destination = False
    asset_registered = False
    try:
        digest, byte_size = _hash_and_join(session, assembled)
        if session.get('requested_sha256') and not hmac.compare_digest(digest, str(session['requested_sha256'])):
            raise HTTPException(422, 'El SHA-256 final no coincide con el declarado.')
        duplicate = repository.find_by_hash(digest)
        if duplicate:
            repository.complete_upload_session(str(session_id), duplicate['asset_id'], True)
            assembled.unlink(missing_ok=True)
            shutil.rmtree(session_dir, ignore_errors=True)
            return {'asset_id': duplicate['asset_id'], 'deduplicated': True, 'state': 'completed'}

        file_kind = str(session['file_kind'])
        extension = _extension(str(session['original_name']))
        bands: list[dict[str, Any]] = []
        extent: tuple[float, float, float, float] | None = None
        values: dict[str, Any] = {
            'crs_text': None, 'epsg': None, 'width': None, 'height': None, 'band_count': None,
            'nodata': None, 'resolution_x': None, 'resolution_y': None, 'technical_metadata': {},
        }
        vrt_sources: dict[str, str] = {}
        if file_kind == 'raster':
            values, bands, extent = _inspect_raster(assembled)
        elif file_kind == 'virtual':
            vrt_sources = _validate_virtual_file(assembled, session, repository)
            values['technical_metadata'] = {'vrt_sources': sorted(vrt_sources), 'validation': 'Fuentes locales del grupo verificadas; su lectura se procesa como trabajo posterior.'}
        else:
            _validate_auxiliary_file(assembled, session, repository)
            values['technical_metadata'] = {'validation': 'XML auxiliar bien formado, sin DTD ni entidades.'}

        storage_key = str(Path('assets') / digest[:2] / f'{digest}{extension}')
        destination = _storage_path(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            assembled.unlink(missing_ok=True)
        else:
            os.replace(assembled, destination)
            moved_destination = True
        declared = dict(session['declared_metadata'] or {})
        captured_at = declared.get('captured_at')
        if captured_at:
            try:
                captured_at = date.fromisoformat(str(captured_at))
            except ValueError:
                captured_at = None
        west = south = east = north = None
        if extent:
            west, south, east, north = extent
        asset_id = str(uuid.uuid4())
        asset_id = repository.register_asset({
            'asset_id': asset_id,
            'asset_group_id': str(session['asset_group_id']) if session.get('asset_group_id') else None,
            'source_asset_id': str(session['source_asset_id']) if session.get('source_asset_id') else None,
            'original_name': session['original_name'], 'storage_key': storage_key, 'sha256': digest,
            'byte_size': byte_size, 'asset_kind': file_kind, 'mime_type': 'image/tiff' if file_kind == 'raster' else 'application/xml',
            'captured_at': captured_at, 'declared_metadata': declared, 'extent': extent,
            'west': west, 'south': south, 'east': east, 'north': north, **values,
        })
        asset_registered = True
        repository.insert_bands(asset_id, bands)
        if session.get('source_asset_id'):
            repository.create_relation(str(session['source_asset_id']), asset_id, 'auxiliary' if file_kind == 'auxiliary' else 'source')
        if file_kind == 'virtual':
            for source_asset_id in vrt_sources.values():
                repository.create_relation(source_asset_id, asset_id, 'vrt_dependency')
        repository.complete_upload_session(str(session_id), asset_id, False)
        shutil.rmtree(session_dir, ignore_errors=True)
        return {'asset_id': asset_id, 'deduplicated': False, 'state': 'completed'}
    except HTTPException as exc:
        assembled.unlink(missing_ok=True)
        if moved_destination and destination and not asset_registered:
            destination.unlink(missing_ok=True)
        try:
            repository.fail_upload_session(str(session_id), str(exc.detail))
        except CatalogUnavailable:
            pass
        shutil.rmtree(session_dir, ignore_errors=True)
        raise
    except (OSError, CatalogUnavailable) as exc:
        assembled.unlink(missing_ok=True)
        if moved_destination and destination and not asset_registered:
            destination.unlink(missing_ok=True)
        try:
            repository.fail_upload_session(str(session_id), 'Fallo al procesar la carga.')
        except CatalogUnavailable:
            pass
        shutil.rmtree(session_dir, ignore_errors=True)
        raise HTTPException(503, 'No se pudo completar la carga persistente.') from exc
