"""CoinGecko -> PostgreSQL (bronze layer).

Usage:
    python pipeline.py snapshot            # live data: markets + global + trending
    python pipeline.py history             # one-off backfill (365 days, the Demo plan max)
    python pipeline.py history --days 2    # daily incremental refresh
"""
import argparse
import logging
import sys
import time
from datetime import datetime, timezone

import config
import db
from client import CoinGeckoClient

log = logging.getLogger("pipeline")

# bronze column -> field name in the /coins/markets response
MARKET_FIELDS = {
    "coin_id": "id",
    "symbol": "symbol",
    "name": "name",
    "current_price": "current_price",
    "market_cap": "market_cap",
    "market_cap_rank": "market_cap_rank",
    "fully_diluted_valuation": "fully_diluted_valuation",
    "total_volume": "total_volume",
    "high_24h": "high_24h",
    "low_24h": "low_24h",
    "price_change_pct_1h": "price_change_percentage_1h_in_currency",
    "price_change_pct_24h": "price_change_percentage_24h_in_currency",
    "price_change_pct_7d": "price_change_percentage_7d_in_currency",
    "circulating_supply": "circulating_supply",
    "total_supply": "total_supply",
    "max_supply": "max_supply",
    "ath": "ath",
    "ath_date": "ath_date",
    "last_updated": "last_updated",
}

GLOBAL_COLUMNS = [
    "updated_at", "active_cryptocurrencies", "markets", "total_market_cap_usd",
    "total_volume_usd", "btc_dominance_pct", "eth_dominance_pct",
    "market_cap_change_pct_24h_usd",
]
TRENDING_COLUMNS = ["snapshot_at", "rank", "coin_id", "name", "symbol", "market_cap_rank"]
DAILY_COLUMNS = ["coin_id", "price_date", "price", "market_cap", "total_volume"]
DAILY_UPSERT = """
ON CONFLICT (coin_id, price_date) DO UPDATE SET
    price = EXCLUDED.price,
    market_cap = EXCLUDED.market_cap,
    total_volume = EXCLUDED.total_volume,
    ingested_at = now()
"""


# ---------- snapshot loaders (append-only, idempotent) ----------

def load_markets(client, conn):
    coins = client.markets(per_page=config.TOP_N_COINS)
    rows = [tuple(c.get(field) for field in MARKET_FIELDS.values()) for c in coins]
    new = db.insert(conn, "bronze.coin_markets", list(MARKET_FIELDS), rows)
    log.info("coin_markets: %d fetched, %d new", len(rows), new)


def load_global(client, conn):
    g = client.global_data()
    row = (
        datetime.fromtimestamp(g["updated_at"], tz=timezone.utc),
        g["active_cryptocurrencies"],
        g["markets"],
        g["total_market_cap"]["usd"],
        g["total_volume"]["usd"],
        g["market_cap_percentage"].get("btc"),
        g["market_cap_percentage"].get("eth"),
        g["market_cap_change_percentage_24h_usd"],
    )
    new = db.insert(conn, "bronze.global_market", GLOBAL_COLUMNS, [row])
    log.info("global_market: %d new", new)


def load_trending(client, conn):
    snapshot_at = datetime.now(timezone.utc)
    items = [c["item"] for c in client.trending()]
    rows = [
        (snapshot_at, rank, i["id"], i["name"], i["symbol"], i.get("market_cap_rank"))
        for rank, i in enumerate(items, start=1)
    ]
    new = db.insert(conn, "bronze.trending_coins", TRENDING_COLUMNS, rows)
    log.info("trending_coins: %d new", new)


def run_snapshot(client, conn):
    """Run each loader independently so one failure does not block the others."""
    failed = 0
    for job in (load_markets, load_global, load_trending):
        try:
            job(client, conn)
            conn.commit()
        except Exception:
            conn.rollback()
            log.exception("%s failed", job.__name__)
            failed += 1
    return failed


# ---------- history loader (upsert) ----------

def parse_chart(coin_id, chart):
    """Merge price / market cap / volume series into one row per UTC day."""
    by_day = {}  # later points of the same day overwrite earlier ones
    series = zip(chart["prices"], chart["market_caps"], chart["total_volumes"])
    for (ts, price), (_, market_cap), (_, volume) in series:
        if price is None:
            continue
        day = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date()
        by_day[day] = (coin_id, day, price, market_cap, volume)
    return list(by_day.values())


def run_history(client, conn, days):
    coins = client.markets(per_page=config.HISTORY_COINS)
    failed = 0
    for coin in coins:
        coin_id = coin["id"]
        try:
            rows = parse_chart(coin_id, client.market_chart(coin_id, days))
            db.insert(conn, "bronze.coin_daily", DAILY_COLUMNS, rows, DAILY_UPSERT)
            conn.commit()
            log.info("coin_daily: %s -> %d days", coin_id, len(rows))
        except Exception:
            conn.rollback()
            log.exception("history failed for %s", coin_id)
            failed += 1
        time.sleep(config.REQUEST_PAUSE_SECONDS)
    return failed


# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("snapshot", help="load live market, global and trending data")
    hist = sub.add_parser("history", help="load daily price history")
    hist.add_argument("--days", type=int, default=config.HISTORY_DAYS)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = CoinGeckoClient()
    conn = db.connect()
    try:
        if args.command == "snapshot":
            failed = run_snapshot(client, conn)
        else:
            failed = run_history(client, conn, min(args.days, config.HISTORY_DAYS))
    finally:
        conn.close()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
