from typing import Dict, Any
from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn

from fastmcp import FastMCP
from hyperskill_api import HyperskillAPI

# Create an instance of the HyperskillAPI class
hyperskill_api = HyperskillAPI()

mcp = FastMCP("Hyperskill")


@mcp.tool()
async def explain_topics_in_the_code(topics: list[str], programming_language: str) -> list[Dict[str, Any]]:
    """Explain topics in the code

    Args:
        topics: List of key topics (or concepts) the user needs to understand to fully grasp given code. Use Hyperskill-compatible topic names like: "for loop", "list comprehensions", "lambda expressions", "decorators", "file I/O", "context managers", etc. Be precise. Avoid duplicates. Avoid overly broad or generic topics.
        programming_language: Programming language of the given code.
    Returns:
        List of dictionaries containing topic id, title, url, hierarchy and clickable link
    """
    topics_details = await find_topics_on_hyperskill(topics, programming_language)
    return topics_details

@mcp.tool()
async def find_topics_on_hyperskill(topics: list[str], programming_language: str) -> list[Dict[str, Any]]:
    """Find topics on Hyperskill and return their details

    Args:
        topics: List of topic keywords to search for. Use Hyperskill-compatible topic names like: "for loop", "list comprehensions", "lambda expressions", "decorators", "file I/O", "context managers", etc. Be precise. Avoid duplicates. Avoid overly broad or generic topics.
        programming_language: Programming language to filter topics by.
    Returns:
        List of dictionaries containing topic id, title, url, hierarchy and clickable link
    """
    return await hyperskill_api.find_topics(topics, programming_language)


# Create Starlette application with SSE transport
def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can serve the provided mcp server with SSE."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/", endpoint=lambda request: PlainTextResponse("Hello from Hyperskill MCP!")),
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

if __name__ == "__main__":
    mcp_server = mcp._mcp_server

    # Create and run Starlette app
    starlette_app = create_starlette_app(mcp_server, debug=True)
    uvicorn.run(starlette_app, host="0.0.0.0", port=8080)
