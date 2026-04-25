from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from proxy_agent.state import AgentState, LynchScore

_llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0.3)

_SYSTEM = """You are a seasoned equity analyst writing a concise investment note for a retail investor.
Style: clear, direct, no jargon. Think Peter Lynch — plain English, story-driven.

Structure your report as:
1. **The Trend** — why this mega trend matters now (2–3 sentences)
2. **The Proxy Logic** — why investing in enablers beats picking winners
3. **Top Proxy Plays** — top 5 ranked companies with 1-line investment thesis each
4. **Watch Out For** — 2–3 key risks
"""


def _format_scores(lynch_scores: dict[str, LynchScore], enablers: list[str]) -> str:
    rows = []
    for ticker, score in sorted(lynch_scores.items(), key=lambda x: -x[1].total):
        flag = "[ENABLER]" if ticker in enablers else ""
        rows.append(
            f"{ticker} {flag}: {score.total}/10 ({score.grade}) | "
            f"Growth:{score.earnings_growth_score} PEG:{score.peg_score} "
            f"Debt:{score.debt_score} Promoter:{score.promoter_score} "
            f"Runway:{score.runway_score}"
        )
    return "\n".join(rows)


def report_generator(state: AgentState) -> dict:
    """Generate final investment narrative with Claude."""
    lynch_scores = state.get("lynch_scores", {})
    enablers = state.get("enablers", [])
    trend = state["trend"]
    trend_context = state.get("trend_context", "")
    stock_data = state.get("stock_data", {})

    scores_text = _format_scores(lynch_scores, enablers)

    # Build company context
    company_context = []
    for ticker, data in stock_data.items():
        score = lynch_scores.get(ticker)
        line = (
            f"{ticker} ({data.get('name', ticker)}): "
            f"PE={data.get('pe_ratio_screener') or data.get('pe_ratio', 'N/A')}, "
            f"EPS_CAGR_3yr={data.get('eps_cagr_3yr', 'N/A')}%, "
            f"D/E={data.get('debt_to_equity_screener') or data.get('debt_to_equity', 'N/A')}, "
            f"Promoter={data.get('promoter_holding', 'N/A')}%, "
            f"Lynch={score.total if score else 'N/A'}/10"
        )
        company_context.append(line)

    context_line = f"\nTheme context: {trend_context}\n" if trend_context else ""
    messages = [
        SystemMessage(content=_SYSTEM),
        HumanMessage(
            content=(
                f"Trend: {trend}\n{context_line}\n"
                f"Identified Enablers: {', '.join(enablers) or 'None'}\n\n"
                f"Lynch Scores (sorted by score):\n{scores_text}\n\n"
                f"Company Fundamentals:\n" + "\n".join(company_context)
            )
        ),
    ]

    response = _llm.invoke(messages)
    return {"report": response.content}
