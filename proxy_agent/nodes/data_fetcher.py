from proxy_agent.state import AgentState
from proxy_agent.tools.yfinance_tool import fetch_yfinance
from proxy_agent.tools.screener_tool import fetch_screener


def data_fetcher(state: AgentState) -> dict:
    """Fetch yfinance + screener.in data for every company in the value chain."""
    value_chain = state["value_chain"]

    # Collect unique tickers
    all_companies: dict[str, dict] = {}
    for companies in value_chain.values():
        for c in companies:
            ticker = c.get("ticker", "").strip().upper()
            if ticker:
                all_companies[ticker] = c

    stock_data: dict[str, dict] = {}
    for ticker, meta in all_companies.items():
        merged: dict = {"ticker": ticker, "name": meta.get("name", ticker)}

        # yfinance
        try:
            yf_data = fetch_yfinance.invoke({"ticker": ticker})
            if isinstance(yf_data, dict) and "error" not in yf_data:
                merged.update(yf_data)
        except Exception as e:
            merged["yfinance_error"] = str(e)

        # screener.in
        try:
            sc_data = fetch_screener.invoke({"ticker": ticker})
            if isinstance(sc_data, dict) and "error" not in sc_data:
                merged.update(sc_data)
        except Exception as e:
            merged["screener_error"] = str(e)

        stock_data[ticker] = merged

    return {"stock_data": stock_data}
