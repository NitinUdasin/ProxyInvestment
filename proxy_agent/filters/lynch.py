from proxy_agent.state import LynchScore


def score_lynch(ticker: str, stock_data: dict, is_enabler: bool = False) -> LynchScore:
    """Score a stock on Peter Lynch's key filters. Returns LynchScore with total 0–10."""
    score = LynchScore(ticker=ticker)

    # 1. Earnings Growth — prefer 15–25% EPS CAGR (sweet spot Lynch called "fast growers")
    eps_cagr = stock_data.get("eps_cagr_3yr") or stock_data.get("eps_cagr_5yr")
    if eps_cagr is None:
        # Fallback to yfinance earnings_growth (1yr, %)
        yf_growth = stock_data.get("earnings_growth")
        eps_cagr = (yf_growth * 100) if yf_growth is not None else None

    if eps_cagr is not None:
        if 15 <= eps_cagr <= 30:
            score.earnings_growth_score = 2
        elif 10 <= eps_cagr < 15 or 30 < eps_cagr <= 40:
            score.earnings_growth_score = 1

    # 2. PEG Ratio — Lynch's favourite: PEG < 1 means stock is cheap relative to growth
    peg = stock_data.get("peg_ratio")
    if peg is None:
        pe = stock_data.get("pe_ratio_screener") or stock_data.get("pe_ratio")
        growth = eps_cagr
        if pe and growth and growth > 0:
            peg = pe / growth

    if peg is not None:
        if 0 < peg < 1:
            score.peg_score = 2
        elif 1 <= peg < 1.5:
            score.peg_score = 1

    # 3. Low Debt — Lynch avoided high-debt companies
    de = stock_data.get("debt_to_equity_screener") or stock_data.get("debt_to_equity")
    if de is not None:
        # yfinance reports D/E as percentage (e.g. 45.2 means 0.452)
        # screener.in reports as ratio (e.g. 0.45)
        # Normalise: if value > 5 assume it's in % form
        if de > 5:
            de = de / 100
        if de < 0.5:
            score.debt_score = 2
        elif de < 1.0:
            score.debt_score = 1

    # 4. Promoter / Insider Holding
    promoter = stock_data.get("promoter_holding")
    if promoter is not None:
        if promoter >= 50:
            score.promoter_score = 2
        elif promoter >= 40:
            score.promoter_score = 1

    # 5. Expansion Runway — is this company an enabler (supplies everyone)?
    if is_enabler:
        score.runway_score = 2
    elif stock_data:  # company is at least in the value chain
        score.runway_score = 1

    return score
