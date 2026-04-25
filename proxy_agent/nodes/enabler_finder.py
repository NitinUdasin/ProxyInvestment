import json

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from proxy_agent.state import AgentState

_llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)

_SYSTEM = """You are a Peter Lynch-style equity analyst. Your job: find the TRUE PROXY PLAYS.

A proxy enabler is a company that:
1. Supplies multiple players across the value chain (not just one stage)
2. Has recurring demand regardless of which brand/OEM wins
3. Benefits from the overall trend growing, not a single player

Given a value chain, identify which companies qualify as enablers.

Output ONLY valid JSON:
{
  "enablers": ["TICKER1", "TICKER2", ...],
  "reasoning": {
    "TICKER1": "one-line reason why this is an enabler"
  }
}
"""


def enabler_finder(state: AgentState) -> dict:
    """Use Claude to identify proxy enablers from the mapped value chain."""
    value_chain = state["value_chain"]

    if not value_chain:
        return {"enablers": []}

    chain_text = json.dumps(value_chain, indent=2)

    messages = [
        SystemMessage(content=_SYSTEM),
        HumanMessage(
            content=f"Trend: {state['trend']}\n\nValue Chain:\n{chain_text}\n\n"
                    f"Which companies are true proxy enablers? "
                    f"Also consider: who supplies everyone? Who has recurring demand?"
        ),
    ]

    response = _llm.invoke(messages)
    raw = response.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        data = json.loads(raw)
        enablers = data.get("enablers", [])
    except json.JSONDecodeError:
        enablers = []

    # Tag is_enabler in value_chain entries
    enabler_set = set(enablers)
    updated_chain: dict = {}
    for stage, companies in value_chain.items():
        updated_chain[stage] = [
            {**c, "is_enabler": c.get("ticker", "") in enabler_set}
            for c in companies
        ]

    return {"enablers": enablers, "value_chain": updated_chain}
