from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_mcp_adapters.client import MultiServerMCPClient


class MCPToolsProvider:
    """
    Client-side helper for FastMCP servers.
    Returns LangChain tool wrappers (so you can use them in LangGraph).
    """

    def __init__(
        self,
        name: str = "mail",
        url: str = "http://127.0.0.1:8000",
        transport="streamable_http"
    ):
        self.name = name
        self.url = url
        self.transport = transport

        self._client: Optional[MultiServerMCPClient] = None
        self._tools: Optional[List[Any]] = None
        self._tools_by_name: Optional[Dict[str, Any]] = None

    async def connect(self) -> None:
        """Create MCP client connection (once)."""
        if self._client is not None:
            return

        self._client = MultiServerMCPClient(
            {
                self.name: {
                    "url": self.url,
                    "transport": self.transport,
                }
            }
        )

    async def get_tools(self, refresh: bool = False) -> List[Any]:
        """
        Fetch tools from MCP server.
        Returns a list of LangChain tool objects (with .invoke/.ainvoke).
        """
        await self.connect()

        if self._tools is None or refresh:
            self._tools = await self._client.get_tools()  # type: ignore[attr-defined]
            self._tools_by_name = {t.name: t for t in self._tools}

        return self._tools

    async def get_tools_by_name(self, refresh: bool = False) -> Dict[str, Any]:
        """Return tools dict: name -> tool."""
        await self.get_tools(refresh=refresh)
        return dict(self._tools_by_name or {})

    async def get_tool(self, name: str) -> Any:
        """Get one tool by name (raises KeyError if missing)."""
        tools = await self.get_tools_by_name()
        if name not in tools:
            available = ", ".join(sorted(tools.keys()))
            raise KeyError(f"Tool '{name}' not found. Available: {available}")
        return tools[name]

    async def ainvoke_tool(self, name: str, args: Dict[str, Any]) -> Any:
        """Convenience: call tool by name."""
        tool = await self.get_tool(name)
        return await tool.ainvoke(args)
