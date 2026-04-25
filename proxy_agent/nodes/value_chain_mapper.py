import json

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from proxy_agent.state import AgentState
from proxy_agent.tools.search_tool import search_tool

_llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)

_SYSTEM = """You are an expert equity analyst specialising in the Indian stock market (NSE/BSE).
Given web search results, map the full value chain for a mega trend and identify listed Indian companies at each stage.

Value chain stages (use all that apply):
- Raw Material
- Manufacturer
- Component Supplier
- Distributor / Infrastructure
- Service Provider

Output ONLY valid JSON — no markdown, no explanation:
{
  "value_chain": {
    "<stage>": [
      {"ticker": "<NSE_TICKER>", "name": "<Company Name>", "brief_role": "<one line>"}
    ]
  }
}

Rules:
- Only include companies listed on NSE or BSE. Use the NSE ticker (no suffix).
- Include 3–6 companies per stage where possible.
- If a company appears at multiple stages, pick the primary one.
- ticker must be the exact NSE/BSE symbol (e.g. TATAMOTORS, INFY, ADANIGREEN).
"""


def value_chain_mapper(state: AgentState) -> dict:
    """Use web search + Claude to map the value chain for the selected mega trend."""
    trend = state["trend"]
    trend_context = state.get("trend_context", "")

    # Enrich search queries with context if this came from a free-form input
    context_hint = f" {trend_context[:120]}" if trend_context else ""
    queries = [
        f"Indian NSE listed companies {trend} value chain raw material manufacturer 2024{context_hint}",
        f"NSE BSE stocks {trend} component supplier infrastructure service provider India",
        f"proxy plays {trend} India stock market enablers listed companies",
    ]

    search_results = []
    for q in queries:
        try:
            results = search_tool.invoke(q)
            if isinstance(results, list):
                search_results.extend(results)
            else:
                search_results.append(str(results))
        except Exception:
            pass

    context = "\n\n".join(
        r.get("content", str(r)) if isinstance(r, dict) else str(r)
        for r in search_results[:12]
    )

    extra = f"\n\nAdditional context: {trend_context}" if trend_context else ""
    messages = [
        SystemMessage(content=_SYSTEM),
        HumanMessage(
            content=f"Trend: {trend}{extra}\n\nSearch Results:\n{context}\n\n"
                    f"Map the complete value chain with listed Indian NSE companies."
        ),
    ]

    response = _llm.invoke(messages)
    raw = response.content.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        data = json.loads(raw)
        value_chain = data.get("value_chain", {})
    except json.JSONDecodeError:
        # Graceful fallback: return empty chain
        value_chain = {}

    return {"value_chain": value_chain}
