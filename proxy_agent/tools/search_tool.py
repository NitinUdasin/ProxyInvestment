from __future__ import annotations
from langchain_core.tools import BaseTool


def _make_search_tool() -> BaseTool:
    from langchain_tavily import TavilySearch
    return TavilySearch(max_results=6)


class _LazySearchTool:
    """Wraps TavilySearch so it is only instantiated when first called (requires API key)."""

    def __init__(self) -> None:
        self._tool: BaseTool | None = None

    def _get(self) -> BaseTool:
        if self._tool is None:
            self._tool = _make_search_tool()
        return self._tool

    def invoke(self, input, **kwargs):  # noqa: ANN001
        return self._get().invoke(input, **kwargs)

    def __call__(self, *args, **kwargs):
        return self._get()(*args, **kwargs)


search_tool = _LazySearchTool()
