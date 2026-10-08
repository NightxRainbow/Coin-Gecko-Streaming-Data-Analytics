"""Central configuration. Values come from environment variables / .env file."""
import os

from dotenv import load_dotenv

load_dotenv()

# --- CoinGecko (Demo plan) ---
API_BASE_URL = "https://api.coingecko.com/api/v3"
API_KEY = os.getenv("COINGECKO_API_KEY", "")
VS_CURRENCY = "usd"
REQUEST_PAUSE_SECONDS = 2.5  # polite delay between history calls

# --- Pipeline scope ---
TOP_N_COINS = min(int(os.getenv("TOP_N_COINS", 100)), 250)  # /coins/markets max per page = 250
HISTORY_COINS = int(os.getenv("HISTORY_COINS", 20))  # coins that get daily history
HISTORY_DAYS = 365  # Demo plan only allows the past 365 days

# --- PostgreSQL ---
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "dbname": os.getenv("POSTGRES_DB", "crypto_analytics"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}
