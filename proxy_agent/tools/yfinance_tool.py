from langchain_core.tools import tool
import yfinance as yf


@tool
def fetch_yfinance(ticker: str) -> dict:
    """Fetch key financial fundamentals for an NSE-listed stock using yfinance.

    Args:
        ticker: NSE ticker symbol (e.g. TATAMOTORS, INFY). Do NOT include .NS suffix.

    Returns:
        Dict with pe_ratio, market_cap, debt_to_equity, earnings_growth,
        revenue_growth, current_price, sector.
    """
    info = yf.Ticker(f"{ticker}.NS").info
    return {
        "ticker": ticker,
        "name": info.get("longName", ticker),
        "sector": info.get("sector", ""),
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "peg_ratio": info.get("trailingPegRatio"),
        "earnings_growth": info.get("earningsGrowth"),       # trailing 1yr
        "revenue_growth": info.get("revenueGrowth"),
        "debt_to_equity": info.get("debtToEquity"),
        "return_on_equity": info.get("returnOnEquity"),
        "profit_margins": info.get("profitMargins"),
    }
