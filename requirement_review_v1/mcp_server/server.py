"""Minimal MCP server entrypoint (stdio transport).

Run:
    python -m requirement_review_v1.mcp_server.server
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from requirement_review_v1.service.review_service import review_prd_text

mcp = FastMCP("requirement-review-v1")


@mcp.tool()
def ping() -> dict[str, Any]:
    """Health check tool for MCP connectivity."""
    return {"ok": True}


@mcp.tool()
def review_prd(prd_text: str, run_id: str | None = None) -> dict[str, Any]:
    """Run one PRD review and return summary output paths and metrics."""
    summary = review_prd_text(
        prd_text=prd_text,
        run_id=run_id,
        config_overrides={"outputs_root": "outputs"},
    )
    return summary.to_dict()


def main() -> None:
    """Start MCP server over stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
