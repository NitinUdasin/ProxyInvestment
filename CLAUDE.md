# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install / sync dependencies
uv sync

# Run the agent
uv run python main.py --trend EV
uv run python main.py --trend "Renewable Energy" --output report.md

# Run tests
uv run pytest tests/ -v

# Run a single test file
uv run pytest tests/test_lynch.py -v

# Add a dependency
uv add <package>
uv add --dev <package>   # dev/test only
```

## Environment Setup

Copy `.env.example` to `.env` and fill in:
- `ANTHROPIC_API_KEY` — for Claude (claude-sonnet-4-6)
- `TAVILY_API_KEY` — for web search in value chain mapping

## Architecture

This is a **LangGraph pipeline agent** implementing the Proxy Investment framework for Indian NSE/BSE stocks. The agent finds "enabler" companies that benefit from a mega trend regardless of which brand wins.

### Graph Flow (proxy_agent/agent.py)

```
trend_selector → value_chain_mapper → enabler_finder → ticker_validator → data_fetcher → lynch_scorer → report_generator
```

Each step is a LangGraph node. The compiled graph is `proxy_graph` in `proxy_agent/agent.py`.

### Key Modules

- **`proxy_agent/state.py`** — `AgentState` (TypedDict) and `LynchScore` (dataclass). State flows through the entire graph.
- **`proxy_agent/nodes/`** — One file per graph node. Nodes take `AgentState` and return a partial state dict.
  - `trend_selector` — normalises input ("ev" → "EV"); uses Claude for free-form inputs
  - `value_chain_mapper` — Claude + Tavily search → structured value chain JSON
  - `enabler_finder` — Claude identifies cross-stage proxy enablers
  - `ticker_validator` — validates every ticker against NSE's equity list (EQUITY_L.csv); auto-corrects fuzzy mismatches, drops truly invalid tickers
  - `data_fetcher` — fetches yfinance + screener.in data for every ticker
  - `report_generator` — Claude writes the final investment narrative
- **`proxy_agent/tools/nse_symbols.py`** — downloads and caches NSE's `EQUITY_L.csv` (24h TTL in `.nse_symbols_cache.json`). `validate_ticker(ticker)` returns `(corrected, status)` where status is `"exact"`, `"fuzzy"`, or `"invalid"`.
- **`proxy_agent/filters/lynch.py`** — `score_lynch(ticker, data, is_enabler)` — purely deterministic scoring, 0–10. All Lynch filter logic lives here.
- **`proxy_agent/tools/`** — LangChain `@tool` wrappers:
  - `yfinance_tool.py` — appends `.NS`, calls `yf.Ticker().info`
  - `screener_tool.py` — scrapes screener.in, `lru_cache` on raw HTML to avoid duplicate requests
  - `search_tool.py` — `TavilySearchResults` instance

### Lynch Scoring (0–10)

| Filter | 2 pts | 1 pt | 0 pts |
|---|---|---|---|
| Earnings Growth | EPS CAGR 15–30% | 10–15% or 30–40% | else |
| PEG Ratio | < 1 | 1–1.5 | else |
| Debt (D/E) | < 0.5 | 0.5–1.0 | else |
| Promoter Holding | > 50% | 40–50% | else |
| Expansion Runway | is_enabler=True | in value chain | else |

Grade: STRONG ≥ 7, MODERATE 4–6, WEAK < 4.

### Data Sources

- **yfinance**: PE, market cap, D/E, trailing earnings growth. NSE tickers get `.NS` appended automatically.
- **screener.in**: EPS CAGR 3yr/5yr, promoter holding %, D/E ratio. Results are `lru_cache`d per session.
- **Tavily**: Web search used in `value_chain_mapper` to discover Indian listed companies per stage.

### Display (proxy_agent/display.py)

Uses `rich` for terminal output. Three print functions: `print_value_chain`, `print_lynch_table`, `print_report`. Call them in sequence after `proxy_graph.invoke()`.

### Excalidraw Diagram (proxy_agent/excalidraw.py)

`build_elements(state)` — generates Excalidraw element dicts from AgentState (swimlane by stage, colour-coded by enabler/Lynch score).
`save_excalidraw(state, path)` — saves a `.excalidraw` file importable at excalidraw.com. Called automatically by `main.py` after each run; output goes to `output.excalidraw` by default.
