import httpx
import urllib.parse
import logging
from typing import Optional, List, Dict, Any

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class HyperskillAPI:
    """Class that encapsulates all interactions with the Hyperskill API."""

    def __init__(self):
        """Initialize the HyperskillAPI class."""
        self._session_id: Optional[str] = None
        self._base_url = "https://hyperskill.org/api"
        self._default_headers = {
            "accept": "application/json",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        }
        # Set up logger
        self.logger = logging.getLogger(__name__)

    async def _make_request(
        self, url: str, 
        method: str = "GET", 
        headers: Optional[Dict[str, str]] = None, 
        params: Optional[Dict[str, Any]] = None, 
        data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make a request to the Hyperskill API with error handling.

        Args:
            url: The URL to make the request to
            method: The HTTP method to use (GET, POST, etc.)
            headers: Additional headers to include in the request
            params: Query parameters to include in the request
            data: Data to include in the request body

        Returns:
            The JSON response from the API or None if the request failed
        """
        request_headers = self._default_headers.copy()
        if headers:
            request_headers.update(headers)

        session_id = await self.get_session_id()
        if session_id:
            request_headers["Cookie"] = f"sessionid={session_id}"

        try:
            async with httpx.AsyncClient() as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=request_headers, params=params, follow_redirects=True)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=request_headers, params=params, json=data, follow_redirects=True)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response.json()
        except httpx.RequestError as exc:
            self.logger.error(f"Error making request: An error occurred while requesting {exc.request.url!r}: {exc}")
            return None
        except httpx.HTTPStatusError as exc:
            self.logger.error(f"HTTP error occurred: {exc.response.status_code} {exc.response.reason_phrase} for URL {exc.request.url!r}")
            return None
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during API request: {e}")
            return None

    async def get_session_id(self) -> Optional[str]:
        """Fetches the session ID from Hyperskill API and caches it.

        Returns:
            The session ID or None if it couldn't be fetched
        """
        # Avoid fetching again if we already have it
        if self._session_id:
            return self._session_id

        url = f"{self._base_url}/profiles/current"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self._default_headers, follow_redirects=True)

                if "sessionid" in response.cookies:
                    self._session_id = response.cookies["sessionid"]
                    self.logger.info(f"Obtained and cached session ID: {self._session_id[:5]}...") # Print truncated ID for security
                    return self._session_id
                else:
                    self.logger.warning("Failed to obtain session ID from Hyperskill API response cookies.")
                    self.logger.warning(f"Status Code: {response.status_code}")
                    return None

        except httpx.RequestError as exc:
            self.logger.error(f"Error fetching session ID: An error occurred while requesting {exc.request.url!r}: {exc}")
            return None
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during session ID fetch: {e}")
            return None

    async def get_search_results(self, keyword: str) -> Optional[str]:
        """Searches Hyperskill for a given keyword and returns the target_id of the first result.

        Args:
            keyword: The keyword to search for

        Returns:
            The target_id of the first result or None if no results were found
        """
        encoded_keyword = urllib.parse.quote_plus(keyword)
        url = f"{self._base_url}/search-results"
        params = {
            "query": encoded_keyword,
            "include_groups": "false",
            "include_projects": "false",
            "include_users": "false"
        }

        response_data = await self._make_request(url, params=params)

        if not response_data:
            self.logger.warning(f"No search results found for keyword: {keyword}")
            return None

        self.logger.debug(f"Search response for keyword '{keyword}': {response_data}") # Detailed debugging info

        search_results = response_data.get("search-results") or response_data.get("search_results")

        if search_results and len(search_results) > 0:
            first_result = search_results[0]
            target_id = first_result.get("target_id")
            if target_id:
                self.logger.info(f"Found target_id {target_id} for keyword: {keyword}")
                return str(target_id) # Ensure it's returned as a string

        self.logger.warning(f"No search results found for keyword: {keyword}")
        return None

    async def get_topics(self, topic_ids: List[str]) -> Optional[List[Dict[str, Any]]]:
        """Fetches detailed information about topics from the Hyperskill API.

        Args:
            topic_ids: A list of topic IDs to fetch details for

        Returns:
            A dictionary containing the topic details or None if the request fails
        """
        if not topic_ids:
            return None

        # Convert list of IDs to comma-separated string
        ids_param = ",".join(topic_ids)
        url = f"{self._base_url}/topics"
        params = {"ids": ids_param}

        response = await self._make_request(url, params=params)
        if response and "topics" in response:
            return response["topics"]
        else:
            return None

    async def get_topics_titles(self, topic_ids: List[str]) -> Dict[str, str]:
        """Fetches titles for parent topic IDs.

        Args:
            topic_ids: List of parent topic IDs

        Returns:
            Dictionary mapping topic IDs to their titles
        """
        if not topic_ids:
            return {}

        # Fetch details for all parent topics
        topics = await self.get_topics(topic_ids)

        # Create a mapping of ID to title
        parent_map = {}
        if topics:
            for topic in topics:
                parent_map[str(topic["id"])] = topic["title"]

        return parent_map

    async def find_topics(self, topics: List[str], programming_language: str) -> List[Dict[str, Any]]:
        """Find topics on Hyperskill and return their details

        Args:
            topics: List of topic keywords to search for
            programming_language: Programming language to filter topics by

        Returns:
            List of dictionaries containing topic id, title, url, hierarchy and clickable link
        """
        # First find the topic IDs
        topic_ids = []
        for topic in topics:
            result = await self.get_search_results(topic + " " + programming_language)
            if result:
                topic_ids.append(result)

        # If no topics found, return empty list
        if not topic_ids:
            return []

        # Fetch details for all found topics
        topics = await self.get_topics(topic_ids)

        # Extract relevant information
        if topics:
            result = []

            # Collect all parent topic IDs for batch fetching
            all_parent_ids = []
            for topic in topics:
                if "hierarchy" in topic and topic["hierarchy"]:
                    all_parent_ids.extend([str(id) for id in topic["hierarchy"]])

            # Fetch parent topic titles in one batch request
            parent_topic_map = await self.get_topics_titles(list(set(all_parent_ids)))

            for topic in topics:
                # Create hierarchy string if hierarchy exists
                hierarchy_string = ""
                if "hierarchy" in topic and topic["hierarchy"]:
                    hierarchy_titles = []
                    for parent_id in topic["hierarchy"]:
                        parent_title = parent_topic_map.get(str(parent_id), f"Unknown ({parent_id})")
                        hierarchy_titles.append(parent_title)
                    hierarchy_string = " / ".join(hierarchy_titles)

                result.append({
                    "id": topic["id"],
                    "title": topic["title"],
                    "url": f"https://hyperskill.org/learn/topic/{topic['id']}",
                    "link": f"[{topic['title']}](https://hyperskill.org/learn/topic/{topic['id']})",
                    "hierarchy": hierarchy_string
                })

            return result

        # Return just the IDs if fetching details failed
        return [{"id": tid} for tid in topic_ids]
