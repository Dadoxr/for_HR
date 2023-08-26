import requests
from typing import List, Dict, Any

class APIExtractor:
    """Extracts data from external APIs."""
    
    def __init__(self, base_url: str = "https://api.example.com") -> None:
        self.base_url: str = base_url
    
    def fetch(self, endpoint: str) -> List[Dict[str, Any]]:
        """Fetch data from API endpoint."""
        response: requests.Response = requests.get(f"{self.base_url}/{endpoint}")
        response.raise_for_status()
        return response.json().get('data', [])

