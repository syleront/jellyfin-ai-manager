import requests
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class JellyfinClient:
    def __init__(self, api_url: str, api_key: str, user_id: str = ""):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.user_id = user_id
        self.headers = {
            "X-Emby-Token": self.api_key,
            "Content-Type": "application/json"
        }

    def get_libraries(self) -> List[Dict[str, Any]]:
        """Gets all libraries (views) for the user."""
        if not self.user_id:
            logger.warning("User ID not provided for JellyfinClient.get_libraries")
            return []
        url = f"{self.api_url}/Users/{self.user_id}/Views"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json().get("Items", [])
        except Exception as e:
            logger.error(f"Error fetching Jellyfin libraries: {e}")
            return []

    def refresh_library(self, library_id: str) -> bool:
        """Triggers a refresh for a specific library."""
        url = f"{self.api_url}/Items/{library_id}/Refresh"
        params = {
            "Recursive": "true",
            "ImageRefreshMode": "Default",
            "MetadataRefreshMode": "Default",
            "ReplaceAllImages": "false",
            "ReplaceAllMetadata": "false"
        }
        try:
            response = requests.post(url, headers=self.headers, params=params)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error refreshing Jellyfin library {library_id}: {e}")
            return False
