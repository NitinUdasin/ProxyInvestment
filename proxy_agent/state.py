from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


@dataclass
class LynchScore:
    ticker: str
    earnings_growth_score: int = 0   # 0-2
    peg_score: int = 0               # 0-2
    debt_score: int = 0              # 0-2
    promoter_score: int = 0          # 0-2
    runway_score: int = 0            # 0-2

    @property
    def total(self) -> int:
        return (
            self.earnings_growth_score
            + self.peg_score
            + self.debt_score
            + self.promoter_score
            + self.runway_score
        )

    @property
    def grade(self) -> str:
        if self.total >= 7:
            return "STRONG"
        elif self.total >= 4:
            return "MODERATE"
        return "WEAK"


class AgentState(TypedDict):
    trend: str
    # Claude's interpretation of the original user input (set when input is free-form).
    # Downstream nodes use this for richer context when searching/prompting.
    trend_context: str
    # stage -> list of {ticker, name, stage, brief_role, is_enabler}
    value_chain: dict[str, list[dict]]
    enablers: list[str]                      # NSE tickers flagged as proxy enablers
    stock_data: dict[str, dict]              # ticker -> raw fundamentals
    lynch_scores: dict[str, LynchScore]      # ticker -> scored result
    report: str
    messages: Annotated[list[BaseMessage], add_messages]
