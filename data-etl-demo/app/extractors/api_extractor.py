import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30


class APIExtractor:
    """Extracts data from external APIs."""

    def __init__(self, base_url: str = "https://api.example.com") -> None:
        self.base_url = base_url
        self._session = requests.Session()

    def fetch(self, endpoint: str) -> list[dict[str, Any]]:
        """Fetch data from API endpoint with timeout and error handling."""
        url = f"{self.base_url}/{endpoint}"
        logger.info("Fetching data from %s", url)

        response = self._session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        payload = response.json()
        if isinstance(payload, dict):
            data = payload.get("data", [])
        elif isinstance(payload, list):
            data = payload
        else:
            data = []

        logger.info("Fetched %d records from %s", len(data), endpoint)
        return data
