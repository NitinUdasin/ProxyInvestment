import argparse
import pathlib
import sys

# Force UTF-8 on Windows so Rich can render emoji and unicode from Claude's output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

console = Console(force_terminal=True, highlight=False)

VALID_TRENDS = ["AI", "EV", "Renewable Energy", "Quick Commerce", "Defense", "Healthcare"]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Proxy Investment Agent — find NSE enabler stocks in mega trends"
    )
    parser.add_argument(
        "--trend",
        required=True,
        help=f"Mega trend to analyse. Options: {', '.join(VALID_TRENDS)}",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to save the markdown report (e.g. report.md)",
    )
    args = parser.parse_args()

    # Lazy import after env is loaded so API keys are present
    from proxy_agent.agent import proxy_graph
    from proxy_agent.display import (
        print_value_chain,
        print_lynch_table,
        print_report,
        print_step,
    )
    from proxy_agent.excalidraw import save_excalidraw

    console.print(
        f"\n[bold cyan]Proxy Investment Agent[/bold cyan] — "
        f"trend: [bold]{args.trend}[/bold]\n"
    )

    initial_state = {"trend": args.trend, "messages": []}
    final_state = None

    try:
        # Stream with mode="values" so each event is the full accumulated state.
        # The last event is the final state — no second invoke needed.
        for state_snapshot in proxy_graph.stream(initial_state, stream_mode="values"):
            node_keys = [k for k in state_snapshot if k not in initial_state or state_snapshot[k] != initial_state.get(k)]
            if node_keys:
                print_step(node_keys[-1] if node_keys else "...")
            final_state = state_snapshot

    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)

    if final_state is None:
        console.print("[red]Agent produced no output.[/red]")
        sys.exit(1)

    print_value_chain(final_state)
    print_lynch_table(final_state)
    print_report(final_state)

    # Save Excalidraw diagram (open output.excalidraw at excalidraw.com)
    diagram_path = pathlib.Path(args.output).with_suffix(".excalidraw") if args.output else pathlib.Path("output.excalidraw")
    save_excalidraw(final_state, diagram_path)
    console.print(f"[dim]Diagram saved to {diagram_path}[/dim]")

    if args.output:
        report_text = final_state.get("report", "")
        pathlib.Path(args.output).write_text(report_text, encoding="utf-8")
        console.print(f"\n[dim]Report saved to {args.output}[/dim]")
    else:
        report_text = final_state.get("report", "")
        pathlib.Path("output.md").write_text(report_text, encoding="utf-8")
        console.print("\n[dim]Report saved to output.md[/dim]")


if __name__ == "__main__":
    main()
