from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.markdown import Markdown

from proxy_agent.state import AgentState, LynchScore

console = Console(force_terminal=True, highlight=False)


def _score_color(score: int) -> str:
    if score >= 7:
        return "bold green"
    elif score >= 4:
        return "yellow"
    return "red"


def print_value_chain(state: AgentState) -> None:
    trend = state["trend"]
    value_chain = state.get("value_chain", {})
    enablers = set(state.get("enablers", []))

    console.print()
    console.print(Panel(f"[bold cyan]Value Chain: {trend}[/bold cyan]", box=box.DOUBLE))

    for stage, companies in value_chain.items():
        table = Table(
            title=f"[bold]{stage}[/bold]",
            box=box.SIMPLE_HEAD,
            show_header=True,
            header_style="dim",
        )
        table.add_column("Ticker", style="bold white", width=16)
        table.add_column("Company", width=30)
        table.add_column("Role", width=40)
        table.add_column("Proxy?", width=8)

        for c in companies:
            ticker = c.get("ticker", "")
            is_enabler = ticker in enablers or c.get("is_enabler", False)
            proxy_tag = Text("ENABLER", style="bold green") if is_enabler else Text("", style="dim")
            table.add_row(
                ticker,
                c.get("name", ""),
                c.get("brief_role", ""),
                proxy_tag,
            )

        console.print(table)


def print_lynch_table(state: AgentState) -> None:
    lynch_scores: dict[str, LynchScore] = state.get("lynch_scores", {})
    stock_data = state.get("stock_data", {})
    enablers = set(state.get("enablers", []))

    if not lynch_scores:
        console.print("[dim]No Lynch scores available.[/dim]")
        return

    console.print()
    console.print(Panel("[bold cyan]Lynch Filter Scores[/bold cyan]", box=box.DOUBLE))

    table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold dim")
    table.add_column("Ticker", width=14)
    table.add_column("Name", width=28)
    table.add_column("Score", width=8, justify="center")
    table.add_column("Grade", width=10, justify="center")
    table.add_column("Growth", width=8, justify="center")
    table.add_column("PEG", width=6, justify="center")
    table.add_column("Debt", width=6, justify="center")
    table.add_column("Promoter", width=10, justify="center")
    table.add_column("Runway", width=8, justify="center")
    table.add_column("Proxy?", width=8)

    for ticker, score in sorted(lynch_scores.items(), key=lambda x: -x[1].total):
        data = stock_data.get(ticker, {})
        name = data.get("name", ticker)[:26]
        color = _score_color(score.total)
        is_enabler = ticker in enablers
        proxy_tag = Text("YES", style="bold green") if is_enabler else Text("", style="dim")

        table.add_row(
            ticker,
            name,
            Text(f"{score.total}/10", style=color),
            Text(score.grade, style=color),
            str(score.earnings_growth_score),
            str(score.peg_score),
            str(score.debt_score),
            str(score.promoter_score),
            str(score.runway_score),
            proxy_tag,
        )

    console.print(table)


def print_report(state: AgentState) -> None:
    report = state.get("report", "")
    if not report:
        return
    console.print()
    console.print(Panel("[bold cyan]Investment Report[/bold cyan]", box=box.DOUBLE))
    console.print(Markdown(report))


def print_step(step_name: str) -> None:
    console.print(f"[dim]  running[/dim] [bold]{step_name}[/bold]...")
