from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.agents.CaseOrchestratorAgent.utils.mcp_tools_provider import MCPToolsProvider


@dataclass(frozen=True)
class McpMailConfig:
    name: str = "mail"
    url: str = "http://127.0.0.1:8000/mcp"
    transport: str = "http"
    tool_name: str = "email_smtp_send"


def _ensure_re_prefix(subject: str, *, default: str = "Your request") -> str:
    s = (subject or "").strip()
    if not s:
        s = default
    return s if s.lower().startswith("re:") else f"Re: {s}"


async def send_email_via_mcp(
    *,
    to_email: str,
    subject: str,
    body: str,
    mcp_config: Optional[McpMailConfig] = None,
) -> Dict[str, Any]:
    """
    Send an email using MCP tool: email_smtp_send.

    Returns the MCP tool response dict.
    Raises exceptions if MCP call fails.
    """
    if not to_email or "@" not in to_email:
        raise ValueError("to_email is missing or invalid")
    if not body or not body.strip():
        raise ValueError("body is required")

    cfg = mcp_config or McpMailConfig()


    mcp_tools = MCPToolsProvider(
        name=cfg.name,
        url=cfg.url,
        transport=cfg.transport,
    )

    final_subject = _ensure_re_prefix(subject)

    payload = {
        "to": to_email,
        "subject": final_subject,
        "body": body,
    }

    res = await mcp_tools.ainvoke_tool(cfg.tool_name, payload)
    return res
