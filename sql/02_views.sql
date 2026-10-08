-- ===================== SILVER: cleaned + enriched =====================

CREATE OR REPLACE VIEW silver.coin_snapshot AS
SELECT
    coin_id,
    upper(symbol)                                       AS symbol,
    name,
    current_price,
    market_cap,
    market_cap_rank,
    total_volume,
    high_24h,
    low_24h,
    price_change_pct_1h,
    price_change_pct_24h,
    price_change_pct_7d,
    circulating_supply,
    max_supply,
    ath,
    ath_date,
    total_volume / NULLIF(market_cap, 0)                AS volume_to_mcap_ratio,
    (high_24h - low_24h) / NULLIF(low_24h, 0) * 100     AS range_24h_pct,
    last_updated,
    ingested_at
FROM bronze.coin_markets
WHERE current_price IS NOT NULL;

CREATE OR REPLACE VIEW silver.coin_daily AS
SELECT
    coin_id,
    price_date,
    price,
    market_cap,
    total_volume,
    (price / NULLIF(LAG(price) OVER w, 0) - 1) * 100    AS daily_return_pct
FROM bronze.coin_daily
WINDOW w AS (PARTITION BY coin_id ORDER BY price_date);

-- ===================== GOLD: what Power BI reads =====================

-- Latest row per coin (ignores coins that dropped out of the tracked list > 1 day ago)
CREATE OR REPLACE VIEW gold.coin_latest AS
SELECT DISTINCT ON (coin_id) *
FROM silver.coin_snapshot
WHERE last_updated >= (SELECT max(last_updated) - interval '1 day' FROM silver.coin_snapshot)
ORDER BY coin_id, last_updated DESC;

-- Intraday price history built from the live snapshots
CREATE OR REPLACE VIEW gold.coin_price_intraday AS
SELECT coin_id, symbol, name, last_updated, current_price, market_cap, total_volume
FROM silver.coin_snapshot;

-- Daily metrics: moving averages, 30-day volatility, drawdown from all-time max in window
CREATE OR REPLACE VIEW gold.coin_daily_metrics AS
SELECT
    d.coin_id,
    l.symbol,
    l.name,
    d.price_date,
    d.price,
    d.market_cap,
    d.total_volume,
    d.daily_return_pct,
    AVG(d.price)                  OVER w7   AS ma_7d,
    AVG(d.price)                  OVER w30  AS ma_30d,
    STDDEV_SAMP(d.daily_return_pct) OVER w30 AS volatility_30d_pct,
    (d.price / MAX(d.price) OVER wall - 1) * 100 AS drawdown_pct
FROM silver.coin_daily d
LEFT JOIN gold.coin_latest l ON l.coin_id = d.coin_id
WINDOW
    w7   AS (PARTITION BY d.coin_id ORDER BY d.price_date ROWS BETWEEN 6  PRECEDING AND CURRENT ROW),
    w30  AS (PARTITION BY d.coin_id ORDER BY d.price_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW),
    wall AS (PARTITION BY d.coin_id ORDER BY d.price_date);

-- Whole-market KPI cards (latest) and trend (history)
CREATE OR REPLACE VIEW gold.market_overview AS
SELECT * FROM bronze.global_market ORDER BY updated_at DESC LIMIT 1;

CREATE OR REPLACE VIEW gold.market_history AS
SELECT updated_at, total_market_cap_usd, total_volume_usd,
       btc_dominance_pct, eth_dominance_pct, market_cap_change_pct_24h_usd
FROM bronze.global_market;

-- Latest trending list
CREATE OR REPLACE VIEW gold.trending_latest AS
SELECT snapshot_at, rank, coin_id, name, upper(symbol) AS symbol, market_cap_rank
FROM bronze.trending_coins
WHERE snapshot_at = (SELECT max(snapshot_at) FROM bronze.trending_coins);
