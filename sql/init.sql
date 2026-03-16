-- ================================================================
-- TRADES RAW
-- exploded raw data, one record per individual trade
-- equivalent to the Bronze layer in your datalake
-- ================================================================
CREATE TABLE IF NOT EXISTS trades_raw (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(50)      NOT NULL,
    price           DOUBLE PRECISION NOT NULL,
    volume          DOUBLE PRECISION NOT NULL,
    event_time      TIMESTAMPTZ      NOT NULL,
    ingested_at     TIMESTAMPTZ      DEFAULT NOW()
);

-- indexes for dashboard queries and dbt
CREATE INDEX idx_trades_raw_symbol      ON trades_raw (symbol);
CREATE INDEX idx_trades_raw_event_time  ON trades_raw (event_time DESC);
CREATE INDEX idx_trades_raw_symbol_time ON trades_raw (symbol, event_time DESC);

-- ================================================================
-- TRADES AGGREGATED 1MIN
-- metrics per 1-minute window per symbol
-- equivalent to the Silver layer
-- ================================================================
CREATE TABLE IF NOT EXISTS trades_aggregated_1min (
    id              BIGSERIAL PRIMARY KEY,
    window_start    TIMESTAMPTZ      NOT NULL,
    window_end      TIMESTAMPTZ      NOT NULL,
    symbol          VARCHAR(50)      NOT NULL,
    total_volume    DOUBLE PRECISION,
    avg_price       DOUBLE PRECISION,
    min_price       DOUBLE PRECISION,
    max_price       DOUBLE PRECISION,
    trade_count     BIGINT,
    volatility      DOUBLE PRECISION,
    vwap            DOUBLE PRECISION,
    ingested_at     TIMESTAMPTZ      DEFAULT NOW(),

    -- prevents duplicates if Spark restarts and rewrites
    UNIQUE (window_start, symbol)
);

CREATE INDEX idx_agg_1min_symbol      ON trades_aggregated_1min (symbol);
CREATE INDEX idx_agg_1min_window      ON trades_aggregated_1min (window_start DESC);
CREATE INDEX idx_agg_1min_symbol_time ON trades_aggregated_1min (symbol, window_start DESC);

-- ================================================================
-- TRADES AGGREGATED 5MIN
-- metrics per 5-minute sliding window
-- ================================================================
CREATE TABLE IF NOT EXISTS trades_aggregated_5min (
    id              BIGSERIAL PRIMARY KEY,
    window_start    TIMESTAMPTZ      NOT NULL,
    window_end      TIMESTAMPTZ      NOT NULL,
    symbol          VARCHAR(50)      NOT NULL,
    total_volume    DOUBLE PRECISION,
    avg_price       DOUBLE PRECISION,
    volatility      DOUBLE PRECISION,
    vwap            DOUBLE PRECISION,
    ingested_at     TIMESTAMPTZ      DEFAULT NOW(),

    UNIQUE (window_start, symbol)
);

CREATE INDEX idx_agg_5min_symbol      ON trades_aggregated_5min (symbol);
CREATE INDEX idx_agg_5min_window      ON trades_aggregated_5min (window_start DESC);
CREATE INDEX idx_agg_5min_symbol_time ON trades_aggregated_5min (symbol, window_start DESC);

-- ================================================================
-- ANOMALIES
-- records where volume > 3x batch average
-- ================================================================
CREATE TABLE IF NOT EXISTS anomalies (
    id              BIGSERIAL PRIMARY KEY,
    detected_at     TIMESTAMPTZ      DEFAULT NOW(),
    symbol          VARCHAR(50)      NOT NULL,
    window_start    TIMESTAMPTZ      NOT NULL,
    window_end      TIMESTAMPTZ      NOT NULL,
    total_volume    DOUBLE PRECISION,
    avg_volume      DOUBLE PRECISION,
    ratio           DOUBLE PRECISION, -- total_volume / avg_volume
    avg_price       DOUBLE PRECISION,
    vwap            DOUBLE PRECISION
);

CREATE INDEX idx_anomalies_symbol     ON anomalies (symbol);
CREATE INDEX idx_anomalies_detected   ON anomalies (detected_at DESC);