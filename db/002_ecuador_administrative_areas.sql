-- Provincias para selección zonal del Geoportal. Las geometrías se conservan
-- fuera de los GeoTIFF y no modifican el catálogo de rásteres existente.
CREATE TABLE IF NOT EXISTS geoportal.administrative_areas (
    area_id text PRIMARY KEY,
    level text NOT NULL CHECK (level IN ('province')),
    name_es text NOT NULL,
    name_en text NOT NULL,
    source_year text,
    source_title text NOT NULL,
    source_url text NOT NULL,
    boundary geometry(MultiPolygon, 4326) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS administrative_areas_boundary_gix
    ON geoportal.administrative_areas USING gist (boundary);
GRANT SELECT, INSERT, UPDATE ON geoportal.administrative_areas TO geoportal_app;
