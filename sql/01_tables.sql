-- Three-tier (medallion) layout:
--   bronze = raw data exactly as loaded by Python
--   silver = cleaned, typed, enriched views
--   gold   = business-ready views that Power BI reads
CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- /coins/markets: one row per coin per CoinGecko update (append-only snapshots)
CREATE TABLE IF NOT EXISTS bronze.coin_markets (
    coin_id                 text        NOT NULL,
    symbol                  text,
    name                    text,
    current_price           numeric,
    market_cap              numeric,
    market_cap_rank         integer,
    fully_diluted_valuation numeric,
    total_volume            numeric,
    high_24h                numeric,
    low_24h                 numeric,
    price_change_pct_1h     numeric,
    price_change_pct_24h    numeric,
    price_change_pct_7d     numeric,
    circulating_supply      numeric,
    total_supply            numeric,
    max_supply              numeric,
    ath                     numeric,
    ath_date                timestamptz,
    last_updated            timestamptz NOT NULL,
    ingested_at             timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (coin_id, last_updated)
);

-- /global: whole-market snapshot
CREATE TABLE IF NOT EXISTS bronze.global_market (
    updated_at                    timestamptz PRIMARY KEY,
    active_cryptocurrencies       integer,
    markets                       integer,
    total_market_cap_usd          numeric,
    total_volume_usd              numeric,
    btc_dominance_pct             numeric,
    eth_dominance_pct             numeric,
    market_cap_change_pct_24h_usd numeric,
    ingested_at                   timestamptz NOT NULL DEFAULT now()
);

-- /search/trending: top trending coins per snapshot
CREATE TABLE IF NOT EXISTS bronze.trending_coins (
    snapshot_at     timestamptz NOT NULL,
    rank            integer     NOT NULL,
    coin_id         text        NOT NULL,
    name            text,
    symbol          text,
    market_cap_rank integer,
    PRIMARY KEY (snapshot_at, coin_id)
);

-- /coins/{id}/market_chart: one row per coin per UTC day (upserted)
CREATE TABLE IF NOT EXISTS bronze.coin_daily (
    coin_id      text    NOT NULL,
    price_date   date    NOT NULL,
    price        numeric NOT NULL,
    market_cap   numeric,
    total_volume numeric,
    ingested_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (coin_id, price_date)
);
