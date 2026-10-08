# CoinGecko Live Crypto Analytics

An end-to-end crypto market analytics project that pulls live market data from CoinGecko, stores it in PostgreSQL, and exposes an analyst-ready reporting layer for Power BI dashboards.

## Project overview

This project was built to turn raw market API data into a practical decision-support dataset for crypto monitoring, performance tracking, and market trend analysis. The objective was simple: create a repeatable pipeline that ingests live market signals, structures them into a reliable warehouse model, and surfaces business-friendly metrics for dashboard reporting.

The solution follows a modern medallion architecture:

- Bronze: raw API ingestion from CoinGecko
- Silver: cleaned, enriched, and normalized data
- Gold: curated views optimized for reporting and Power BI consumption

This project is designed to demonstrate strong data engineering fundamentals, clear modeling discipline, and practical business reporting.

---

## Business value

The pipeline enables:

- market monitoring of the largest cryptocurrencies by market cap
- price and trend analysis over short- and medium-term horizons
- volatility and drawdown monitoring for risk-aware decision support
- trending coin tracking for sentiment and market attention
- daily performance metrics for Power BI reporting and executive visibility

This is particularly useful for:

- crypto market monitoring
- trading intelligence dashboards
- portfolio watchlists
- market structure and risk analysis
- operational reporting for digital asset teams

---

## Architecture

```text
CoinGecko API
    │
    ▼
Python ingestion layer (client.py + pipeline.py)
    │
    ▼
PostgreSQL bronze tables
    │
    ▼
SQL silver views
    │
    ▼
SQL gold reporting views
    │
    ▼
Power BI dashboard and market reporting
```

---

## Data sources and ingestion logic

| Endpoint | Destination table | Frequency | Purpose |
|---|---|---|---|
| `/coins/markets` | `bronze.coin_markets` | snapshot | current price, market cap, volume, 24h/7d changes, ATH, supply metrics |
| `/global` | `bronze.global_market` | snapshot | total market cap, total volume, BTC/ETH dominance, 24h market shift |
| `/search/trending` | `bronze.trending_coins` | snapshot | trending coin list and popularity signals |
| `/coins/{id}/market_chart` | `bronze.coin_daily` | daily upsert | historical daily pricing for returns, volatility, and moving averages |

### Data collection logic

- snapshot jobs capture the latest live market state
- history jobs backfill normalized daily price series for selected coins
- raw bronze data is intentionally append-only or idempotent to keep the source-of-truth pipeline clean
- downstream views enrich the data with return calculations, windowed averages, volatility, drawdown, and KPI metrics

---

## Project structure

```text
coingecko-pipeline/
├── client.py                 # CoinGecko API client and retry logic
├── config.py                 # environment-driven configuration
├── db.py                     # PostgreSQL connection and insert helpers
├── pipeline.py               # ingestion orchestration and CLI entry point
├── requirements.txt          # Python dependencies
├── .env.example              # sample environment variables
├── .env                     # local secret config (not committed)
├── README.md                 # project documentation
├── sql/
│   ├── 01_tables.sql         # bronze schema creation
│   └── 02_views.sql          # silver + gold reporting views
├── report assets/
│   ├── market overview.pdf
│   ├── 24h coin analysis.pdf
│   ├── daily volatility.pdf
│   ├── trending coin.pdf
│   └── Coin Gecko Coin Daily Report.pbix
└── .venv/                    # local virtual environment (not committed)
```

---

## Repository conventions

### Bronze layer

Raw data tables are stored exactly as loaded from the API and are optimized for traceability and reprocessing.

### Silver layer

This layer adds transformation logic for:

- daily return calculations
- market-cap-to-volume ratios
- 24h range calculations
- rolling window metrics

### Gold layer

The gold layer is the reporting layer used by Power BI. It contains:

- `gold.market_overview` for KPI cards and market-level monitoring
- `gold.market_history` for trend analysis across time
- `gold.coin_latest` for current state per coin
- `gold.coin_price_intraday` for intraday price lines
- `gold.coin_daily_metrics` for return, moving average, volatility, and drawdown analysis
- `gold.trending_latest` for trending coin sentiment views

---

## Local setup

### Prerequisites

- Python 3.10+
- PostgreSQL installed locally or reachable via host
- `psql` available in PATH
- CoinGecko API key

### 1) Create and activate the virtual environment

#### Windows PowerShell

