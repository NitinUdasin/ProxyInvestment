"""
Scraper for screener.in — extracts:
  - PE ratio, Debt/Equity, ROE, ROCE  (from top-ratios widget)
  - Compounded Profit Growth 3yr / 5yr (from sub-table inside P&L section)
  - Promoter holding %                 (from Shareholding Pattern section)
  - Debt/Equity fallback               (computed from Balance Sheet if missing above)
"""

import re
from functools import lru_cache

import requests
from bs4 import BeautifulSoup, Tag
from langchain_core.tools import tool

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_number(text: str | None) -> float | None:
    """Return the first number (int or float, possibly negative) in a string."""
    if not text:
        return None
    clean = text.strip().replace(",", "").replace("%", "")
    m = re.search(r"-?\d+\.?\d*", clean)
    return float(m.group()) if m else None


def _latest(cells: list[Tag]) -> float | None:
    """Return the last non-None number across a list of <td> cells."""
    values = [_parse_number(c.get_text()) for c in cells]
    non_null = [v for v in values if v is not None]
    return non_null[-1] if non_null else None


@lru_cache(maxsize=256)
def _fetch_html(ticker: str) -> str:
    url = f"https://www.screener.in/company/{ticker.upper()}/"
    resp = requests.get(url, headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


# ── Section finders ───────────────────────────────────────────────────────────

def _find_section(soup: BeautifulSoup, *keywords: str) -> Tag | None:
    """Return the first <section> whose heading contains ALL keywords."""
    for section in soup.find_all("section"):
        h = section.find(["h2", "h3"])
        if h:
            txt = h.get_text(strip=True)
            if all(k in txt for k in keywords):
                return section
    return None


# ── Parsers ───────────────────────────────────────────────────────────────────

def _parse_top_ratios(soup: BeautifulSoup) -> dict:
    result: dict = {}
    ratios_div = soup.find(id="top-ratios")
    if not ratios_div:
        return result
    for li in ratios_div.find_all("li"):
        name_tag = li.find("span", class_="name")
        num_tag  = li.find("span", class_="number")
        if not (name_tag and num_tag):
            continue
        label = name_tag.get_text(strip=True)
        value = _parse_number(num_tag.get_text(strip=True))
        if "P/E" in label:
            result["pe_ratio_screener"] = value
        elif "Debt / Eq" in label or "Debt/Eq" in label:
            result["debt_to_equity_screener"] = value
        elif "ROE" in label:
            result["roe"] = value
        elif "ROCE" in label:
            result["roce"] = value
        elif "Dividend Yield" in label:
            result["dividend_yield"] = value
    return result


def _parse_profit_growth(soup: BeautifulSoup) -> dict:
    """Find the 'Compounded Profit Growth' sub-table inside the P&L section."""
    result: dict = {}
    pl_section = _find_section(soup, "Profit", "Loss")
    if not pl_section:
        return result

    for table in pl_section.find_all("table"):
        rows = table.find_all("tr")
        for i, row in enumerate(rows):
            th = row.find("th")
            if th and "Compounded Profit" in th.get_text():
                # Subsequent rows: [label_td, value_td]
                for j in range(i + 1, min(i + 7, len(rows))):
                    next_row = rows[j]
                    # Stop if we hit the next <th> header
                    if next_row.find("th"):
                        break
                    cells = next_row.find_all("td")
                    if len(cells) < 2:
                        continue
                    label = cells[0].get_text(strip=True)
                    value = _parse_number(cells[1].get_text())
                    if value is None:
                        continue
                    if "3 Year" in label:
                        result["eps_cagr_3yr"] = value
                    elif "5 Year" in label:
                        result["eps_cagr_5yr"] = value
                    elif "10 Year" in label:
                        result["eps_cagr_10yr"] = value
                return result   # found the block, done

    return result


def _parse_promoter(soup: BeautifulSoup) -> dict:
    """Extract latest promoter holding % from the Shareholding Pattern section."""
    result: dict = {}
    section = _find_section(soup, "Shareholding")
    if not section:
        return result

    for row in section.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue
        label = cells[0].get_text(strip=True)
        # Match "Promoters", "Promoters+", "Promoter & Promoter Group", etc.
        if re.match(r"Promoter", label, re.IGNORECASE):
            # Take the most recent (last) quarterly value
            val = _latest(cells[1:])
            if val is not None:
                result["promoter_holding"] = val
            break   # first matching row is the quarterly table; don't re-match annual

    return result


def _parse_debt_from_balance_sheet(soup: BeautifulSoup) -> dict:
    """Fallback: compute D/E from Balance Sheet borrowings and equity."""
    result: dict = {}
    section = _find_section(soup, "Balance Sheet")
    if not section:
        return result

    borrowings: float | None = None
    equity: float | None = None
    reserves: float | None = None

    for row in section.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            cells = row.find_all("th")
        if not cells:
            continue
        label = cells[0].get_text(strip=True)
        if re.search(r"Borrowing", label, re.IGNORECASE):
            borrowings = _latest(cells[1:])
        elif re.search(r"Equity Capital", label, re.IGNORECASE):
            equity = _latest(cells[1:])
        elif re.search(r"Reserves", label, re.IGNORECASE):
            reserves = _latest(cells[1:])

    if borrowings is not None and equity is not None:
        total_equity = (equity or 0) + (reserves or 0)
        if total_equity > 0:
            result["debt_to_equity_screener"] = round(borrowings / total_equity, 2)

    return result


# ── Main entry ────────────────────────────────────────────────────────────────

def _scrape(ticker: str) -> dict:
    html = _fetch_html(ticker)
    soup = BeautifulSoup(html, "html.parser")

    result: dict = {"ticker": ticker}
    result.update(_parse_top_ratios(soup))
    result.update(_parse_profit_growth(soup))
    result.update(_parse_promoter(soup))

    # D/E fallback: compute from Balance Sheet if top-ratios didn't have it
    if "debt_to_equity_screener" not in result:
        result.update(_parse_debt_from_balance_sheet(soup))

    return result


@tool
def fetch_screener(ticker: str) -> dict:
    """Scrape Screener.in for EPS CAGR, promoter holding, and debt ratio for an NSE stock.

    Args:
        ticker: NSE ticker symbol (e.g. TATAMOTORS, INFY).

    Returns:
        Dict with eps_cagr_3yr, eps_cagr_5yr, promoter_holding, debt_to_equity_screener,
        pe_ratio_screener, roe, roce.
    """
    try:
        return _scrape(ticker)
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}
