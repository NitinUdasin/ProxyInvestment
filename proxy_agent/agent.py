from langgraph.graph import StateGraph, START, END

from proxy_agent.state import AgentState, LynchScore
from proxy_agent.filters.lynch import score_lynch
from proxy_agent.nodes import (
    trend_selector,
    value_chain_mapper,
    enabler_finder,
    ticker_validator,
    data_fetcher,
    report_generator,
)


def lynch_scorer(state: AgentState) -> dict:
    """Score every fetched stock against Lynch filters."""
    stock_data = state.get("stock_data", {})
    enabler_set = set(state.get("enablers", []))
    value_chain = state.get("value_chain", {})

    # Build ticker -> is_enabler map from tagged value_chain
    enabler_map: dict[str, bool] = {}
    for companies in value_chain.values():
        for c in companies:
            t = c.get("ticker", "")
            enabler_map[t] = c.get("is_enabler", False)

    lynch_scores: dict[str, LynchScore] = {}
    for ticker, data in stock_data.items():
        is_enabler = ticker in enabler_set or enabler_map.get(ticker, False)
        lynch_scores[ticker] = score_lynch(ticker, data, is_enabler=is_enabler)

    return {"lynch_scores": lynch_scores}


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("trend_selector", trend_selector)
    graph.add_node("value_chain_mapper", value_chain_mapper)
    graph.add_node("enabler_finder", enabler_finder)
    graph.add_node("ticker_validator", ticker_validator)
    graph.add_node("data_fetcher", data_fetcher)
    graph.add_node("lynch_scorer", lynch_scorer)
    graph.add_node("report_generator", report_generator)

    graph.add_edge(START, "trend_selector")
    graph.add_edge("trend_selector", "value_chain_mapper")
    graph.add_edge("value_chain_mapper", "enabler_finder")
    graph.add_edge("enabler_finder", "ticker_validator")
    graph.add_edge("ticker_validator", "data_fetcher")
    graph.add_edge("data_fetcher", "lynch_scorer")
    graph.add_edge("lynch_scorer", "report_generator")
    graph.add_edge("report_generator", END)

    return graph.compile()


# Singleton compiled graph
proxy_graph = build_graph()