```powershell
cd "your dir"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> Note: if PowerShell blocks activation, run:
>
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> .\.venv\Scripts\Activate.ps1
> ```

#### macOS / Linux

```bash
cd /path/to/coingecko-pipeline
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure environment variables

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

Example:

```env
COINGECKO_API_KEY=your_api_key_here

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=crypto_analytics
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password

TOP_N_COINS=100
HISTORY_COINS=20
```

---

## Database setup

Create the PostgreSQL database and load the schema:

```bash
createdb crypto_analytics
psql -d crypto_analytics -f sql/01_tables.sql
psql -d crypto_analytics -f sql/02_views.sql
```

If you are using Windows, the equivalent is typically:

```powershell
psql -U postgres -c "CREATE DATABASE crypto_analytics;"
psql -U postgres -d crypto_analytics -f sql\01_tables.sql
psql -U postgres -d crypto_analytics -f sql\02_views.sql
```

---

## Running the pipeline

### Full history backfill

```bash
python pipeline.py history
```

This loads daily history for the selected set of tracked coins, up to the Demo plan limit.

### Live snapshot

```bash
python pipeline.py snapshot
```

This fetches the latest market, global, and trending data.

### Incremental history refresh

```bash
python pipeline.py history --days 2
```

This is useful for shorter refresh windows or recent backfill updates.

---

## Scheduling and automation

This project is designed to run on a recurring schedule.

### Linux / cron example

```cron
*/30 * * * *  cd /path/to/coingecko-pipeline && .venv/bin/python pipeline.py snapshot
15 0 * * *    cd /path/to/coingecko-pipeline && .venv/bin/python pipeline.py history --days 2
```

### Windows Task Scheduler

Use the same commands with the Windows Python path:

```powershell
cd /d "your dir"
.\.venv\Scripts\python.exe pipeline.py snapshot
```

The reason the history refresh is scheduled at 00:15 UTC is practical: CoinGecko publishes the prior completed UTC day around 00:10, so a slight delay helps avoid missing or incomplete close-of-day data.

---

## Rate limits and operational notes

CoinGecko Demo plans have strict API limits, so this project was built with operational discipline in mind:

- each successful request consumes a credit
- snapshot loads are intentionally lightweight and bounded by `TOP_N_COINS`
- history loads are limited by `HISTORY_COINS`
- the client retries on HTTP 429 and 5xx responses to absorb temporary rate-limit conditions
- the pipeline waits between history calls using a configurable pause interval

This makes it resilient enough for automated use without failing noisily under rate-limit pressure.

---

## Power BI reporting layer

The project is designed to connect directly to PostgreSQL and query the gold-layer views. These views are optimized for executive and analyst dashboards.

### Gold views for Power BI

- `gold.market_overview` — KPI cards for total market cap, total volume, BTC dominance, and ETH dominance
- `gold.market_history` — market-wide historical trend analysis
- `gold.coin_latest` — latest snapshot per coin for rankings and top movers
- `gold.coin_price_intraday` — intraday price lines and current pricing snapshot
- `gold.coin_daily_metrics` — daily return, moving averages, volatility, and drawdown calculations
- `gold.trending_latest` — latest trending coin list

### Recommended Power BI connection mode

For local dashboarding, Import mode is usually the easiest and fastest option. For real-time visibility, DirectQuery is also viable if you want the latest PostgreSQL data without refreshing the model manually.

The recommended analyst workflow is:

- connect Power BI to PostgreSQL
- load the `gold` schema
- use `coin_id` as the key for coin-level relationships
- use `symbol` and `name` for slicers and drilldowns
- build one market overview page and one coin analysis page

---

## Recommended data model in Power BI

Use the following structure in the data model:

- `gold.coin_latest` as the dimension table for coin metadata
- `gold.coin_daily_metrics` and `gold.coin_price_intraday` as fact tables for time-based analytics
- `gold.market_overview` and `gold.market_history` as market facts
- `gold.trending_latest` as a ranking table for sentiment analysis

### Relationship logic

The key business relationship is:

- one `coin_id` in `gold.coin_latest`
- many matching rows in `gold.coin_daily_metrics`
- many matching rows in `gold.coin_price_intraday`

So the relationship should be configured as:

- `gold.coin_daily_metrics[coin_id]` → `gold.coin_latest[coin_id]` : Many to one
- `gold.coin_price_intraday[coin_id]` → `gold.coin_latest[coin_id]` : Many to one
- `gold.trending_latest[coin_id]` → `gold.coin_latest[coin_id]` : Many to one

This supports clean filtering by coin, symbol, and name across the report.

---

## Suggested report pages

### 1) Market Overview

- total market cap
- total volume
- BTC dominance
- ETH dominance
- market cap trend over time
- volume trend over time

### 2) Top Movers

- latest market snapshot by coin
- price change by 1h, 24h, 7d
- market cap ranking
- volume-to-market-cap ratio

### 3) Coin Analysis

- selected coin price chart
- moving averages
- daily returns
- drawdown analysis
- volatility trends

### 4) Trending Market

- most active trending coins
- rank changes
- market attention snapshot over time

---

## Report assets

The repository includes a set of generated reporting assets under the `report assets/` folder. These files provide a visual baseline for the project and can be used as references for the Power BI deliverable:

- `Coin Gecko Coin Daily Report.pbix`
- `market overview.pdf`
- `24h coin analysis.pdf`
- `daily volatility.pdf`
- `trending coin.pdf`

These assets are useful for validating the structure and narrative of the dashboard before expanding into a wider reporting suite.

## Dashboard screenshots

### Market overview

![Market overview dashboard](jpg%20assets/market%20overview_page.jpg)

This page summarizes the current market state. It highlights key macro-level KPIs such as active cryptocurrency count, market cap, trading volume, and BTC/ETH dominance. It is designed to provide a quick executive-level view of overall market health and momentum at a glance.

### 24h coin analysis

![24h coin analysis dashboard](jpg%20assets/24h%20coin%20analysis.jpg)

This view focuses on short-term coin behavior. It compares current price levels, recent performance, and daily return volatility across the tracked asset set. It is especially useful for identifying which coins are moving sharply within a short time window and which assets are displaying stronger or weaker momentum.

### Daily volatility

![Daily volatility dashboard](jpg%20assets/daily%20volatility.jpg)

This page highlights risk and market stability. By surfacing market-cap-weighted exposure, price movement ranges, and volatility signals, it helps identify which coins may be comparatively more unstable or more resilient in the current market cycle.

### Trending coin analysis

![Trending coin dashboard](jpg%20assets/trending%20coin_page.jpg)

This report surfaces the most actively discussed or attention-heavy assets based on ranking and trending signal data. It provides a user-friendly way to scan the market for momentum and sentiment-driven opportunities, while also showing ranking intensity across the current list of tracked coins.

---

These dashboard views reflect the same underlying data model: raw API ingestion flows into standardized bronze tables, is transformed into SQL-based analytics views, and is then surfaced through Power BI. The end result is a clear, analyst-friendly narrative from raw crypto data to actionable market insight.

---

## Data quality and reliability checks

This project assumes operational discipline around data quality:

- null values are handled in view logic
- daily calculations are window-based and resilient to missing values
- raw ingestion remains traceable to the source API payloads
- reporting logic sits above the raw layer rather than in the ingestion scripts

Recommended validation checks:

- confirm only expected schema tables exist
- verify record counts for snapshot jobs
- validate that daily market data has one row per coin per day
- inspect duplicate or stale coin entries in the latest view
- ensure no API rate-limit failures are silently skipping updates

---

## Security and repository hygiene

This repository should never store secrets in version control. Keep:

- `.env` local only
- `.venv` local only
- generated caches and runtime artifacts out of the repo

The project includes a `.gitignore` to keep local environment artifacts from polluting source control.

---

## Recommended next steps

1. run the pipeline locally and validate the data loads into PostgreSQL
2. check each `gold` view for correctness and completeness
3. connect Power BI to PostgreSQL and test the reporting layer
4. build the market overview dashboard first
5. extend into coin-level analysis and trending insights
6. choose Import or DirectQuery based on reporting latency and performance requirements

---

## Conclusion

This project demonstrates a practical analytics workflow that moves from raw API data to a structured, reportable data product. It combines data extraction, transformation, modeling, and presentation into a single end-to-end solution that is realistic, maintainable, and suitable for portfolio-style showcasing.

The work reflects core data engineering principles: repeatable ingestion, reliable storage, layered transformation logic, and business-facing analytics design. It is a strong example of how raw market data can be turned into actionable dashboard insight using a clean and scalable architecture.
