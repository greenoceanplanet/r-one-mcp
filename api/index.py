"""Vercel 진입점. 모든 요청을 FastMCP Streamable HTTP 앱(/mcp)으로 넘긴다."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from r_one_mcp.server import build_http_app  # noqa: E402

_mcp_app = build_http_app(path="/mcp")


async def app(scope, receive, send):
    # vercel.json의 rewrite 때문에 앱에 들어오는 경로가 원래 주소(/mcp)와 다를 수 있다
    # (예: /api/index). 이 함수는 MCP 하나만 서비스하므로 HTTP 요청은 모두 /mcp로 맞춘다.
    if scope["type"] == "http":
        scope = {**scope, "path": "/mcp", "raw_path": b"/mcp"}
    await _mcp_app(scope, receive, send)
