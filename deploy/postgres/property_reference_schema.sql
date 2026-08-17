CREATE TABLE IF NOT EXISTS ai_reference_metadata (
    source_name TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    row_count BIGINT NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_property_reference (
    district TEXT NOT NULL,
    bun CHAR(4) NOT NULL,
    ji CHAR(4) NOT NULL,
    housing_type TEXT NOT NULL,
    model_name TEXT NOT NULL,
    source_building_name TEXT NOT NULL,
    sample_count BIGINT NOT NULL CHECK (sample_count > 0),
    PRIMARY KEY (
        district,
        bun,
        ji,
        housing_type,
        model_name,
        source_building_name
    )
);

CREATE INDEX IF NOT EXISTS idx_ai_property_reference_parcel
    ON ai_property_reference (
        district, bun, ji, housing_type
    );

CREATE INDEX IF NOT EXISTS idx_ai_property_reference_district
    ON ai_property_reference (district, housing_type);

CREATE INDEX IF NOT EXISTS idx_ai_property_reference_type
    ON ai_property_reference (housing_type);
