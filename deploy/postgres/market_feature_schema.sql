CREATE TABLE IF NOT EXISTS ai_market_metadata (
    source_name TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    row_count BIGINT NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_rone_value (
    transaction_type TEXT NOT NULL,
    housing_type TEXT NOT NULL,
    region_path TEXT NOT NULL,
    region_name TEXT NOT NULL,
    size_band TEXT NOT NULL,
    base_month CHAR(7) NOT NULL,
    feature_name TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (
        transaction_type,
        housing_type,
        region_path,
        size_band,
        base_month,
        feature_name
    )
);

CREATE INDEX IF NOT EXISTS idx_ai_rone_lookup
    ON ai_rone_value (
        transaction_type,
        housing_type,
        size_band,
        feature_name,
        base_month DESC
    );

CREATE INDEX IF NOT EXISTS idx_ai_rone_region
    ON ai_rone_value (region_name, region_path);

CREATE TABLE IF NOT EXISTS ai_cofix_value (
    publication_date DATE PRIMARY KEY,
    target_month CHAR(7) NOT NULL,
    value DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_ecos_mortgage_rate (
    contract_month CHAR(7) PRIMARY KEY,
    base_month CHAR(7) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    provisional BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_kosis_value (
    contract_month CHAR(7) NOT NULL,
    base_month CHAR(7) NOT NULL,
    feature_name TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    provisional BOOLEAN NOT NULL,
    PRIMARY KEY (contract_month, feature_name)
);

CREATE INDEX IF NOT EXISTS idx_ai_kosis_lookup
    ON ai_kosis_value (contract_month DESC, feature_name);
