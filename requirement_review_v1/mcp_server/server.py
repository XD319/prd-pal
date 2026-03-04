"""Minimal MCP server entrypoint (stdio transport).

Run:
    python -m requirement_review_v1.mcp_server.server
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("requirement-review-v1")


@mcp.tool()
def ping() -> dict[str, Any]:
    """Health check tool for MCP connectivity."""
    return {"ok": True}


def main() -> None:
    """Start MCP server over stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

