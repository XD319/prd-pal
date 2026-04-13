"""Public MCP server entrypoint for prd-pal."""

from requirement_review_v1.mcp_server.server import *  # noqa: F401,F403
from requirement_review_v1.mcp_server.server import main


if __name__ == "__main__":
    main()
