# ProxyInvestment

A LangGraph-based agent that implements the **Proxy Investment framework** for Indian NSE/BSE stocks — find the enablers that win regardless of which brand dominates a mega trend.

## The Framework

```
Step 1: Pick a Mega Trend     AI · EV · Renewable Energy · Quick Commerce · Defense · Healthcare
Step 2: Map the Value Chain   Raw Material → Manufacturer → Component Supplier → Infra → Service
Step 3: Find Enablers         Who supplies everyone? Who wins regardless of brand?
Step 4: Apply Lynch Filters   Growth · PEG · Debt · Promoter Holding · Expansion Runway
```

Instead of betting on which EV brand wins, find the wire harness maker supplying all of them.

## Agent Pipeline

```
trend_selector → value_chain_mapper → enabler_finder → data_fetcher → lynch_scorer → report_generator
```

| Node | What it does |
|---|---|
| `trend_selector` | Normalises input ("ev" → "EV") |
| `value_chain_mapper` | Claude + Tavily web search → structured value chain with NSE tickers |
| `enabler_finder` | Claude identifies cross-stage proxy enablers |
| `data_fetcher` | Fetches yfinance + screener.in fundamentals for every company |
| `lynch_scorer` | Deterministic Lynch scoring (0–10) |
| `report_generator` | Claude writes final investment narrative |

## Setup

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/)

```bash
git clone <repo>
cd ProxyInvestment
uv sync
cp .env.example .env
```

Edit `.env`:
```
ANTHROPIC_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here
```

Get keys: [Anthropic Console](https://console.anthropic.com) · [Tavily](https://tavily.com)

## Usage

```bash
uv run python main.py --trend EV
uv run python main.py --trend "Alcoholic Beverages"
uv run python main.py --trend Defense --output report.md
```

**Supported trends:** `AI`, `EV`, `Renewable Energy`, `Quick Commerce`, `Defense`, `Healthcare`

**Output:**
1. Value chain table with enablers highlighted
2. Lynch score table (color-coded: green ≥7, yellow 4–6, red <4)
3. Investment narrative with ranked proxy plays and risks

## Lynch Scoring (0–10)

| Filter | 2 pts | 1 pt |
|---|---|---|
| Earnings Growth | EPS CAGR 15–30% | 10–15% or 30–40% |
| PEG Ratio | < 1 | 1–1.5 |
| Debt (D/E) | < 0.5 | 0.5–1.0 |
| Promoter Holding | > 50% | 40–50% |
| Expansion Runway | Enabler (supplies everyone) | In value chain |

## Data Sources

- **yfinance** — PE, market cap, debt, earnings growth (NSE tickers via `.NS` suffix)
- **screener.in** — EPS CAGR 3yr/5yr, promoter holding % (scraped, session-cached)
- **Tavily** — web search for value chain research

## Development

```bash
# Run tests
uv run pytest tests/ -v

# Add a dependency
uv add <package>
```

## How to conver Mark down to word 
```

pandoc output.md -o output.docx

pandoc scuttlebutt_report.md -o scuttlebutt_report.docx

pandoc phillipfisher.md -o phillipfisher.docx

```