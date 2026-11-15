-- Ejecutar como el rol de aplicación dentro de geoportal_db, después de
-- CREATE EXTENSION postgis. No contiene contraseñas ni toca otras bases.
CREATE SCHEMA IF NOT EXISTS geoportal AUTHORIZATION CURRENT_USER;

CREATE TABLE IF NOT EXISTS geoportal.asset_groups (
    asset_group_id uuid PRIMARY KEY,
    label text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS geoportal.raster_assets (
    asset_id uuid PRIMARY KEY,
    asset_group_id uuid REFERENCES geoportal.asset_groups(asset_group_id),
    source_asset_id uuid REFERENCES geoportal.raster_assets(asset_id),
    original_name text NOT NULL,
    storage_key text NOT NULL UNIQUE,
    sha256 char(64) NOT NULL UNIQUE,
    byte_size bigint NOT NULL CHECK (byte_size >= 0),
    asset_kind text NOT NULL CHECK (asset_kind IN ('raster', 'virtual', 'auxiliary', 'derived', 'mask')),
    mime_type text NOT NULL,
    crs_text text,
    epsg integer,
    width integer CHECK (width IS NULL OR width > 0),
    height integer CHECK (height IS NULL OR height > 0),
    band_count integer CHECK (band_count IS NULL OR band_count > 0),
    nodata double precision,
    resolution_x double precision,
    resolution_y double precision,
    extent_4326 geometry(Polygon, 4326),
    captured_at date,
    declared_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    technical_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    ingestion_status text NOT NULL CHECK (ingestion_status IN ('ready', 'quarantined', 'failed')),
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS raster_assets_extent_4326_gix
    ON geoportal.raster_assets USING gist (extent_4326);
CREATE INDEX IF NOT EXISTS raster_assets_captured_at_idx
    ON geoportal.raster_assets (captured_at DESC NULLS LAST);

CREATE TABLE IF NOT EXISTS geoportal.raster_bands (
    asset_id uuid NOT NULL REFERENCES geoportal.raster_assets(asset_id) ON DELETE CASCADE,
    band_index integer NOT NULL CHECK (band_index > 0),
    dtype text NOT NULL,
    scale double precision,
    band_offset double precision,
    description text,
    color_interpretation text,
    semantic_role text,
    PRIMARY KEY (asset_id, band_index)
);

CREATE TABLE IF NOT EXISTS geoportal.asset_relations (
    parent_asset_id uuid NOT NULL REFERENCES geoportal.raster_assets(asset_id) ON DELETE CASCADE,
    child_asset_id uuid NOT NULL REFERENCES geoportal.raster_assets(asset_id) ON DELETE CASCADE,
    relation_type text NOT NULL CHECK (relation_type IN ('source', 'mask', 'auxiliary', 'derived_from', 'vrt_dependency')),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (parent_asset_id, child_asset_id, relation_type),
    CHECK (parent_asset_id <> child_asset_id)
);

CREATE TABLE IF NOT EXISTS geoportal.upload_sessions (
    session_id uuid PRIMARY KEY,
    original_name text NOT NULL,
    expected_bytes bigint NOT NULL CHECK (expected_bytes > 0),
    expected_chunks integer NOT NULL CHECK (expected_chunks > 0),
    chunk_bytes integer NOT NULL CHECK (chunk_bytes > 0),
    requested_sha256 char(64),
    file_kind text NOT NULL CHECK (file_kind IN ('raster', 'virtual', 'auxiliary')),
    declared_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    asset_group_id uuid REFERENCES geoportal.asset_groups(asset_group_id),
    source_asset_id uuid REFERENCES geoportal.raster_assets(asset_id),
    received_chunks jsonb NOT NULL DEFAULT '{}'::jsonb,
    received_bytes bigint NOT NULL DEFAULT 0,
    state text NOT NULL DEFAULT 'active' CHECK (state IN ('active', 'completed', 'failed', 'expired')),
    asset_id uuid REFERENCES geoportal.raster_assets(asset_id),
    deduplicated boolean NOT NULL DEFAULT false,
    error_message text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz
);
CREATE INDEX IF NOT EXISTS upload_sessions_state_idx ON geoportal.upload_sessions (state, created_at);

CREATE TABLE IF NOT EXISTS geoportal.processing_jobs (
    job_id uuid PRIMARY KEY,
    submitted_by text,
    job_type text NOT NULL,
    input_fingerprint char(64) NOT NULL,
    parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
    state text NOT NULL CHECK (state IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
    progress numeric(5,2) NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    cache_key char(64),
    result_asset_id uuid REFERENCES geoportal.raster_assets(asset_id),
    result_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    error_message text,
    created_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    completed_at timestamptz
);
CREATE INDEX IF NOT EXISTS processing_jobs_fingerprint_idx
    ON geoportal.processing_jobs (input_fingerprint, job_type, state);

CREATE TABLE IF NOT EXISTS geoportal.persistent_cache (
    cache_key char(64) PRIMARY KEY,
    namespace text NOT NULL,
    payload jsonb NOT NULL,
    expires_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    accessed_at timestamptz NOT NULL DEFAULT now()
);
