import json

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from proxy_agent.state import AgentState

# Known trends — fast path, no LLM needed
_KNOWN = {
    "AI": "AI",
    "ARTIFICIAL INTELLIGENCE": "AI",
    "EV": "EV",
    "ELECTRIC VEHICLE": "EV",
    "ELECTRIC VEHICLES": "EV",
    "RENEWABLE": "Renewable Energy",
    "RENEWABLE ENERGY": "Renewable Energy",
    "SOLAR": "Renewable Energy",
    "QUICK COMMERCE": "Quick Commerce",
    "QCOMMERCE": "Quick Commerce",
    "Q-COMMERCE": "Quick Commerce",
    "DEFENSE": "Defense",
    "DEFENCE": "Defense",
    "HEALTHCARE": "Healthcare",
    "HEALTH": "Healthcare",
    "PHARMA": "Healthcare",
}

_llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)

_SYSTEM = """You are an equity research analyst specialising in the Indian stock market.

The user has given a free-form investment theme or macro event. Your job:
1. Understand the investment angle (what sectors/companies benefit)
2. Derive a short, clean trend label (3-5 words max)
3. Write a one-paragraph context explaining which Indian NSE sectors and types of companies are likely to benefit, and why

Output ONLY valid JSON, no markdown:
{
  "trend": "<short trend label>",
  "trend_context": "<one paragraph: which Indian sectors/companies benefit and why>"
}
"""


def _interpret_with_claude(raw_input: str) -> dict:
    messages = [
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=f'User input: "{raw_input}"'),
    ]
    response = _llm.invoke(messages)
    text = response.content.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def trend_selector(state: AgentState) -> dict:
    """Normalise the trend input. Known trends are matched instantly.
    Free-form inputs (e.g. 'infra boom after Iran war') are interpreted by Claude,
    which derives a clean trend label and sector context for downstream nodes.
    """
    raw = state.get("trend", "").strip()
    normalized = _KNOWN.get(raw.upper())

    if normalized:
        # Fast path — known trend, no LLM call needed
        return {"trend": normalized, "trend_context": ""}

    # Slow path — free-form input, ask Claude to interpret
    result = _interpret_with_claude(raw)
    return {
        "trend": result.get("trend", raw),
        "trend_context": result.get("trend_context", ""),
    }
