"""Thin CoinGecko API client: one method per endpoint, retries on 429 / 5xx."""
import logging
import time

import requests

import config

log = logging.getLogger(__name__)


class CoinGeckoClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers["accept"] = "application/json"
        if config.API_KEY:
            self.session.headers["x-cg-demo-api-key"] = config.API_KEY

    def _get(self, path, params=None, max_retries=5):
        url = f"{config.API_BASE_URL}{path}"
        for attempt in range(1, max_retries + 1):
            resp = self.session.get(url, params=params, timeout=30)
            if resp.status_code == 429 or resp.status_code >= 500:
                retry_after = resp.headers.get("Retry-After", "")
                wait = int(retry_after) if retry_after.isdigit() else 15 * attempt
                log.warning("%s -> HTTP %s, retry %d/%d in %ds",
                            path, resp.status_code, attempt, max_retries, wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError(f"{path} failed after {max_retries} attempts")

    # GET /coins/markets: price, market cap, volume, supply, ATH (1 call = up to 250 coins)
    def markets(self, per_page):
        return self._get("/coins/markets", {
            "vs_currency": config.VS_CURRENCY,
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "1h,24h,7d",
        })

    # GET /global: total market cap, volume, BTC/ETH dominance
    def global_data(self):
        return self._get("/global")["data"]

    # GET /search/trending: top trending coins in the last 24h
    def trending(self):
        return self._get("/search/trending")["coins"]

    # GET /coins/{id}/market_chart: daily price, market cap, volume
    def market_chart(self, coin_id, days):
        return self._get(f"/coins/{coin_id}/market_chart", {
            "vs_currency": config.VS_CURRENCY,
            "days": days,
            "interval": "daily",
        })
