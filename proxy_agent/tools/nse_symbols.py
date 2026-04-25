"""
Fetches and caches the NSE equity symbol list.
Used to validate / fuzzy-correct tickers before data fetching.

NSE publishes EQUITY_L.csv which lists every NSE-listed symbol.
We cache it locally for 24 hours to avoid hammering NSE on every run.
"""

from __future__ import annotations

import csv
import io
import json
import pathlib
import time
from difflib import get_close_matches
from functools import lru_cache

import requests

_CACHE_FILE = pathlib.Path(__file__).parent.parent.parent / ".nse_symbols_cache.json"
_CACHE_TTL_HOURS = 24
_CSV_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"


def _nse_session() -> requests.Session:
    """Create a session that mimics a browser — NSE requires cookies from the homepage."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.nseindia.com/",
        }
    )
    try:
        # Seed cookies — NSE returns 403 without a prior homepage visit
        session.get("https://www.nseindia.com/", timeout=10)
    except Exception:
        pass
    return session


def _fetch_from_nse() -> dict[str, str]:
    """Download NSE EQUITY_L.csv and return {SYMBOL: NAME} mapping."""
    session = _nse_session()
    resp = session.get(_CSV_URL, timeout=30)
    resp.raise_for_status()

    # NSE CSV may use Windows-1252 encoding
    text = resp.content.decode("windows-1252", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    symbols: dict[str, str] = {}
    for row in reader:
        symbol = (row.get("SYMBOL") or "").strip().upper()
        name = (row.get("NAME OF COMPANY") or "").strip()
        if symbol:
            symbols[symbol] = name
    return symbols


def _load_cache() -> dict[str, str] | None:
    if not _CACHE_FILE.exists():
        return None
    try:
        cache = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        age_hours = (time.time() - cache["timestamp"]) / 3600
        if age_hours < _CACHE_TTL_HOURS:
            return cache["symbols"]
    except Exception:
        pass
    return None


def _save_cache(symbols: dict[str, str]) -> None:
    try:
        _CACHE_FILE.write_text(
            json.dumps({"timestamp": time.time(), "symbols": symbols}),
            encoding="utf-8",
        )
    except Exception:
        pass


@lru_cache(maxsize=1)
def get_nse_symbols() -> dict[str, str]:
    """Return {SYMBOL: COMPANY_NAME} for all NSE-listed equities (cached 24h)."""
    cached = _load_cache()
    if cached:
        return cached

    try:
        symbols = _fetch_from_nse()
        if symbols:
            _save_cache(symbols)
            return symbols
    except Exception as e:
        print(f"[nse_symbols] Could not fetch NSE equity list: {e}")

    # Return empty dict — validation will be skipped gracefully
    return {}


def validate_ticker(ticker: str) -> tuple[str | None, str]:
    """Check if ticker is a valid NSE symbol.

    Returns:
        (corrected_ticker, status) where status is one of:
          "exact"   — ticker found as-is
          "fuzzy"   — close match found, ticker corrected
          "invalid" — no match found
    """
    symbols = get_nse_symbols()
    if not symbols:
        # Can't validate — let it through
        return ticker, "unknown"

    upper = ticker.strip().upper()

    if upper in symbols:
        return upper, "exact"

    # Common LLM aliasing fixes before fuzzy search
    _ALIASES: dict[str, str] = {
        "TATAMOTORS": "TATAMOTORS",   # sometimes NSE lists as TATAMTRDVR
        "MAHINDRA": "M&M",
        "IOCL": "IOC",
        "BHELEC": "BHEL",
        "KECINTL": "KEC",
        "NHAI": None,                  # NHAI InvIT — not equity listed
        "EXICOMTELE": "EXICOM",
        "TATVACHIN": "TATVA",
        "AMARAJABAT": "ARE&M",
        "TVSSCS": "TVSSCL",
        "JBMA": "JBMAAUTO",
    }
    if upper in _ALIASES:
        alias = _ALIASES[upper]
        if alias is None:
            return None, "invalid"
        if alias in symbols:
            return alias, "fuzzy"

    # Difflib fuzzy search over the full symbol list
    matches = get_close_matches(upper, symbols.keys(), n=1, cutoff=0.82)
    if matches:
        return matches[0], "fuzzy"

    return None, "invalid"
