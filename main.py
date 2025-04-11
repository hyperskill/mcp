import httpx
import urllib.parse
from typing import Optional
from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn

from fastmcp import FastMCP

# Global variable to cache the session ID
_session_id: Optional[str] = None

async def fetch_session_id() -> Optional[str]:
    """Fetches the session ID from Hyperskill API and caches it."""
    global _session_id
    # Avoid fetching again if we already have it
    if _session_id:
        return _session_id

    url = "https://hyperskill.org/api/profiles/current"
    headers = {
        "accept": "application/json",
        # It's generally good practice to identify your client with a proper User-Agent
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    }

    try:
        async with httpx.AsyncClient() as client:
            # We don't need the response body, just the cookies, so stream=True might be slightly more efficient
            # but for simplicity, a standard get is fine.
            response = await client.get(url, headers=headers, follow_redirects=True)
            # We don't necessarily need to raise for status, 
            # as a redirect or even a 4xx/5xx might still set cookies, although less likely.
            # response.raise_for_status()

            if "sessionid" in response.cookies:
                _session_id = response.cookies["sessionid"]
                print(f"Obtained and cached session ID: {_session_id[:5]}...") # Print truncated ID for security
                return _session_id
            else:
                print("Failed to obtain session ID from Hyperskill API response cookies.")
                # Check if the response indicates why (e.g., redirect to login?)
                print(f"Status Code: {response.status_code}")
                # print(f"Response Headers: {response.headers}") # Uncomment for detailed debugging
                return None

    except httpx.RequestError as exc:
        print(f"Error fetching session ID: An error occurred while requesting {exc.request.url!r}: {exc}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during session ID fetch: {e}")
        return None

mcp = FastMCP("Hyperskill")

@mcp.tool()
async def find_topics_on_hyperskill(topics: list[str]) -> list[str]:
    """Find topics on Hyperskill"""
    # Assuming the intention is to return a list of formatted strings for each topic found
    # This is just an example fix, the actual logic might be different
    # Call search_hyperskill for each topic and return the target_id of the first result

    results = []
    for topic in topics:
        result = await search_hyperskill(topic)
        if result:
            results.append(result)
    return results

async def search_hyperskill(keyword: str) -> Optional[str]:
    """Searches Hyperskill for a given keyword and returns the target_id of the first result."""
    # Ensure session ID is fetched/refreshed before proceeding (implicitly via get_session_id)
    # await fetch_session_id() # Removed explicit call

    encoded_keyword = urllib.parse.quote_plus(keyword)
    url = f"https://hyperskill.org/api/search-results?query={encoded_keyword}&include_groups=false&include_projects=false&include_users=false"
    
    headers = {"accept": "application/json"}
    # Now awaits fetch_session_id directly
    session_id = await fetch_session_id()
    if session_id:
        headers["Cookie"] = f"sessionid={session_id}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

            response_data = response.json()
            print(f"Search response for keyword '{keyword}': {response_data}") # Optional: for debugging

            search_results = response_data.get("search-results") or response_data.get("search_results")

            if search_results and len(search_results) > 0:
                first_result = search_results[0]
                target_id = first_result.get("target_id")
                if target_id:
                    return str(target_id) # Ensure it's returned as a string

            print(f"No search results found for keyword: {keyword}")
            return None
    except httpx.RequestError as exc:
        print(f"An error occurred while requesting {exc.request.url!r}: {exc}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during search for '{keyword}': {e}")
        # Consider more specific exception handling if needed
        return None

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
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

if __name__ == "__main__":
    mcp_server = mcp._mcp_server
    
    # Create and run Starlette app
    starlette_app = create_starlette_app(mcp_server, debug=True)
    uvicorn.run(starlette_app, host="0.0.0.0", port=8080)