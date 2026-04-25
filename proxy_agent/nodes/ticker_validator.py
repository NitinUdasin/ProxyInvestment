from rich.console import Console

from proxy_agent.state import AgentState
from proxy_agent.tools.nse_symbols import validate_ticker

console = Console(force_terminal=True, highlight=False)


def ticker_validator(state: AgentState) -> dict:
    """Validate every ticker in the value chain against NSE's official equity list.

    - Exact matches pass through unchanged.
    - Close mismatches are auto-corrected (e.g. KECINTL → KEC, IOCL → IOC).
    - Truly invalid tickers are dropped with a console warning.
    - Enablers list is updated to reflect any corrections/removals.
    """
    value_chain = state.get("value_chain", {})
    enablers = state.get("enablers", [])

    corrections: dict[str, str] = {}   # old_ticker -> new_ticker
    dropped: list[str] = []

    updated_chain: dict[str, list[dict]] = {}

    for stage, companies in value_chain.items():
        valid: list[dict] = []
        for c in companies:
            raw_ticker = c.get("ticker", "").strip().upper()
            if not raw_ticker:
                continue

            corrected, status = validate_ticker(raw_ticker)

            if status == "exact" or status == "unknown":
                valid.append(c)

            elif status == "fuzzy" and corrected:
                corrections[raw_ticker] = corrected
                console.print(
                    f"  [yellow]~[/yellow] {raw_ticker} → [green]{corrected}[/green]"
                    f" [dim](auto-corrected)[/dim]"
                )
                valid.append({**c, "ticker": corrected})

            else:  # invalid
                dropped.append(raw_ticker)
                console.print(
                    f"  [red]✗[/red] {raw_ticker} [dim]— not found on NSE, skipping[/dim]"
                )

        if valid:
            updated_chain[stage] = valid

    # Update enablers: apply corrections, drop invalids
    dropped_set = set(dropped)
    updated_enablers = [
        corrections.get(t, t)
        for t in enablers
        if t not in dropped_set and corrections.get(t, t) not in dropped_set
    ]

    if corrections:
        console.print(
            f"\n  [dim]Corrected {len(corrections)} ticker(s), "
            f"dropped {len(dropped)}[/dim]\n"
        )
    elif dropped:
        console.print(f"\n  [dim]Dropped {len(dropped)} invalid ticker(s)[/dim]\n")

    return {"value_chain": updated_chain, "enablers": updated_enablers}
